from __future__ import annotations

lazy import base64
lazy import sys
lazy from collections.abc import Callable
lazy from dataclasses import fields
lazy from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from azure_speech import AzureSpeechTTS, _PushAudioReader
lazy from realtime_speech_output import (
    REALTIME_OUTPUT_AZURE,
    REALTIME_OUTPUT_AZURE_HD,
    REALTIME_OUTPUT_OPENAI,
    AzureRealtimeVoice,
    LocalRealtimeVoice,
    RealtimeSpeechOutput,
    RealtimeSpeechOutputConfig,
    RealtimeTextSegmenter,
)
lazy from realtime_voice import RealtimeSessionConfig, RealtimeVoiceClient


class FakeSignal:
    def __init__(self) -> None:
        self._callbacks: list[Callable[..., None]] = []

    def connect(self, callback: Callable[..., None]) -> None:
        self._callbacks.append(callback)

    def emit(self, *args: object) -> None:
        for callback in tuple(self._callbacks):
            callback(*args)


class FakeSpeechEngine:
    def __init__(self, name: str) -> None:
        self.name = name
        self.finished = FakeSignal()
        self.failed = FakeSignal()
        self.viseme_cue = FakeSignal()
        self.synthesis_latency_measured = FakeSignal()
        self.speak_calls: list[tuple[str, str, str, str]] = []
        self.locales: list[str] = []
        self.stop_calls = 0
        self.volume_calls: list[tuple[int, bool]] = []

    def speak(
        self,
        text: str,
        api_key: str,
        region: str,
        voice: str,
        locale: str = "",
    ) -> None:
        self.speak_calls.append((text, api_key, region, voice))
        self.locales.append(locale)

    def stop(self) -> None:
        self.stop_calls += 1

    def set_volume(self, volume_percent: int, muted: bool = False) -> None:
        self.volume_calls.append((volume_percent, muted))


class FakeOperationSpeechEngine(FakeSpeechEngine):
    def __init__(self, name: str) -> None:
        super().__init__(name)
        self.operation_started = FakeSignal()
        self.operation_finished = FakeSignal()
        self.operation_failed = FakeSignal()
        self.operation_viseme_cue = FakeSignal()
        self.operation_synthesis_latency_measured = FakeSignal()
        self.operation_ids: list[int] = []

    def speak(
        self,
        text: str,
        api_key: str,
        region: str,
        voice: str,
        locale: str = "",
    ) -> int:
        self.speak_calls.append((text, api_key, region, voice))
        self.locales.append(locale)
        operation_id = len(self.operation_ids) + 1
        self.operation_ids.append(operation_id)
        self.operation_started.emit(operation_id)
        return operation_id


class FakeLocalSpeechEngine:
    def __init__(self) -> None:
        self.finished = FakeSignal()
        self.failed = FakeSignal()
        self.viseme_cue = FakeSignal()
        self.speak_calls: list[tuple[str, str, int]] = []
        self.stop_calls = 0
        self.volume_calls: list[tuple[int, bool]] = []

    def speak(self, text: str, voice_name: str = "", rate: int = -1) -> None:
        self.speak_calls.append((text, voice_name, rate))

    def stop(self) -> None:
        self.stop_calls += 1

    def set_volume(self, volume_percent: int, muted: bool = False) -> None:
        self.volume_calls.append((volume_percent, muted))


class FakeSynthesizer:
    def __init__(self) -> None:
        self.stop_calls = 0

    def stop_speaking_async(self) -> None:
        self.stop_calls += 1


def _voice(prefix: str) -> AzureRealtimeVoice:
    return AzureRealtimeVoice(
        api_key=f"{prefix}-test-key",
        region=f"{prefix}-region",
        voice=f"{prefix}-female-voice",
    )


def _hybrid_config(
    mode: str,
    *,
    local_available: bool = False,
) -> RealtimeSpeechOutputConfig:
    return RealtimeSpeechOutputConfig(
        mode=mode,
        azure=_voice("standard"),
        azure_hd=_voice("hd"),
        local=LocalRealtimeVoice(
            available=local_available,
            voice="local-female-voice",
            rate=-1,
        ),
    )


