lazy import io
lazy import json
lazy import math
lazy import os
lazy import queue
lazy import sqlite3
lazy import sys
lazy import time
lazy import wave
lazy from array import array
lazy from pathlib import Path
lazy from tempfile import TemporaryDirectory
lazy from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from ai_client import (
    DEFAULT_TEXT_MODEL,
    TEXT_MODELS,
    AIWorker,
    AIWorkerRequest,
    offline_reply,
)
lazy from app import (
    VOICE_GENERATION_PROMPT,
    migrate_voice_defaults,
)
lazy from command_parser import is_start_work_command, is_stop_work_command
lazy from db import PlatformProgressUpdate, StudioDB, format_duration
lazy from lip_sync import VOWEL_FORMANTS, analyze_pcm16, infer_vowel_pcm16
lazy from realtime_voice import RealtimeVoiceClient
lazy from speech import (
    SpeechListener,
    WindowsTTS,
    apply_wav_volume,
    female_windows_voices_for_language,
    preferred_windows_voice,
    windows_voices,
)
lazy from text_normalizer import to_taiwan_traditional


class PlaybackProbe:
    def __init__(self) -> None:
        self.chunks: list[bytes] = []

    def write(self, chunk: bytes) -> None:
        self.chunks.append(chunk)


def _open_migrated_default_database(temp_dir: str) -> StudioDB:
    database_path = Path(temp_dir) / "test.db"
    db = StudioDB(database_path)
    assert db.setting("ai_model") == "gpt-5.6-luna"
    db.set_setting("ai_model", "gpt-5.4-mini")
    db.conn.execute(
        "DELETE FROM settings WHERE key=?",
        ("luna_default_v210rc1_migrated",),
    )
    db.conn.commit()
    db.close()
    db = StudioDB(database_path)
    assert db.setting("ai_model") == "gpt-5.6-luna"
    return db


def _assert_custom_model_is_preserved(temp_dir: str) -> None:
    database_path = Path(temp_dir) / "custom-model.db"
    custom_db = StudioDB(database_path)
    custom_db.set_setting("ai_model", "gpt-5.6-terra")
    custom_db.conn.execute(
        "DELETE FROM settings WHERE key='mini_default_v118_migrated'"
    )
    custom_db.conn.execute(
        "DELETE FROM settings WHERE key='mini_default_v1213_restored'"
    )
    custom_db.conn.execute(
        "DELETE FROM settings WHERE key=?",
        ("luna_default_v210rc1_migrated",),
    )
    custom_db.conn.commit()
    custom_db.close()
    custom_db = StudioDB(database_path)
    assert custom_db.setting("ai_model") == "gpt-5.6-terra"
    custom_db.close()


def _assert_voice_defaults_migrate_safely(temp_dir: str) -> None:
    voice_db = StudioDB(Path(temp_dir) / "voice-migration.db")
    voice_db.set_setting("voice_instructions", "舊語音提示")
    voice_db.set_setting("tts_voice", "marin")
    voice_db.set_setting("cloud_voice", "marin")
    voice_db.set_setting("realtime_voice", "shimmer")
    migrate_voice_defaults(voice_db)
    assert voice_db.setting("voice_instructions") == VOICE_GENERATION_PROMPT
    assert voice_db.setting("tts_voice") == "coral"
    assert voice_db.setting("cloud_voice") == "coral"
    assert voice_db.setting("realtime_voice") == "coral"
    voice_db.set_setting("voice_instructions", "主上自訂的新提示")
    voice_db.set_setting("tts_voice", "cedar")
    migrate_voice_defaults(voice_db)
    assert voice_db.setting("voice_instructions") == "主上自訂的新提示"
    assert voice_db.setting("tts_voice") == "cedar"
    voice_db.close()


