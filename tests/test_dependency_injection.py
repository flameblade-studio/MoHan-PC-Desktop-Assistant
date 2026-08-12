from __future__ import annotations

lazy import os
lazy import sys
lazy from dataclasses import dataclass
lazy from pathlib import Path
lazy from tempfile import TemporaryDirectory

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from PySide6.QtCore import QObject, Signal
lazy from PySide6.QtWidgets import QApplication, QLineEdit

lazy from app import CompanionWindow, SpeechCredentials
lazy from db import StudioDB
lazy from realtime_voice import RealtimeVoiceRequest
lazy from service_container import CompanionServices


class FakeSecretStore:
    def __init__(self, value: str = "test-key") -> None:
        self.value = value

    def load(self) -> str:
        return self.value

    def save(self, value: str) -> None:
        self.value = value

    def clear(self) -> None:
        self.value = ""


class FakeSpeechEngine(QObject):
    finished = Signal()
    failed = Signal(str)
    viseme_cue = Signal(str, float)

    def __init__(self) -> None:
        super().__init__()
        self.volume_calls: list[tuple[int, bool]] = []
        self.speak_calls: list[tuple[tuple, dict]] = []

    def set_volume(self, volume_percent: int, muted: bool = False) -> None:
        self.volume_calls.append((volume_percent, muted))

    def speak(self, *args, **kwargs) -> None:
        self.speak_calls.append((args, kwargs))


class FakeRealtime(QObject):
    status_changed = Signal(str)
    user_transcript = Signal(str)
    assistant_transcript = Signal(str)
    speaking_changed = Signal(bool)
    viseme_cue = Signal(str, float)
    failed = Signal(str)
    output_text_started = Signal(int)
    output_text_delta = Signal(int, str)
    output_text_done = Signal(int)
    output_interrupted = Signal(int)

    def __init__(self) -> None:
        super().__init__()
        self.running = False
        self.stop_calls = 0
        self.start_requests: list[RealtimeVoiceRequest] = []
        self.volume_calls: list[tuple[int, bool]] = []

    def set_volume(self, volume_percent: int, muted: bool = False) -> None:
        self.volume_calls.append((volume_percent, muted))

    def start(self, request: RealtimeVoiceRequest) -> None:
        self.start_requests.append(request)
        self.running = True

    def stop(self) -> int:
        self.running = False
        self.stop_calls += 1
        return self.stop_calls

    def set_external_playback_active(self, _active: bool) -> None:
        return


def _assert_credential_repr_is_redacted() -> None:
    secrets = ("openai-secret", "azure-secret", "azure-hd-secret")
    credentials = SpeechCredentials(
        openai_api_key=secrets[0],
        azure_api_key=secrets[1],
        azure_region="eastasia",
        azure_hd_api_key=secrets[2],
        azure_hd_region="westus2",
    )
    rendered = repr(credentials)
    assert all(secret not in rendered for secret in secrets)


class FakeListener(QObject):
    recognized = Signal(str)
    failed = Signal(str)
    listening_changed = Signal(bool)
    recording_changed = Signal(bool)
    status_changed = Signal(str)
    diagnostic_changed = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.is_recording = False
        self.toggle_calls = 0

    def toggle_listening(self) -> None:
        self.toggle_calls += 1


@dataclass(slots=True)
class InjectedTestContext:
    app: QApplication
    db: StudioDB
    secret_store: FakeSecretStore
    azure_secret_store: FakeSecretStore
    azure_hd_secret_store: FakeSecretStore
    local_tts: FakeSpeechEngine
    cloud_tts: FakeSpeechEngine
    azure_tts: FakeSpeechEngine
    azure_hd_tts: FakeSpeechEngine
    realtime: FakeRealtime
    listener: FakeListener
    window: CompanionWindow


def _create_injected_context(temp_dir: str) -> InjectedTestContext:
    app = QApplication.instance() or QApplication([])
    db = StudioDB(Path(temp_dir) / "mohan.db")
    db.set_setting("onboarding_complete", True)
    db.set_setting("tts_enabled", False)
    db.set_setting("voice_volume_percent", 137)
    db.set_setting("voice_muted", False)
    secret_store = FakeSecretStore()
    azure_secret_store = FakeSecretStore()
    azure_hd_secret_store = FakeSecretStore("test-hd-key")
    local_tts = FakeSpeechEngine()
    cloud_tts = FakeSpeechEngine()
    azure_tts = FakeSpeechEngine()
    azure_hd_tts = FakeSpeechEngine()
    realtime = FakeRealtime()
    listener = FakeListener()
    services = CompanionServices(
        db=db,
        secret_store=secret_store,
        local_tts=local_tts,
        cloud_tts=cloud_tts,
        realtime=realtime,
        listener=listener,
        azure_speech=azure_tts,
        azure_hd_speech=azure_hd_tts,
        azure_secret_store=azure_secret_store,
        azure_hd_secret_store=azure_hd_secret_store,
    )
    window = CompanionWindow(startup_speech=False, services=services)
    return InjectedTestContext(
        app=app,
        db=db,
        secret_store=secret_store,
        azure_secret_store=azure_secret_store,
        azure_hd_secret_store=azure_hd_secret_store,
        local_tts=local_tts,
        cloud_tts=cloud_tts,
        azure_tts=azure_tts,
        azure_hd_tts=azure_hd_tts,
        realtime=realtime,
        listener=listener,
        window=window,
    )