def _create_output() -> tuple[
    RealtimeSpeechOutput,
    FakeSpeechEngine,
    FakeSpeechEngine,
    FakeLocalSpeechEngine,
]:
    standard = FakeSpeechEngine("standard")
    hd = FakeSpeechEngine("hd")
    local = FakeLocalSpeechEngine()
    return RealtimeSpeechOutput(standard, hd, local), standard, hd, local


def _create_operation_output() -> tuple[
    RealtimeSpeechOutput,
    FakeOperationSpeechEngine,
    FakeOperationSpeechEngine,
    FakeLocalSpeechEngine,
]:
    standard = FakeOperationSpeechEngine("standard")
    hd = FakeOperationSpeechEngine("hd")
    local = FakeLocalSpeechEngine()
    return RealtimeSpeechOutput(standard, hd, local), standard, hd, local


def _assert_session_output_modes_are_exclusive() -> None:
    native = RealtimeVoiceClient._session_update_event(
        RealtimeSessionConfig(
            voice="marin",
            output_mode=REALTIME_OUTPUT_OPENAI,
        ),
        "test",
    )["session"]
    assert native["output_modalities"] == ["audio"]
    assert native["audio"]["output"] == {
        "format": {"type": "audio/pcm", "rate": 24000},
        "voice": "marin",
    }

    for mode in (REALTIME_OUTPUT_AZURE, REALTIME_OUTPUT_AZURE_HD):
        hybrid = RealtimeVoiceClient._session_update_event(
            RealtimeSessionConfig(output_mode=mode),
            "test",
        )["session"]
        assert hybrid["output_modalities"] == ["text"]
        assert "output" not in hybrid["audio"]


def _assert_streamed_text_is_segmented_in_order() -> None:
    segmenter = RealtimeTextSegmenter()
    assert segmenter.feed("主上，妾已經完整收到您的所有訊息，") == (
        "主上，妾已經完整收到您的所有訊息，",
    )
    assert segmenter.feed("現在開始處理。接著") == ("現在開始處理。",)
    assert segmenter.feed("會依照順序完成！尾聲") == ("接著會依照順序完成！",)
    assert segmenter.finish() == ("尾聲",)
    assert segmenter.finish() == ()

    long_text = "one two three four five six seven eight nine ten eleven"
    chunks = (*segmenter.feed(long_text), *segmenter.finish())
    assert "".join(chunks).replace(" ", "") == long_text.replace(" ", "")
    assert all(len(chunk) <= RealtimeTextSegmenter.MAXIMUM for chunk in chunks)


def _assert_secret_repr_is_redacted() -> None:
    secret = "must-not-appear"
    voice = AzureRealtimeVoice(secret, "eastasia", "zh-TW-TestNeural")
    config = RealtimeSpeechOutputConfig(azure=voice)

    assert secret not in repr(voice)
    assert secret not in repr(config)
    assert fields(AzureRealtimeVoice)[0].repr is False


def _assert_ui_locale_reaches_cross_language_azure_voice() -> None:
    output, standard, _hd, _local = _create_output()
    config = _hybrid_config(REALTIME_OUTPUT_AZURE)
    output.configure(
        RealtimeSpeechOutputConfig(
            mode=config.mode,
            locale="zh-TW",
            azure=AzureRealtimeVoice(
                config.azure.api_key,
                config.azure.region,
                "zh-CN-XiaoxiaoNeural",
            ),
            azure_hd=config.azure_hd,
            local=config.local,
        )
    )
    output.begin_response(1)
    output.add_text(1, "跨語系錯誤仍須使用繁體中文。")
    output.finish_response(1)

    assert standard.locales == ["zh-TW"]