def _assert_ai_worker_defaults() -> None:
    replies: list[str] = []
    worker = AIWorker(
        AIWorkerRequest(
            user_text="主上問候",
            mode="陪伴",
            api_key="sk-test",
        )
    )
    worker.signals.done.connect(replies.append)
    fake_response = io.BytesIO(
        json.dumps({"output_text": "主上，妾在。"}).encode("utf-8")
    )
    with patch(
        "ai_client.urlopen",
        return_value=fake_response,
    ) as mocked_urlopen:
        worker.run()
    sent_request = mocked_urlopen.call_args.args[0]
    sent_payload = json.loads(sent_request.data.decode("utf-8"))
    assert DEFAULT_TEXT_MODEL == "gpt-5.6-luna"
    assert TEXT_MODELS[0] == "gpt-5.6-luna"
    assert "gpt-5.4-mini" not in TEXT_MODELS
    assert sent_payload["model"] == "gpt-5.6-luna"
    assert "[[MOHAN_EMOTION:情緒:強度]]" in sent_payload["instructions"]
    assert replies == ["主上，妾在。"]


def _assert_work_sessions(db: StudioDB) -> None:
    assert db.start_work() is True
    assert db.start_work() is False
    assert db.active_session() is not None
    assert db.stop_work() is True
    assert db.stop_work() is False


def _assert_todos_and_ideas(db: StudioDB) -> None:
    todo_id = db.add_todo("完成漫畫分鏡", "漫畫")
    assert any(row["id"] == todo_id for row in db.list_todos())
    db.set_todo_done(todo_id, True)
    assert not db.list_todos()
    idea_id = db.add_idea("雨夜劍魂場景")
    assert db.list_ideas()[0]["title"] == "雨夜劍魂場景"
    db.update_idea(idea_id, "剑魂苏醒", "她在雨夜听见主上的声音。")
    edited_idea = db.idea(idea_id)
    assert edited_idea["title"] == "劍魂甦醒"
    assert edited_idea["content"] == "她在雨夜聽見主上的聲音。"
    disposable_idea = db.add_idea("待刪除靈感")
    assert db.delete_ideas([disposable_idea]) == 1
    assert db.idea(disposable_idea) is None


def _assert_platform_progress(db: StudioDB) -> None:
    db.update_platform(PlatformProgressUpdate("Pubu", "準備資料", "封面"))
    pubu = next(row for row in db.platform_rows() if row["platform"] == "Pubu")
    assert pubu["missing"] == "封面"
    assert db.add_platform("Company ERP", "portal.example.com") is True
    assert db.add_platform("company erp", "https://duplicate.invalid") is False
    db.update_platform(
        PlatformProgressUpdate(
            "Company ERP",
            "進行中",
            "等待主管回覆",
            "Q3 報表",
            "星期五前送審",
            "財務部窗口",
            "https://portal.example.com",
        )
    )
    erp = next(
        row
        for row in db.platform_rows()
        if row["platform"] == "Company ERP"
    )
    assert erp["item_name"] == "Q3 報表"
    assert erp["url"] == "https://portal.example.com"
    assert db.delete_platform("Company ERP") is True
    assert all(
        row["platform"] != "Company ERP"
        for row in db.platform_rows()
    )


def _assert_settings_memory_and_chat(db: StudioDB) -> None:
    db.set_setting("mode", "工作")
    assert db.setting("mode") == "工作"
    memory_id = db.add_memory("主上偏好先處理漫畫", "偏好", "manual", 4)
    assert memory_id
    assert "先處理漫畫" in db.memory_context()
    db.delete_memory(memory_id)
    assert db.list_memories() == []
    db.log_chat("assistant", "劍主請先休息")
    db.log_chat("user", "你还记得自己的故事吗？")
    assert db.recent_chat()[-1]["content"] == "你還記得自己的故事嗎？"
    retained_count = db.chat_count()
    db.log_chat("assistant", "這則稍後刪除")
    disposable_chat = int(db.recent_chat()[-1]["id"])
    assert db.delete_chat_entries([disposable_chat]) == 1
    assert db.chat_count() == retained_count


def _assert_reopened_chat_migration(temp_dir: str) -> None:
    migrated = StudioDB(Path(temp_dir) / "test.db")
    assert migrated.recent_chat()[-2]["content"] == "主上請先休息"
    migrated.close()