def _assert_dependencies_are_injected(context: InjectedTestContext) -> None:
    assert context.window.db is context.db
    assert context.window.secret_store is context.secret_store
    assert context.window.tts is context.local_tts
    assert context.window.cloud_tts is context.cloud_tts
    assert context.window.azure_tts is context.azure_tts
    assert context.window.azure_hd_tts is context.azure_hd_tts
    assert context.window.azure_hd_secret_store is (
        context.azure_hd_secret_store
    )
    assert context.window.realtime is context.realtime
    assert context.window.listener is context.listener
    assert context.local_tts.volume_calls[-1] == (137, False)
    assert context.cloud_tts.volume_calls[-1] == (137, False)
    assert context.azure_tts.volume_calls[-1] == (137, False)
    assert context.azure_hd_tts.volume_calls[-1] == (137, False)
    assert context.realtime.volume_calls[-1] == (137, False)


def _assert_provider_switch_persists_and_routes(
    context: InjectedTestContext,
) -> None:
    dashboard = context.window.dashboard
    local_index = dashboard.voice_engine.findData("system-local")
    openai_index = dashboard.voice_engine.findData("openai-speech")
    assert local_index >= 0 and openai_index >= 0

    dashboard.voice_engine.setCurrentIndex(openai_index)
    assert context.db.setting("voice_engine") == "openai-speech"
    context.window._start_speech_provider("OpenAI 語音測試。")
    assert context.cloud_tts.speak_calls[-1][0][0] == "OpenAI 語音測試。"

    dashboard.voice_engine.setCurrentIndex(local_index)
    assert context.db.setting("voice_engine") == "system-local"
    context.window._start_speech_provider("本機語音測試。")
    assert context.local_tts.speak_calls[-1][0][0] == "本機語音測試。"



def _assert_voice_choices_save_and_apply_immediately(
    context: InjectedTestContext,
) -> None:
    dashboard = context.window.dashboard

    dashboard.tts_voice.setCurrentText("marin")
    assert context.db.setting("tts_voice") == "marin"
    assert context.db.setting("cloud_voice") == "marin"

    assert dashboard.azure_voice.findText("zh-CN-XiaoxiaoNeural") >= 0
    dashboard.azure_voice.setCurrentText("zh-CN-XiaoxiaoNeural")
    assert (
        context.db.setting("azure_speech_voice")
        == "zh-CN-XiaoxiaoNeural"
    )

    southeast_asia = dashboard.azure_region.findData("southeastasia")
    assert southeast_asia >= 0
    dashboard.azure_region.setCurrentIndex(southeast_asia)
    assert context.db.setting("azure_speech_region") == "southeastasia"

    hd_southeast_asia = dashboard.azure_hd_region.findData("southeastasia")
    hd_central_india = dashboard.azure_hd_region.findData("centralindia")
    assert hd_southeast_asia >= 0 and hd_central_india >= 0
    dashboard.azure_hd_region.setCurrentIndex(hd_southeast_asia)
    flash_voice = "zh-CN-Xiaoxiao:DragonHDFlashLatestNeural"
    assert dashboard.azure_hd_voice.findText(flash_voice) >= 0
    dashboard.azure_hd_voice.setCurrentText(flash_voice)
    assert context.db.setting("azure_hd_speech_voice") == flash_voice

    dashboard.azure_hd_region.setCurrentIndex(hd_central_india)
    assert context.db.setting("azure_hd_speech_region") == "centralindia"
    assert dashboard.azure_hd_voice.findText(flash_voice) == -1
    assert "Flash" not in dashboard.azure_hd_voice.currentText()
    assert context.db.setting("azure_hd_speech_voice") == (
        dashboard.azure_hd_voice.currentText()
    )

    dashboard.realtime_voice.setCurrentText("shimmer")
    assert context.db.setting("realtime_voice") == "shimmer"
    assert context.realtime.start_requests == []

    context.window.toggle_realtime(True)
    assert context.realtime.start_requests[-1].session.voice == "shimmer"
    dashboard.realtime_voice.setCurrentText("coral")
    assert context.db.setting("realtime_voice") == "coral"
    assert context.realtime.stop_calls == 1
    assert context.realtime.start_requests[-1].session.voice == "coral"