def _assert_4096_token_text_remains_bounded() -> None:
    output, standard, hd, local = _create_operation_output()
    output.configure(_hybrid_config(REALTIME_OUTPUT_AZURE))
    generation = 1
    output.begin_response(generation)
    token_count = 4_096
    source = "token " * token_count
    output.add_text(generation, source)
    output.finish_response(generation)

    assert output._queue.maxlen == 1_024
    assert len(output._queue) < output._queue.maxlen
    while output._active_operation_id is not None:
        standard.operation_finished.emit(output._active_operation_id)

    spoken = "".join(call[0] for call in standard.speak_calls)
    assert spoken.replace(" ", "") == source.replace(" ", "")
    assert len(standard.speak_calls) <= 1_024
    assert hd.speak_calls == []
    assert local.speak_calls == []


def _assert_oversized_response_stays_rejected_until_next_response() -> None:
    output, standard, hd, local = _create_operation_output()
    failures: list[str] = []
    output.failed.connect(failures.append)
    output.configure(_hybrid_config(REALTIME_OUTPUT_AZURE))
    output.begin_response(1)
    output.add_text(1, "甲" * 32_769)

    assert failures == ["Realtime 回應過長，已安全停止本輪語音。"]
    assert standard.stop_calls == 0
    assert standard.speak_calls == []

    output.add_text(1, "這個遲到片段不得重新開啟同一輪。")
    output.finish_response(1)
    assert standard.speak_calls == []
    assert hd.speak_calls == []
    assert local.speak_calls == []

    output.begin_response(2)
    output.add_text(2, "下一輪可以安全發聲。")
    output.finish_response(2)
    assert [call[0] for call in standard.speak_calls] == ["下一輪可以安全發聲。"]


def _assert_segments_wait_for_the_active_engine() -> None:
    output, standard, hd, local = _create_output()
    output.configure(_hybrid_config(REALTIME_OUTPUT_AZURE))
    output.begin_response(1)
    output.add_text(1, "第一句。第二句。")
    output.finish_response(1)

    assert standard.speak_calls == [
        (
            "第一句。",
            "standard-test-key",
            "standard-region",
            "standard-female-voice",
        )
    ]
    assert hd.speak_calls == []
    assert local.speak_calls == []

    standard.synthesis_latency_measured.emit(120.0)
    standard.finished.emit()
    assert [call[0] for call in standard.speak_calls] == ["第一句。", "第二句。"]
    assert hd.speak_calls == []

    standard.finished.emit()
    assert [call[0] for call in standard.speak_calls] == ["第一句。", "第二句。"]


def _assert_interruption_stops_and_discards_pending_speech() -> None:
    output, standard, hd, local = _create_output()
    output.configure(_hybrid_config(REALTIME_OUTPUT_AZURE))
    output.begin_response(1)
    output.add_text(1, "正在播放。這句不得在插話後播放。")
    assert len(standard.speak_calls) == 1

    output.cancel(2)
    assert standard.stop_calls == 1
    assert hd.stop_calls == 0
    assert local.stop_calls == 0

    standard.finished.emit()
    assert len(standard.speak_calls) == 1


def _assert_newer_cancel_barrier_blocks_queued_generation() -> None:
    output, standard, hd, local = _create_output()
    output.configure(_hybrid_config(REALTIME_OUTPUT_AZURE))
    output.begin_response(3)
    output.add_text(3, "舊世代已開始。")
    assert [call[0] for call in standard.speak_calls] == ["舊世代已開始。"]

    output.cancel(4)
    output.add_text(3, "遲到的舊文字不得重新發聲。")
    output.finish_response(3)
    standard.finished.emit()

    assert [call[0] for call in standard.speak_calls] == ["舊世代已開始。"]
    assert standard.stop_calls == 1
    assert hd.speak_calls == []
    assert local.speak_calls == []

    output.begin_response(5)
    output.add_text(5, "新世代可以安全發聲。")
    output.finish_response(5)

    assert [call[0] for call in standard.speak_calls] == [
        "舊世代已開始。",
        "新世代可以安全發聲。",
    ]