def _assert_legacy_database_migration(temp_dir: str) -> None:
    legacy_path = Path(temp_dir) / "legacy.db"
    legacy_connection = sqlite3.connect(legacy_path)
    legacy_connection.execute(
        "CREATE TABLE ideas (id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "text TEXT NOT NULL,created_at TEXT NOT NULL)"
    )
    legacy_connection.execute(
        "INSERT INTO ideas(text,created_at) VALUES(?,?)",
        ("舊版靈感", "2026-01-01T10:00:00"),
    )
    legacy_connection.commit()
    legacy_connection.close()
    legacy = StudioDB(legacy_path)
    migrated_idea = legacy.list_ideas()[0]
    assert migrated_idea["title"] == "舊版靈感"
    assert migrated_idea["content"] == ""
    assert legacy.setting("assistant_name") == "墨寒"
    assert legacy.setting("organization_name") == "炎劍文化工作室"
    assert legacy.setting("onboarding_complete") is True
    legacy.close()


def _assert_fresh_profile_defaults(temp_dir: str) -> None:
    fresh_profile = StudioDB(Path(temp_dir) / "fresh-profile.db")
    assert fresh_profile.setting("onboarding_complete", False) is False
    assert fresh_profile.platform_rows() == []
    fresh_profile.close()


def _assert_database_contracts() -> None:
    with TemporaryDirectory() as temp_dir:
        db = _open_migrated_default_database(temp_dir)
        _assert_custom_model_is_preserved(temp_dir)
        _assert_voice_defaults_migrate_safely(temp_dir)
        _assert_ai_worker_defaults()
        _assert_work_sessions(db)
        _assert_todos_and_ideas(db)
        _assert_platform_progress(db)
        _assert_settings_memory_and_chat(db)
        db.close()
        _assert_reopened_chat_migration(temp_dir)
        _assert_legacy_database_migration(temp_dir)
        _assert_fresh_profile_defaults(temp_dir)


def _assert_offline_reply_contract() -> None:
    assert format_duration(3720) == "1 小時 2 分"
    assert "計時" in offline_reply("我開始工作了", "工作")
    assert "計時已啟" not in offline_reply(
        "我只是單純在文字框提到開始工作，沒有要啟動計時。",
        "工作",
    )
    assert "計時已啟" not in offline_reply(
        "為什麼墨寒剛才回答計時已啟？",
        "陪伴",
    )
    assert "加班" not in offline_reply(
        "如果我下班之後還有精神，再整理靈感。",
        "工作",
    )
    assert "加班" in offline_reply("我下班了", "工作")
    assert "優先順序" in offline_reply("幫我分析這件事", "工作")
    assert "絕非心疼" in offline_reply("我好累", "陪伴")
    assert "妾" in offline_reply("我想你", "陪伴")


def _assert_speech_listener_contract() -> None:
    quiet = b"\x00\x00" * 160
    loud = b"\xe8\x03" * 160
    assert SpeechListener._rms(quiet) == 0
    assert SpeechListener._rms(loud) == 1000
    assert SpeechListener.TRANSCRIPTION_MODEL == "gpt-4o-mini-transcribe"
    assert SpeechListener.END_SILENCE_SECONDS == 0.85
    assert SpeechListener.MIN_SPEECH_SECONDS == 0.8
    assert SpeechListener.INITIAL_SILENCE_SECONDS == 2.0
    assert SpeechListener.MAX_RECORD_SECONDS == 10.0
    assert SpeechListener.ACTIVE_SPEECH_THRESHOLD_RATIO == 0.68
    assert "金鑰無效" in SpeechListener._http_error_message(401, "")
    assert "未授權" in SpeechListener._http_error_message(403, "")
    assert "找不到轉錄模型" in SpeechListener._http_error_message(404, "")
    assert "額度不足" in SpeechListener._http_error_message(
        429, '{"code":"insufficient_quota"}'
    )
    assert "速率限制" in SpeechListener._http_error_message(429, "")
    assert "暫時異常" in SpeechListener._http_error_message(503, "")
    assert "使用者選擇的語言" in SpeechListener.TRANSCRIPTION_PROMPT
    assert "產品名" in SpeechListener.TRANSCRIPTION_PROMPT


def _assert_pcm_analysis() -> None:
    silent_level, silent_articulation = analyze_pcm16(b"\x00\x00" * 240)
    voiced_level, voiced_articulation = analyze_pcm16(
        array("h", [5000] * 240).tobytes()
    )
    bright_level, bright_articulation = analyze_pcm16(
        array("h", [9000, -9000] * 120).tobytes()
    )
    assert silent_level == silent_articulation == 0.0
    assert voiced_level > silent_level
    assert voiced_articulation < 0.05
    assert bright_level > voiced_level
    assert bright_articulation > 0.9