def _assert_secret_fields_save_consistently_and_securely(
    context: InjectedTestContext,
) -> None:
    dashboard = context.window.dashboard
    fields = (
        (dashboard.api_key_input, context.secret_store, "sk-openai-test"),
        (
            dashboard.azure_key_input,
            context.azure_secret_store,
            "azure-standard-test",
        ),
        (
            dashboard.azure_hd_key_input,
            context.azure_hd_secret_store,
            "azure-dragon-hd-test",
        ),
    )
    for key_input, secret_store, secret in fields:
        assert key_input.echoMode() == QLineEdit.Password
        assert key_input.isEnabled()
        assert key_input.accessibleName()
        assert "自動安全保存" in key_input.toolTip()
        secret_store.clear()
        key_input.setText(secret)
        key_input.editingFinished.emit()
        assert secret_store.load() == secret
        assert key_input.text() == ""
        assert "保存" in key_input.placeholderText()

    database_text = "\n".join(
        str(row["value"])
        for row in context.db.conn.execute("SELECT value FROM settings")
    )
    assert all(secret not in database_text for *_prefix, secret in fields)

def _assert_cloud_failure_uses_local_tts(
    context: InjectedTestContext,
) -> None:
    context.db.set_setting("tts_enabled", True)
    context.db.set_setting("voice_engine", "OpenAI 自然語音")
    context.db.set_setting("windows_voice", "OneCore::Microsoft Yating")
    cloud_calls = len(context.cloud_tts.speak_calls)
    local_calls = len(context.local_tts.speak_calls)
    context.window.speak("主上，妾在。", "speaking")
    assert len(context.cloud_tts.speak_calls) == cloud_calls + 1
    assert len(context.local_tts.speak_calls) == local_calls
    context.cloud_tts.failed.emit("模擬雲端播放失敗")
    context.app.processEvents()
    assert context.local_tts.speak_calls[-1][0] == (
        "主上，妾在。",
        "OneCore::Microsoft Yating",
        -1,
    )
    assert context.window.cloud_fallback_active


def _assert_azure_failure_uses_local_tts(
    context: InjectedTestContext,
) -> None:
    context.window.speech_playing = False
    context.window.cloud_fallback_active = False
    context.db.set_setting("voice_engine", "Azure Speech（預覽）")
    context.db.set_setting("azure_speech_region", "eastasia")
    context.db.set_setting(
        "azure_speech_voice",
        "zh-TW-HsiaoChenNeural",
    )
    context.window.speak("Azure 測試。", "speaking")
    assert context.azure_tts.speak_calls[-1][0] == (
        "Azure 測試。",
        "test-key",
        "eastasia",
        "zh-TW-HsiaoChenNeural",
        "zh-TW",
    )
    context.azure_tts.failed.emit("模擬 Azure 播放失敗")
    context.app.processEvents()
    assert context.local_tts.speak_calls[-1][0] == (
        "Azure 測試。",
        "OneCore::Microsoft Yating",
        -1,
    )


def _assert_missing_azure_settings_fail_locally(
    context: InjectedTestContext,
) -> None:
    azure_call_count = len(context.azure_tts.speak_calls)
    context.azure_secret_store.clear()
    context.db.set_setting("azure_speech_region", "")
    context.window.speech_playing = False
    context.window.cloud_fallback_active = False
    context.window.speak("缺少 Azure 設定。", "speaking")
    assert len(context.azure_tts.speak_calls) == azure_call_count
    assert context.local_tts.speak_calls[-1][0] == (
        "缺少 Azure 設定。",
        "OneCore::Microsoft Yating",
        -1,
    )
    status = context.window.dashboard.api_status.text()
    assert "未送出" in status and "雲端請求" in status, status


def _assert_controls_and_shutdown(context: InjectedTestContext) -> None:
    context.window.dashboard.mic_btn.click()
    assert context.listener.toggle_calls == 1
    stop_calls_before_close = context.realtime.stop_calls
    context.window.close()
    context.app.processEvents()
    assert context.realtime.stop_calls == stop_calls_before_close + 1


def run() -> None:
    _assert_credential_repr_is_redacted()
    with TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
        context = _create_injected_context(temp_dir)
        _assert_dependencies_are_injected(context)
        _assert_provider_switch_persists_and_routes(context)
        _assert_voice_choices_save_and_apply_immediately(context)
        _assert_cloud_failure_uses_local_tts(context)
        _assert_azure_failure_uses_local_tts(context)
        _assert_missing_azure_settings_fail_locally(context)
        _assert_secret_fields_save_consistently_and_securely(context)
        _assert_controls_and_shutdown(context)
    print("DEPENDENCY_INJECTION_OK")


if __name__ == "__main__":
    run()