def _assert_stale_same_engine_callbacks_cannot_close_new_operation() -> None:
    output, standard, _hd, _local = _create_operation_output()
    failures: list[str] = []
    visemes: list[tuple[float, str]] = []
    output.failed.connect(failures.append)
    output.viseme_cue.connect(lambda level, vowel: visemes.append((level, vowel)))
    output.configure(_hybrid_config(REALTIME_OUTPUT_AZURE))
    output.begin_response(1)
    output.add_text(1, "舊的一輪。")
    old_operation = standard.operation_ids[-1]

    output.begin_response(2)
    output.add_text(2, "新的語音仍應繼續。下一段也必須保留。")
    output.finish_response(2)
    new_operation = standard.operation_ids[-1]
    assert new_operation != old_operation

    standard.operation_synthesis_latency_measured.emit(old_operation, 1.0)
    standard.operation_viseme_cue.emit(old_operation, 0.9, "A")
    standard.operation_finished.emit(old_operation)
    standard.operation_failed.emit(old_operation, "stale failure")

    assert len(standard.speak_calls) == 2
    assert visemes == []
    assert failures == []
    assert output._active_operation_id == new_operation

    standard.operation_synthesis_latency_measured.emit(new_operation, 2.0)
    standard.operation_viseme_cue.emit(new_operation, 0.5, "I")
    standard.operation_finished.emit(new_operation)

    assert visemes == [(0.5, "I")]
    assert len(standard.speak_calls) == 3


def _assert_stale_failure_does_not_trigger_fallback() -> None:
    output, standard, hd, local = _create_operation_output()
    output.configure(
        _hybrid_config(
            REALTIME_OUTPUT_AZURE_HD,
            local_available=True,
        )
    )
    output.begin_response(1)
    output.add_text(1, "舊的 Dragon HD。")
    old_operation = hd.operation_ids[-1]

    output.begin_response(2)
    output.add_text(2, "新的 Dragon HD。")
    new_operation = hd.operation_ids[-1]
    hd.operation_failed.emit(old_operation, "stale failure")

    assert new_operation != old_operation
    assert len(hd.speak_calls) == 2
    assert standard.speak_calls == []
    assert local.speak_calls == []
    assert output._active_operation_id == new_operation

    hd.operation_failed.emit(new_operation, "current failure")
    assert [call[0] for call in standard.speak_calls] == ["新的 Dragon HD。"]


def _assert_hd_falls_back_to_standard_once() -> None:
    output, standard, hd, local = _create_output()
    failures: list[str] = []
    output.failed.connect(failures.append)
    output.configure(_hybrid_config(REALTIME_OUTPUT_AZURE_HD))
    output.begin_response(1)
    output.add_text(1, "同一段只能各嘗試一次。")

    assert [call[0] for call in hd.speak_calls] == ["同一段只能各嘗試一次。"]
    assert standard.speak_calls == []

    hd.failed.emit("hd unavailable")
    assert [call[0] for call in standard.speak_calls] == ["同一段只能各嘗試一次。"]
    assert local.speak_calls == []

    standard.failed.emit("standard unavailable")
    assert [call[0] for call in hd.speak_calls] == ["同一段只能各嘗試一次。"]
    assert [call[0] for call in standard.speak_calls] == ["同一段只能各嘗試一次。"]
    assert local.speak_calls == []
    assert failures == ["Realtime 語音輸出失敗：standard unavailable"]


def _assert_partial_audio_failure_does_not_repeat_the_clause() -> None:
    output, standard, hd, local = _create_operation_output()
    failures: list[str] = []
    output.failed.connect(failures.append)
    output.configure(
        _hybrid_config(REALTIME_OUTPUT_AZURE_HD, local_available=True)
    )
    output.begin_response(1)
    output.add_text(1, "已經播放句首的句子。")
    operation_id = hd.operation_ids[-1]
    hd.operation_synthesis_latency_measured.emit(operation_id, 25.0)
    hd.operation_failed.emit(operation_id, "stream interrupted")

    assert len(hd.speak_calls) == 1
    assert hd.stop_calls == 1
    assert standard.speak_calls == []
    assert local.speak_calls == []
    assert failures == ["Realtime 語音輸出失敗：stream interrupted"]

    output.add_text(1, "同一輪遲到的片段不得重新啟動發聲。")
    output.finish_response(1)
    assert len(hd.speak_calls) == 1
    assert standard.speak_calls == []
    assert local.speak_calls == []

    output.begin_response(2)
    output.add_text(2, "下一輪可以安全重新發聲。")
    output.finish_response(2)
    assert [call[0] for call in hd.speak_calls] == [
        "已經播放句首的句子。",
        "下一輪可以安全重新發聲。",
    ]