def _assert_vowel_inference() -> None:
    for expected_vowel, (first_formant, second_formant) in (
        VOWEL_FORMANTS.items()
    ):
        synthetic_vowel = array(
            "h",
            (
                int(
                    7000 * math.sin(2 * math.pi * first_formant * index / 24000)
                    + 5000
                    * math.sin(2 * math.pi * second_formant * index / 24000)
                )
                for index in range(960)
            ),
        )
        vowel_level, inferred_vowel = infer_vowel_pcm16(
            synthetic_vowel.tobytes(),
            24000,
        )
        assert vowel_level > 0.5
        assert inferred_vowel == expected_vowel
    assert infer_vowel_pcm16(b"\x00\x00" * 960) == (0.0, "CLOSED")


def _build_test_wave() -> bytes:
    wave_buffer = io.BytesIO()
    with wave.open(wave_buffer, "wb") as writer:
        writer.setnchannels(1)
        writer.setsampwidth(2)
        writer.setframerate(24000)
        writer.writeframes(
            array(
                "h",
                (
                    int(
                        7000 * math.sin(2 * math.pi * 800 * index / 24000)
                        + 5000
                        * math.sin(2 * math.pi * 1200 * index / 24000)
                    )
                    for index in range(1920)
                ),
            ).tobytes()
        )
    return wave_buffer.getvalue()


def _assert_tts_viseme_cues(wave_data: bytes) -> WindowsTTS:
    emitted_visemes: list[tuple[float, str]] = []
    tts_probe = WindowsTTS()
    tts_probe.viseme_cue.connect(
        lambda level, vowel: emitted_visemes.append((level, vowel))
    )
    with patch("time.sleep", return_value=None):
        tts_probe._emit_wave_cues(wave_data)
    assert emitted_visemes
    assert any(vowel == "A" for _, vowel in emitted_visemes)
    return tts_probe


def _assert_wave_volume(wave_data: bytes) -> None:
    boosted_wave = apply_wav_volume(wave_data, 125, False)
    muted_wave = apply_wav_volume(wave_data, 125, True)
    with wave.open(io.BytesIO(boosted_wave), "rb") as reader:
        boosted_samples = array("h", reader.readframes(reader.getnframes()))
    with wave.open(io.BytesIO(muted_wave), "rb") as reader:
        muted_samples = array("h", reader.readframes(reader.getnframes()))
    assert max(abs(sample) for sample in boosted_samples) > 7000
    assert max(abs(sample) for sample in muted_samples) == 0


def _assert_streaming_wave_rebuild(wave_data: bytes) -> None:
    streaming_wave = bytearray(wave_data)
    streaming_wave[4:8] = (0xFFFFFFFF).to_bytes(4, "little")
    data_offset = streaming_wave.index(b"data")
    streaming_wave[data_offset + 4 : data_offset + 8] = (
        0xFFFFFFFF
    ).to_bytes(4, "little")
    rebuilt_streaming_wave = apply_wav_volume(
        bytes(streaming_wave),
        125,
        False,
    )
    with wave.open(io.BytesIO(rebuilt_streaming_wave), "rb") as reader:
        assert reader.getnframes() == 1920
        assert len(reader.readframes(reader.getnframes())) == 3840


def _assert_tts_volume_clamping(tts_probe: WindowsTTS) -> None:
    tts_probe.set_volume(999, True)
    assert tts_probe.volume_percent == 160
    assert tts_probe.muted


def _assert_work_command_parser() -> None:
    assert is_start_work_command("我開始工作了。")
    assert is_start_work_command("墨寒，開始工作！")
    assert not is_start_work_command("我剛才說我開始工作了，為什麼又計時？")
    assert not is_start_work_command("如果我開始工作，你再提醒我")
    assert not is_start_work_command("開始工作只是這句話裡的一部分")
    assert is_stop_work_command("我收工了。")
    assert not is_stop_work_command("如果我下班以後再處理")


