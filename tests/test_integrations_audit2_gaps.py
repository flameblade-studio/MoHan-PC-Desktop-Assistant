"""第 2 發 integrations 重驗（2026-09-02）找到的九項缺口，全部以行為測試釘住。

重驗明講：不可再用原始碼字串搜尋替代付費呼叫次數、socket 關閉與稽核持久化
結果的驗證。這裡每一條都數實際發生的事。
"""
from __future__ import annotations

lazy import io
lazy import os
lazy import types
lazy import wave
lazy from pathlib import Path
lazy from urllib import error as urllib_error

lazy import pytest

lazy from application.flagship_action_runtime import redact_audit_payload
lazy from integrations import openai_outfit_generator as gen
lazy from integrations import speech_voice_catalog as catalog
lazy from integrations.cloud_connectors import OAuthError, _require_identified
lazy from integrations.home_assistant import HomeAssistantClient, HomeAssistantError
lazy from integrations.realtime_session import RealtimeSessionMethods
lazy from integrations.speech_audio import PcmAudioError, apply_wav_volume


# ---- 1. 被 URLError 包裝的 timeout 不得重送付費請求 ----


def test_wrapped_timeout_is_not_retried(monkeypatch) -> None:
    calls = {"n": 0}

    def fake_urlopen(request, timeout=None):
        calls["n"] += 1
        raise urllib_error.URLError(TimeoutError("timed out"))

    monkeypatch.setattr(gen.urllib_request, "urlopen", fake_urlopen)
    monkeypatch.setattr(gen.time, "sleep", lambda _s: None)
    transport = object.__new__(gen.OpenAIImageEditTransport)
    transport._options = gen.OpenAIImageEditOptions(api_key="test-key")
    with pytest.raises(gen.OutfitImageGenerationError) as failure:
        transport._open_with_retry(object())
    assert calls["n"] == 1
    assert failure.value.retryable is False
    assert failure.value.code == "timeout-ambiguous"


def test_plain_connection_failure_is_still_retried(monkeypatch) -> None:
    calls = {"n": 0}

    def fake_urlopen(request, timeout=None):
        calls["n"] += 1
        raise urllib_error.URLError(ConnectionRefusedError("refused"))

    monkeypatch.setattr(gen.urllib_request, "urlopen", fake_urlopen)
    monkeypatch.setattr(gen.time, "sleep", lambda _s: None)
    transport = object.__new__(gen.OpenAIImageEditTransport)
    transport._options = gen.OpenAIImageEditOptions(api_key="test-key")
    with pytest.raises(gen.OutfitImageGenerationError):
        transport._open_with_retry(object())
    assert calls["n"] == gen.MAX_TRANSIENT_ATTEMPTS


# ---- 2. 同一視角的第二次付費呼叫（handheld）前也要檢查取消 ----


def test_cancel_between_garment_and_handheld_stops_before_second_paid_call(
    monkeypatch, tmp_path: Path
) -> None:
    reference = tmp_path / "ref.png"
    reference.write_bytes(b"png")
    monkeypatch.setattr(gen, "_reference_path", lambda _root, _view: reference)
    generator = object.__new__(gen.OpenAIOutfitDraftGenerator)
    generator._root = tmp_path
    paid = {"n": 0}

    def fake_edit(self, *_edit_arguments):
        paid["n"] += 1
        return b"image"

    generator._checkpointed_edit = types.MethodType(fake_edit, generator)
    generator._design_prompt = lambda request, trends: "design"
    generator._view_prompt = lambda design, view_id, target: "view"
    generator._handheld_prompt = lambda request, view_id, target: "handheld"
    request = types.SimpleNamespace(requested_categories=frozenset({"garment", "handheld"}))
    with pytest.raises(gen.OutfitGenerationCancelled):
        generator.create(
            request,
            (),
            ("yaw+000-pitch+00",),
            cancelled=lambda: paid["n"] >= 1,  # garment 回來後立刻按停手
        )
    assert paid["n"] == 1, f"停手後仍送出了 {paid['n'] - 1} 次 handheld 付費呼叫"


# ---- 3. 郵件預覽與 Home Assistant 個資不得原樣進稽核 ----