def _assert_fallback_chain_is_one_way_and_isolated() -> None:
    output, standard, hd, local = _create_output()
    output.configure(
        _hybrid_config(
            REALTIME_OUTPUT_AZURE_HD,
            local_available=True,
        )
    )
    output.begin_response(1)
    output.add_text(1, "依序備援，不得同時播放。")

    hd.failed.emit("hd unavailable")
    hd.finished.emit()
    assert len(standard.speak_calls) == 1
    assert local.speak_calls == []

    standard.failed.emit("standard unavailable")

    assert [call[0] for call in hd.speak_calls] == ["依序備援，不得同時播放。"]
    assert [call[0] for call in standard.speak_calls] == ["依序備援，不得同時播放。"]
    assert local.speak_calls == [("依序備援，不得同時播放。", "local-female-voice", -1)]

    local.finished.emit()
    assert len(hd.speak_calls) == 1
    assert len(standard.speak_calls) == 1
    assert len(local.speak_calls) == 1


def _assert_native_mode_never_starts_azure_engines() -> None:
    output, standard, hd, local = _create_output()
    output.configure(_hybrid_config(REALTIME_OUTPUT_OPENAI))
    output.begin_response(1)
    output.add_text(1, "原生 Realtime 應自行發聲。")
    output.finish_response(1)

    assert not output.active
    assert standard.speak_calls == []
    assert hd.speak_calls == []
    assert local.speak_calls == []
    assert standard.stop_calls == 0
    assert hd.stop_calls == 0
    assert local.stop_calls == 0


def _assert_switching_routes_stops_only_the_active_engine() -> None:
    output, standard, hd, local = _create_output()
    output.configure(_hybrid_config(REALTIME_OUTPUT_AZURE))
    output.begin_response(1)
    output.add_text(1, "一般 Azure 正在播放。")

    output.configure(_hybrid_config(REALTIME_OUTPUT_AZURE_HD))
    assert standard.stop_calls == 1
    assert hd.stop_calls == 0
    assert local.stop_calls == 0

    output.begin_response(2)
    output.add_text(2, "Dragon HD 接手。")
    assert [call[0] for call in standard.speak_calls] == ["一般 Azure 正在播放。"]
    assert [call[0] for call in hd.speak_calls] == ["Dragon HD 接手。"]


def _assert_azure_stop_discards_audio_and_isolates_instances() -> None:
    first = AzureSpeechTTS()
    second = AzureSpeechTTS()
    first_reader = _PushAudioReader()
    second_reader = _PushAudioReader()
    first_synthesizer = FakeSynthesizer()
    second_synthesizer = FakeSynthesizer()
    first_reader.write(memoryview(b"\x01\x00" * 480))
    second_reader.write(memoryview(b"\x02\x00" * 480))
    first._active_reader = first_reader
    first._active_synthesizer = first_synthesizer
    second._active_reader = second_reader
    second._active_synthesizer = second_synthesizer

    first.stop()

    assert first_reader.read(bytearray(960)) == 0
    assert first_synthesizer.stop_calls == 1
    assert first._active_reader is None
    assert first._active_synthesizer is None
    assert second_reader.read(bytearray(960)) == 960
    assert second_synthesizer.stop_calls == 0
    assert second._active_reader is second_reader
    assert second._active_synthesizer is second_synthesizer


def _assert_text_mode_rejects_unexpected_openai_audio() -> None:
    client = RealtimeVoiceClient()
    client.native_audio_output = False
    speaking: list[bool] = []
    client.speaking_changed.connect(speaking.append)
    unexpected_audio = base64.b64encode(b"\x01\x00" * 480).decode("ascii")

    client._handle_server_event({
        "type": "response.output_audio.delta",
        "delta": unexpected_audio,
    })

    assert speaking == []
    assert not client._assistant_audio_active.is_set()
    assert client._audio_queue.empty()