def _assert_windows_voice_selection() -> None:
    voices = [
        ("Microsoft Zira Desktop", "en-US"),
        ("OneCore::Microsoft Zhiwei", "zh-TW"),
        ("Microsoft Hanhan Desktop", "zh-TW"),
        ("OneCore::Microsoft Yating", "zh-TW"),
        ("OneCore::Microsoft Ayumi", "ja-JP"),
    ]
    assert preferred_windows_voice(voices) == "OneCore::Microsoft Yating"
    assert (
        preferred_windows_voice(voices, "Microsoft Hanhan Desktop")
        == "Microsoft Hanhan Desktop"
    )
    assert (
        preferred_windows_voice(voices, "OneCore::Microsoft Zhiwei")
        == "OneCore::Microsoft Yating"
    )
    assert female_windows_voices_for_language(voices, "zh-TW") == [
        ("Microsoft Hanhan Desktop", "zh-TW"),
        ("OneCore::Microsoft Yating", "zh-TW"),
    ]
    assert female_windows_voices_for_language(voices, "zh-CN") == [
        ("Microsoft Hanhan Desktop", "zh-TW"),
        ("OneCore::Microsoft Yating", "zh-TW"),
    ]
    assert female_windows_voices_for_language(voices, "en") == [
        ("Microsoft Zira Desktop", "en-US"),
    ]
    assert female_windows_voices_for_language(voices, "ja-JP") == [
        ("OneCore::Microsoft Ayumi", "ja-JP"),
    ]
    installed = windows_voices()
    # GitHub's clean Windows runners do not guarantee that optional language
    # packs are installed.  The deterministic list above verifies that Yating
    # is preferred when available; this live registry probe only verifies the
    # shape and companion-voice filtering of the current host.
    assert all(
        isinstance(name, str) and isinstance(culture, str)
        for name, culture in installed
    )
    assert all("zhiwei" not in name.lower() for name, _culture in installed)
    if os.environ.get("MOHAN_TEST_REQUIRE_YATING") == "1":
        assert ("OneCore::Microsoft Yating", "zh-TW") in installed


def _assert_voice_generation_prompt() -> None:
    assert VOICE_GENERATION_PROMPT == (
        "請使用台灣繁體中文，以自然的台灣中文口音說話。"
        "聲線如二十多歲的女性動漫配音，清澈、沉靜、帶有古典氣質；"
        "咬字清楚但不要字正腔圓得像播報員。"
        "語氣專業、機敏、略帶傲嬌，對主上含有不明說的溫柔與愛慕。"
        "避免中國普通話腔、兒童聲、過度甜膩、誇張撒嬌或舞台式朗誦。"
    )


def _assert_realtime_audio_lifecycle() -> RealtimeVoiceClient:
    realtime_access_error = RealtimeVoiceClient._friendly_error(
        "invalid_request_error.model_not_found",
        "gpt-realtime-2.1-mini",
    )
    assert "同一個 Project" in realtime_access_error
    assert "gpt-realtime-2.1-mini" in realtime_access_error
    realtime = RealtimeVoiceClient()
    realtime.echo_guard = True
    speaking_events = []
    closing_viseme_cues = []
    realtime.speaking_changed.connect(speaking_events.append)
    realtime.viseme_cue.connect(
        lambda level, vowel: closing_viseme_cues.append((level, vowel))
    )
    completed_transcripts = []
    realtime.user_transcript.connect(completed_transcripts.append)
    realtime._begin_assistant_audio()
    assert realtime._microphone_blocked()
    realtime._emit_completed_user_transcript("你今天心情好吗？")
    assert completed_transcripts == ["你今天心情好吗？"]
    realtime._finish_assistant_audio()
    assert speaking_events[-2:] == [True, False]
    assert closing_viseme_cues[-1] == (0.0, "CLOSED")
    assert realtime._microphone_blocked()
    realtime._input_resume_at = time.monotonic() - 0.1
    assert not realtime._microphone_blocked()
    for completion_event in (
        "response.output_audio.done",
        "response.audio.done",
        "response.done",
        "response.cancelled",
        "response.failed",
    ):
        realtime._begin_assistant_audio()
        assert realtime._assistant_audio_active.is_set()
        realtime._handle_server_event({"type": completion_event})
        assert not realtime._assistant_audio_active.is_set()
        assert speaking_events[-1] is False
    realtime._begin_assistant_audio()
    realtime._handle_server_event(
        {"type": "input_audio_buffer.speech_started"}
    )
    assert not realtime._assistant_audio_active.is_set()
    assert speaking_events[-1] is False
    realtime.running = True
    realtime._begin_assistant_audio()
    with realtime._assistant_state_lock:
        realtime._last_assistant_audio_at = time.monotonic() - 5.0
    time.sleep(0.4)
    assert not realtime._assistant_audio_active.is_set()
    realtime.running = False
    return realtime


