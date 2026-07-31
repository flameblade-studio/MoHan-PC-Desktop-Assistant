import threading
import sys
from pathlib import Path
from tempfile import NamedTemporaryFile
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from speech import SpeechListener


class CapturedThread:
    target = None
    args = ()

    def __init__(self, target, args, daemon):
        assert daemon
        CapturedThread.target = target
        CapturedThread.args = args

    def start(self):
        return None


def run() -> None:
    owner_thread = threading.get_ident()
    provider_calls: list[int] = []

    def provider(value):
        def read():
            provider_calls.append(threading.get_ident())
            return value
        return read

    listener = SpeechListener(
        Path("voice_listener.ps1"),
        api_key_provider=provider("sk-test"),
        recognition_mode_provider=provider("OpenAI 高準確辨識（推薦）"),
        transcription_model_provider=provider("gpt-4o-mini-transcribe"),
        transcription_language_provider=provider("zh"),
        transcription_prompt_provider=provider("繁中詞庫"),
        windows_fallback_provider=provider(False),
    )
    with patch("speech.threading.Thread", CapturedThread):
        listener.listen_once()
    assert provider_calls
    assert set(provider_calls) == {owner_thread}
    assert CapturedThread.args == (
        "sk-test",
        "gpt-4o-mini-transcribe",
        "zh",
        "繁中詞庫",
        False,
    )
    assert listener.is_recording
    listener.toggle_listening()
    assert listener._stop_recording.is_set()

    listener._busy.clear()
    listener._recording_active.clear()
    errors: list[str] = []
    no_key = SpeechListener(
        Path("voice_listener.ps1"),
        api_key_provider=lambda: "",
        recognition_mode_provider=lambda: "OpenAI 高準確辨識（推薦）",
        windows_fallback_provider=lambda: False,
    )
    no_key.failed.connect(errors.append)
    no_key.listen_once()
    assert errors and "未設定 OpenAI API 金鑰" in errors[-1]
    assert "備援目前已關閉" in errors[-1]
    assert not no_key.is_busy

    with NamedTemporaryFile(suffix=".wav", delete=False) as temp:
        audio_path = Path(temp.name)
        temp.write(b"RIFF-test")
    diagnostics: list[str] = []
    failures: list[str] = []
    worker = SpeechListener(Path("voice_listener.ps1"))
    worker._busy.set()
    worker.diagnostic_changed.connect(diagnostics.append)
    worker.failed.connect(failures.append)
    with (
        patch.object(worker, "_record_wav", return_value=audio_path),
        patch.object(
            worker,
            "_transcribe",
            side_effect=RuntimeError(
                "OpenAI 已成功連線，但沒有從這段錄音辨識出文字。"
            ),
        ),
    ):
        worker._listen_with_openai(
            "sk-test",
            "gpt-4o-mini-transcribe",
            "zh",
            "繁中詞庫",
            False,
        )
    assert diagnostics and "成功連線" in diagnostics[-1]
    assert failures and "備援目前已關閉" in failures[-1]
    assert not audio_path.exists()
    assert not worker.is_busy
    print("TRANSCRIPTION_CONTROL_OK")


if __name__ == "__main__":
    run()