def test_audit_redaction_covers_mail_preview_and_home_assistant_attributes() -> None:
    payload = {
        "messages": [{"id": "m1", "subject": "診斷結果", "bodyPreview": "醫師說……", "from": {"emailAddress": {"address": "a@b"}}}],
        "state": {"entity_id": "person.owner", "state": "home", "attributes": {"latitude": 25.03, "longitude": 121.5, "friendly_name": "明樺"}},
    }
    redacted = redact_audit_payload(payload)
    text = str(redacted)
    for secret in ("診斷結果", "醫師說", "a@b", "25.03", "121.5", "明樺"):
        assert secret not in text, f"稽核 payload 仍含 {secret!r}"
    assert redacted["messages"][0]["id"] == "m1"
    assert redacted["state"]["entity_id"] == "person.owner"
    assert redacted["state"]["state"] == "home"


# ---- 4. 非 16-bit WAV 在靜音時不得原音播出 ----


def _wav(sampwidth: int) -> bytes:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as target:
        target.setnchannels(1)
        target.setsampwidth(sampwidth)
        target.setframerate(8000)
        target.writeframes(bytes(range(256)) * 4 if sampwidth == 1 else b"\x00\x10" * 512)
    return buffer.getvalue()


def test_muted_non_pcm16_audio_is_a_failure_not_full_volume() -> None:
    eight_bit = _wav(1)
    with pytest.raises(PcmAudioError):
        apply_wav_volume(eight_bit, 100, muted=True)
    with pytest.raises(PcmAudioError):
        apply_wav_volume(eight_bit, 30, muted=False)
    assert apply_wav_volume(eight_bit, 100, muted=False) == eight_bit  # 原音量：不需處理


# ---- 5. null／容器型 ID 不算已識別 ----


@pytest.mark.parametrize("value", [None, False, {}, [], "", "   "])
def test_non_identifying_values_are_rejected(value) -> None:
    with pytest.raises(OAuthError):
        _require_identified({"id": value}, "Gmail 寄送", "id")


@pytest.mark.parametrize("value", ["abc", 7])
def test_real_identifiers_pass(value) -> None:
    assert _require_identified({"id": value}, "Gmail 寄送", "id") == {"id": value}


# ---- 6. Realtime 非 JSON frame：通知走對的 Signal，且連線一定關閉 ----


class _Signal:
    def __init__(self) -> None:
        self.messages: list[str] = []

    def emit(self, message: str) -> None:
        self.messages.append(message)


class _Ws:
    def __init__(self) -> None:
        self.closed = False

    def close(self) -> None:
        self.closed = True


def test_non_json_realtime_frame_emits_failed_and_closes_socket() -> None:
    fake = types.SimpleNamespace(failed=_Signal(), running=True)
    fake._handle_server_event = lambda event: (_ for _ in ()).throw(AssertionError("不該處理"))
    fake._emit_failure = lambda message: None
    callbacks = RealtimeSessionMethods._websocket_callbacks(fake, object(), lambda: True)
    ws = _Ws()
    callbacks["on_message"](ws, b"\x00\x01 not json")
    assert fake.failed.messages, "failed Signal 沒有被通知"
    assert ws.closed, "非 JSON frame 之後 websocket 沒有被關閉"


# ---- 7. Home Assistant 空物件不是成功讀取 ----


def test_home_assistant_empty_state_object_is_an_error() -> None:
    client = object.__new__(HomeAssistantClient)
    client._request = lambda *args, **kwargs: {}
    with pytest.raises(HomeAssistantError):
        client.state("light.office")
    client._request = lambda *args, **kwargs: {"entity_id": "light.office", "state": "unknown"}
    assert client.state("light.office")["state"] == "unknown"


# ---- 9. 登錄檔項目讀不到且沒有任何語音，必須是查詢失敗而非「未安裝」 ----


@pytest.mark.skipif(os.name != "nt", reason="Windows 語音登錄檔只在 Windows 上")
def test_all_voice_tokens_unreadable_is_a_catalog_error(monkeypatch) -> None:
    def fake_registry_voices(registry_path, prefix):
        fake_registry_voices.last_skipped = 1
        return []

    fake_registry_voices.last_skipped = 0
    monkeypatch.setattr(catalog, "_registry_voices", fake_registry_voices)
    with pytest.raises(catalog.WindowsVoiceCatalogError):
        catalog.windows_voice_catalog()

    def fake_registry_voices_ok(registry_path, prefix):
        fake_registry_voices_ok.last_skipped = 0
        return []

    fake_registry_voices_ok.last_skipped = 0
    monkeypatch.setattr(catalog, "_registry_voices", fake_registry_voices_ok)
    assert catalog.windows_voice_catalog() == []  # 真的沒有語音：正常的空清單