def _official_text_event(
    kind: str,
    response_id: str,
    **payload: object,
) -> dict[str, object]:
    return {
        "type": kind,
        "event_id": f"event-{kind}",
        "response_id": response_id,
        "item_id": "item-1",
        "output_index": 0,
        "content_index": 0,
        **payload,
    }


def _assert_official_response_lifecycle_commits_only_completed_text() -> None:
    client = RealtimeVoiceClient()
    client.native_audio_output = False
    deltas: list[tuple[int, str]] = []
    transcripts: list[str] = []
    completed: list[int] = []
    started: list[int] = []
    client.output_text_started.connect(started.append)
    client.output_text_delta.connect(
        lambda generation, text: deltas.append((generation, text))
    )
    client.assistant_transcript.connect(transcripts.append)
    client.output_text_done.connect(completed.append)

    client._handle_server_event({
        "type": "response.created",
        "response": {"id": "response-1", "status": "in_progress"},
    })
    assert started == [1]
    client._handle_server_event(
        _official_text_event(
            "response.output_text.delta",
            "response-1",
            delta="主上，妾在。",
        )
    )
    client._handle_server_event(
        _official_text_event(
            "response.output_text.done",
            "response-1",
            text="主上，妾在。",
        )
    )
    assert deltas == [(1, "主上，妾在。")]
    assert transcripts == []
    assert completed == []

    completed_event = {
        "type": "response.done",
        "response": {"id": "response-1", "status": "completed"},
    }
    client._handle_server_event(completed_event)
    client._handle_server_event(completed_event)
    client._handle_server_event(
        _official_text_event(
            "response.output_text.delta",
            "response-1",
            delta="不得重複。",
        )
    )

    assert deltas == [(1, "主上，妾在。")]
    assert transcripts == ["主上，妾在。"]
    assert completed == [1]


def _assert_native_cancel_discards_audio_and_ignores_late_events() -> None:
    client = RealtimeVoiceClient()
    client.native_audio_output = True
    speaking: list[bool] = []
    client.speaking_changed.connect(speaking.append)
    audio = base64.b64encode(b"\x01\x00" * 480).decode("ascii")
    client._handle_server_event({
        "type": "response.created",
        "response": {"id": "native-old", "status": "in_progress"},
    })
    client._handle_server_event(
        _official_text_event("response.output_audio.delta", "native-old", delta=audio)
    )
    assert not client._audio_queue.empty()

    cancelled = {
        "type": "response.done",
        "response": {"id": "native-old", "status": "cancelled"},
    }
    client._handle_server_event(cancelled)
    client._handle_server_event(cancelled)
    assert client._audio_queue.empty()
    assert speaking == [True, False]

    client._handle_server_event({
        "type": "response.created",
        "response": {"id": "native-new", "status": "in_progress"},
    })
    client._handle_server_event(
        _official_text_event("response.output_audio.delta", "native-old", delta=audio)
    )
    assert client._audio_queue.empty()
    client._handle_server_event(
        _official_text_event("response.output_audio.delta", "native-new", delta=audio)
    )
    assert not client._audio_queue.empty()


def _assert_aborted_responses_block_late_text_events() -> None:
    for index, status in enumerate(("cancelled", "failed", "incomplete")):
        client = RealtimeVoiceClient()
        client.native_audio_output = False
        deltas: list[tuple[int, str]] = []
        transcripts: list[str] = []
        completed: list[int] = []
        interrupted: list[int] = []
        client.output_text_delta.connect(
            lambda generation, text, deltas=deltas: deltas.append(
                (generation, text)
            )
        )
        client.assistant_transcript.connect(transcripts.append)
        client.output_text_done.connect(completed.append)
        client.output_interrupted.connect(interrupted.append)
        response_id = f"response-aborted-{index}"

        client._handle_server_event({
            "type": "response.created",
            "response": {"id": response_id, "status": "in_progress"},
        })
        client._handle_server_event(
            _official_text_event(
                "response.output_text.delta",
                response_id,
                delta="尚未完成",
            )
        )
        client._handle_server_event({
            "type": "response.done",
            "response": {"id": response_id, "status": status},
        })
        client._handle_server_event(
            _official_text_event(
                "response.output_text.delta",
                response_id,
                delta="不得外流",
            )
        )
        client._handle_server_event(
            _official_text_event(
                "response.output_text.done",
                response_id,
                text="尚未完成不得外流",
            )
        )
        client._handle_server_event({
            "type": "response.done",
            "response": {"id": response_id, "status": "completed"},
        })

        assert deltas == [(1, "尚未完成")]
        assert transcripts == []
        assert completed == []
        assert interrupted == [2]


