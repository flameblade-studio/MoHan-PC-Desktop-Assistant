from __future__ import annotations

lazy import json
lazy import sys
lazy from pathlib import Path
lazy from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy import realtime_voice
lazy from realtime_voice import (
    _REALTIME_MESSAGES,
    MAX_ASSISTANT_RESPONSE_CHARACTERS,
    RealtimeSessionConfig,
    RealtimeVoiceClient,
    RealtimeVoiceRequest,
    _realtime_message,
)

EXPECTED_MESSAGES = frozendict({
    "zh-TW": frozendict({
        "connecting": "正在連線…",
        "disconnected": "未連線",
        "listening": "已連線，妾在聽",
        "missing_key": "請先儲存 OpenAI API 金鑰",
        "response_too_long": (
            "Realtime 回應超過 32,768 字元安全上限，已停止本輪回應。"
        ),
        "invalid_key": (
            "目前儲存的 OpenAI API 金鑰無效或已撤銷。"
            "請到「設定」頁重新貼上同一 Project 新建立的 API Key。"
        ),
        "quota": (
            "OpenAI API 額度不足或專案預算已達上限。請檢查該 Project 的 "
            "Billing、Budget 與 Realtime 模型用量限制。"
        ),
        "audio_failed": "音訊裝置無法啟動：backend offline",
        "microphone_prefix": "Windows 無法開啟麥克風。",
    }),
    "zh-CN": frozendict({
        "connecting": "正在连接…",
        "disconnected": "未连接",
        "listening": "已连接，妾在听",
        "missing_key": "请先保存 OpenAI API 密钥",
        "response_too_long": (
            "Realtime 回复超过 32,768 字符安全上限，已停止本轮回复。"
        ),
        "invalid_key": (
            "当前保存的 OpenAI API 密钥无效或已撤销。"
            "请到“设置”页重新粘贴同一 Project 新建立的 API Key。"
        ),
        "quota": (
            "OpenAI API 额度不足或项目预算已达上限。请检查该 Project 的 "
            "Billing、Budget 与 Realtime 模型用量限制。"
        ),
        "audio_failed": "音频设备无法启动：backend offline",
        "microphone_prefix": "Windows 无法打开麦克风。",
    }),
    "en": frozendict({
        "connecting": "Connecting…",
        "disconnected": "Disconnected",
        "listening": "Connected and listening",
        "missing_key": "Save an OpenAI API key first",
        "response_too_long": (
            "The Realtime response exceeded the 32,768-character safety limit; "
            "this response was stopped."
        ),
        "invalid_key": (
            "The saved OpenAI API key is invalid or revoked. Save a new key from "
            "the same Project in Settings."
        ),
        "quota": (
            "The OpenAI API quota is insufficient or the project budget limit "
            "was reached. Check Billing, Budget, and Realtime model usage limits."
        ),
        "audio_failed": "The audio device could not start: backend offline",
        "microphone_prefix": "Windows could not open the microphone.",
    }),
    "ja-JP": frozendict({
        "connecting": "接続中…",
        "disconnected": "未接続",
        "listening": "接続済み、聞いています",
        "missing_key": "先に OpenAI API キーを保存してください",
        "response_too_long": (
            "Realtime の応答が 32,768 文字の安全上限を超えたため、"
            "この応答を停止しました。"
        ),
        "invalid_key": (
            "保存された OpenAI API キーは無効か、取り消されています。"
            "同じ Project で新しいキーを作成し、設定で保存し直してください。"
        ),
        "quota": (
            "OpenAI API の利用枠が不足しているか、プロジェクトの予算上限に"
            "達しました。Billing、Budget、Realtime モデルの利用上限を確認してください。"
        ),
        "audio_failed": "音声デバイスを開始できませんでした：backend offline",
        "microphone_prefix": "Windows でマイクを開けませんでした。",
    }),
})


class _IdleThread:
    def __init__(self, **_options: object) -> None:
        pass

    def start(self) -> None:
        pass


class _WebSocket:
    def __init__(self) -> None:
        self.sent: list[dict[str, object]] = []
        self.close_calls = 0

    def send(self, payload: str) -> None:
        self.sent.append(json.loads(payload))

    def close(self) -> None:
        self.close_calls += 1


def _request(locale: str, api_key: str = "test-key") -> RealtimeVoiceRequest:
    return RealtimeVoiceRequest(
        api_key=api_key,
        instructions="test",
        memory_context="",
        session=RealtimeSessionConfig(locale=locale),
    )


def assert_catalogs_are_complete_and_exact() -> None:
    expected_keys = set(_REALTIME_MESSAGES["zh-TW"])
    assert set(_REALTIME_MESSAGES) == set(EXPECTED_MESSAGES)
    for locale, expected in EXPECTED_MESSAGES.items():
        assert set(_REALTIME_MESSAGES[locale]) == expected_keys
        for key in (
            "connecting",
            "disconnected",
            "listening",
            "missing_key",
            "response_too_long",
        ):
            assert _realtime_message(locale, key) == expected[key]


