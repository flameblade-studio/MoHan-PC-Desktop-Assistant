from __future__ import annotations

import io
import sys
import urllib.error
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from azure_speech import (
    AzureSpeechTTS,
    azure_female_voices,
    azure_speech_error_message,
    build_azure_ssml,
    normalize_azure_region,
)
from ui_localization import ui_text


class FakeResponse:
    def __init__(self, payload: bytes):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_args) -> None:
        return None

    def read(self) -> bytes:
        return self.payload


def run() -> None:
    assert normalize_azure_region(" EastAsia ") == "eastasia"
    for invalid in ("", "https://eastasia", "eastasia/path", "a" * 40):
        try:
            normalize_azure_region(invalid)
        except ValueError:
            pass
        else:
            raise AssertionError(f"Invalid region accepted: {invalid!r}")

    assert azure_female_voices("zh-TW")[0] == "zh-TW-HsiaoChenNeural"
    assert azure_female_voices("zh-CN")[0] == "zh-CN-XiaoxiaoNeural"
    assert azure_female_voices("en")[0] == "en-US-AvaMultilingualNeural"
    assert azure_female_voices("ja-JP")[0] == "ja-JP-NanamiNeural"

    ssml = build_azure_ssml(
        "主上 <妾在> & ready",
        "zh-TW-HsiaoChenNeural",
    ).decode("utf-8")
    assert "&lt;妾在&gt; &amp; ready" in ssml
    assert "xml:gender='Female'" in ssml
    try:
        build_azure_ssml("test", "zh-TW-YunJheNeural")
    except ValueError:
        pass
    else:
        raise AssertionError("A voice outside the female allowlist was accepted")

    assert "金鑰" in azure_speech_error_message(401, "secret")
    assert "額度" in azure_speech_error_message(429, "secret")
    assert "secret" not in azure_speech_error_message(500, "secret")
    assert "invalid" in azure_speech_error_message(
        401,
        "secret",
        "en-US",
    )
    assert "密钥" in azure_speech_error_message(
        401,
        "secret",
        "zh-CN",
    )
    assert "キー" in azure_speech_error_message(401, "secret", "ja-JP")
    assert ui_text("en", "azure_engine", "fallback") == (
        "Azure Speech (Preview)"
    )
    assert ui_text("zh-CN", "azure_remove_key", "fallback") == (
        "移除 Azure Speech 密钥"
    )

    engine = AzureSpeechTTS()
    finished: list[bool] = []
    failures: list[str] = []
    engine.finished.connect(lambda: finished.append(True))
    engine.failed.connect(failures.append)
    captured = {}

    with patch("azure_speech.urllib.request.urlopen") as no_request:
        engine.speak(
            "主上，妾在。",
            "",
            "",
            "zh-TW-HsiaoChenNeural",
        )
    no_request.assert_not_called()
    assert "尚未設定" in failures[-1]

    engine.speak(
        "Ready.",
        "not-a-real-key",
        "https://invalid-region",
        "en-US-AvaMultilingualNeural",
    )
    assert failures[-1] == "The Azure Speech region is invalid."
    failures.clear()

    def fake_urlopen(request, timeout):
        captured["request"] = request
        captured["timeout"] = timeout
        return FakeResponse(b"RIFF-test-wave")

    with (
        patch("azure_speech.urllib.request.urlopen", fake_urlopen),
        patch("azure_speech.play_wave_with_visemes") as playback,
    ):
        engine._run(
            "主上，妾在。",
            "not-a-real-key",
            "eastasia",
            "zh-TW-HsiaoChenNeural",
        )

    request = captured["request"]
    assert request.full_url == (
        "https://eastasia.tts.speech.microsoft.com/cognitiveservices/v1"
    )
    headers = dict(request.header_items())
    assert headers["Ocp-apim-subscription-key"] == "not-a-real-key"
    assert headers["X-microsoft-outputformat"] == (
        "riff-24khz-16bit-mono-pcm"
    )
    assert captured["timeout"] == 60
    playback.assert_called_once()
    assert finished == [True]
    assert not failures

    http_error = urllib.error.HTTPError(
        request.full_url,
        401,
        "Unauthorized",
        {},
        io.BytesIO(b"not-a-real-key"),
    )
    with patch(
        "azure_speech.urllib.request.urlopen",
        side_effect=http_error,
    ):
        engine._run(
            "主上，妾在。",
            "not-a-real-key",
            "eastasia",
            "zh-TW-HsiaoChenNeural",
        )
    assert "not-a-real-key" not in failures[-1]
    assert "金鑰" in failures[-1]

    print("AZURE_SPEECH_OK")


if __name__ == "__main__":
    run()