def _assert_missing_response_id_remains_compatible() -> None:
    client = RealtimeVoiceClient()
    client.native_audio_output = False
    transcripts: list[str] = []
    completed: list[int] = []
    client.assistant_transcript.connect(transcripts.append)
    client.output_text_done.connect(completed.append)

    client._handle_server_event({
        "type": "response.output_text.delta",
        "delta": "相容事件。",
    })
    client._handle_server_event({
        "type": "response.output_text.done",
        "text": "相容事件。",
    })
    client._handle_server_event({
        "type": "response.done",
        "response": {"status": "completed"},
    })

    assert transcripts == ["相容事件。"]
    assert completed == [1]


def _assert_foreign_terminal_event_cannot_cancel_active_response() -> None:
    client = RealtimeVoiceClient()
    client.native_audio_output = False
    transcripts: list[str] = []
    interrupted: list[int] = []
    client.assistant_transcript.connect(transcripts.append)
    client.output_interrupted.connect(interrupted.append)

    client._handle_server_event({
        "type": "response.created",
        "response": {"id": "response-active", "status": "in_progress"},
    })
    client._handle_server_event(
        _official_text_event(
            "response.output_text.delta",
            "response-active",
            delta="正確回應。",
        )
    )
    client._handle_server_event({
        "type": "response.done",
        "response": {"id": "response-stale", "status": "cancelled"},
    })
    client._handle_server_event({
        "type": "response.done",
        "response": {"id": "response-active", "status": "completed"},
    })

    assert transcripts == ["正確回應。"]
    assert interrupted == []


def _assert_websocket_close_interrupts_hybrid_output_once() -> None:
    client = RealtimeVoiceClient()
    client.native_audio_output = False
    interrupted: list[int] = []
    client.output_interrupted.connect(interrupted.append)

    client._close_realtime_session()
    client._close_realtime_session()

    assert interrupted == [1]


def run() -> None:
    _assert_session_output_modes_are_exclusive()
    _assert_streamed_text_is_segmented_in_order()
    _assert_secret_repr_is_redacted()
    _assert_ui_locale_reaches_cross_language_azure_voice()
    _assert_4096_token_text_remains_bounded()
    _assert_oversized_response_stays_rejected_until_next_response()
    _assert_segments_wait_for_the_active_engine()
    _assert_interruption_stops_and_discards_pending_speech()
    _assert_newer_cancel_barrier_blocks_queued_generation()
    _assert_stale_same_engine_callbacks_cannot_close_new_operation()
    _assert_stale_failure_does_not_trigger_fallback()
    _assert_hd_falls_back_to_standard_once()
    _assert_partial_audio_failure_does_not_repeat_the_clause()
    _assert_fallback_chain_is_one_way_and_isolated()
    _assert_native_mode_never_starts_azure_engines()
    _assert_switching_routes_stops_only_the_active_engine()
    _assert_azure_stop_discards_audio_and_isolates_instances()
    _assert_text_mode_rejects_unexpected_openai_audio()
    _assert_official_response_lifecycle_commits_only_completed_text()
    _assert_native_cancel_discards_audio_and_ignores_late_events()
    _assert_aborted_responses_block_late_text_events()
    _assert_missing_response_id_remains_compatible()
    _assert_foreign_terminal_event_cannot_cancel_active_response()
    _assert_websocket_close_interrupts_hybrid_output_once()
    print("REALTIME_SPEECH_OUTPUT_OK")


if __name__ == "__main__":
    run()