def assert_runtime_status_signals_are_localized() -> None:
    for locale, expected in EXPECTED_MESSAGES.items():
        client = RealtimeVoiceClient()
        statuses: list[str] = []
        client.status_changed.connect(statuses.append)
        websocket = _WebSocket()

        with (
            patch.object(
                RealtimeVoiceClient,
                "dependencies_available",
                return_value=True,
            ),
            patch.object(realtime_voice.threading, "Thread", _IdleThread),
        ):
            client.start(_request(locale))

        assert statuses == [expected["connecting"]]
        with patch.object(client, "_open_audio"):
            client._open_realtime_session(websocket, _request(locale))
        assert statuses[-1] == expected["listening"]
        client.stop()
        assert statuses[-1] == expected["disconnected"]
        assert websocket.close_calls == 1


def assert_missing_key_signal_is_localized() -> None:
    for locale, expected in EXPECTED_MESSAGES.items():
        client = RealtimeVoiceClient()
        failures: list[str] = []
        client.failed.connect(failures.append)
        client.start(_request(locale, api_key="  "))
        assert failures == [expected["missing_key"]]
        assert not client.running


def assert_oversize_failure_is_localized() -> None:
    oversized = "文" * (MAX_ASSISTANT_RESPONSE_CHARACTERS + 1)
    traditional = EXPECTED_MESSAGES["zh-TW"]["response_too_long"]
    for locale, expected in EXPECTED_MESSAGES.items():
        client = RealtimeVoiceClient()
        client._reset_session_state(
            RealtimeVoiceClient._normalized_request(_request(locale))
        )
        client.native_audio_output = False
        failures: list[str] = []
        client.failed.connect(failures.append)
        client._handle_assistant_text_delta(
            {"response_id": "response-1", "delta": oversized}
        )
        assert failures == [expected["response_too_long"]]
        if locale != "zh-TW":
            assert failures[0] != traditional


def assert_security_errors_are_localized() -> None:
    traditional_invalid = EXPECTED_MESSAGES["zh-TW"]["invalid_key"]
    traditional_quota = EXPECTED_MESSAGES["zh-TW"]["quota"]
    for locale, expected in EXPECTED_MESSAGES.items():
        invalid = RealtimeVoiceClient._friendly_error(
            "HTTP 401 invalid_api_key",
            "gpt-realtime-2.1-mini",
            locale,
        )
        quota = RealtimeVoiceClient._friendly_error(
            "insufficient_quota",
            "gpt-realtime-2.1-mini",
            locale,
        )
        assert invalid == expected["invalid_key"]
        assert quota == expected["quota"]
        if locale != "zh-TW":
            assert invalid != traditional_invalid
            assert quota != traditional_quota


def assert_audio_errors_are_localized() -> None:
    traditional_audio = EXPECTED_MESSAGES["zh-TW"]["audio_failed"]
    for locale, expected in EXPECTED_MESSAGES.items():
        generic = RealtimeVoiceClient._audio_error_message(
            RuntimeError("backend offline"),
            locale,
        )
        microphone = RealtimeVoiceClient._audio_error_message(
            RuntimeError("RawInputStream invalid device"),
            locale,
        )
        assert generic.startswith(expected["audio_failed"].split("backend offline")[0])
        assert "backend offline" not in generic
        assert microphone.startswith(expected["microphone_prefix"])
        assert "RawInputStream invalid device" not in microphone
        if locale != "zh-TW":
            assert generic != traditional_audio


def assert_unknown_locale_falls_back_safely() -> None:
    traditional = EXPECTED_MESSAGES["zh-TW"]
    assert _realtime_message("fr-FR", "connecting") == traditional["connecting"]
    assert RealtimeVoiceClient._friendly_error(
        "invalid_api_key",
        "gpt-realtime-2.1-mini",
        "fr-FR",
    ) == traditional["invalid_key"]
    unknown_audio = RealtimeVoiceClient._audio_error_message(
        RuntimeError("backend offline"),
        "fr-FR",
    )
    assert unknown_audio.startswith(
        traditional["audio_failed"].split("backend offline")[0]
    )
    assert "backend offline" not in unknown_audio


def run() -> None:
    assert_catalogs_are_complete_and_exact()
    assert_runtime_status_signals_are_localized()
    assert_missing_key_signal_is_localized()
    assert_oversize_failure_is_localized()
    assert_security_errors_are_localized()
    assert_audio_errors_are_localized()
    assert_unknown_locale_falls_back_safely()
    print("REALTIME_LOCALIZATION_OK")


if __name__ == "__main__":
    run()