def _playback_queue():
    playback_queue = queue.Queue()
    playback_queue.put(array("h", [7000, -7000] * 1200).tobytes())
    playback_queue.put(None)
    return playback_queue


def _assert_realtime_playback(realtime: RealtimeVoiceClient) -> None:
    playback_queue = _playback_queue()
    playback_probe = PlaybackProbe()
    playback_visemes: list[tuple[float, str]] = []
    realtime.viseme_cue.connect(
        lambda level, vowel: playback_visemes.append((level, vowel))
    )
    realtime.running = True
    realtime._playback_loop(playback_queue, playback_probe, 24000)
    realtime.running = False
    assert len(playback_probe.chunks) == 5
    realtime_samples = array("h", b"".join(playback_probe.chunks))
    assert max(realtime_samples) == 8750
    assert len(playback_visemes) >= 5
    muted_queue = _playback_queue()
    muted_probe = PlaybackProbe()
    realtime.set_volume(125, True)
    realtime.running = True
    realtime._playback_loop(muted_queue, muted_probe, 24000)
    realtime.running = False
    assert set(array("h", b"".join(muted_probe.chunks))) == {0}


def _assert_traditional_text_normalization() -> None:
    assert (
        to_taiwan_traditional("会保持专注，打开软件和鼠标。")
        == "會保持專注，開啟軟體和滑鼠。"
    )


def _assert_traditional_chat_migration() -> None:
    with TemporaryDirectory() as temp_dir:
        traditional_path = Path(temp_dir) / "traditional-chat.db"
        traditional_db = StudioDB(traditional_path)
        traditional_db.conn.execute(
            "DELETE FROM settings "
            "WHERE key='traditional_chat_v1215_migrated'"
        )
        traditional_db.conn.execute(
            "INSERT INTO chat_log(role,content,created_at) VALUES(?,?,?)",
            (
                "assistant",
                "会保持专注，打开软件和鼠标。",
                "2026-01-01T00:00:00",
            ),
        )
        traditional_db.conn.commit()
        traditional_db.close()
        traditional_db = StudioDB(traditional_path)
        assert traditional_db.recent_chat(1)[0]["content"] == (
            "會保持專注，開啟軟體和滑鼠。"
        )
        assert traditional_db.setting(
            "traditional_chat_v1215_migrated", False
        ) is True
        traditional_db.close()


def _assert_listener_script_contract() -> None:
    listener_script = (
        Path(__file__).resolve().parents[1] / "voice_listener.ps1"
    ).read_text(encoding="utf-8")
    assert "EndSilenceTimeout" in listener_script
    assert "FromMilliseconds(2500)" in listener_script
    assert "FromMilliseconds(600)" in listener_script
    assert "FromSeconds(7)" in listener_script
    assert "FromSeconds(9)" not in listener_script


def run() -> None:
    _assert_database_contracts()
    _assert_offline_reply_contract()
    _assert_speech_listener_contract()
    _assert_pcm_analysis()
    _assert_vowel_inference()
    wave_data = _build_test_wave()
    tts_probe = _assert_tts_viseme_cues(wave_data)
    _assert_wave_volume(wave_data)
    _assert_streaming_wave_rebuild(wave_data)
    _assert_tts_volume_clamping(tts_probe)
    _assert_work_command_parser()
    _assert_windows_voice_selection()
    _assert_voice_generation_prompt()
    realtime = _assert_realtime_audio_lifecycle()
    _assert_realtime_playback(realtime)
    _assert_traditional_text_normalization()
    _assert_traditional_chat_migration()
    _assert_listener_script_contract()
    print("CORE_TESTS_OK")


if __name__ == "__main__":
    run()
