from __future__ import annotations

lazy import sys
lazy from pathlib import Path
lazy from types import SimpleNamespace
lazy from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from azure_regions import (
    azure_region_identifiers,
    azure_region_options,
    azure_region_supports_hd_flash,
)
lazy from azure_speech import (
    AZURE_FEMALE_VOICES,
    AzureSpeechTTS,
    azure_female_voices,
    azure_hd_female_voices,
    azure_speech_error_message,
    build_azure_ssml,
    normalize_azure_region,
)
lazy from ui_localization import ui_text


def _assert_region_normalization() -> None:
    assert normalize_azure_region(" EastAsia ") == "eastasia"
    for invalid in ("", "https://eastasia", "eastasia/path", "a" * 40):
        try:
            normalize_azure_region(invalid)
        except ValueError:
            pass
        else:
            raise AssertionError(f"Invalid region accepted: {invalid!r}")


def _assert_region_catalog() -> None:
    all_regions = azure_region_identifiers()
    hd_regions = azure_region_identifiers(hd_only=True)
    assert len(all_regions) == len(set(all_regions)) == 33
    assert "eastasia" in all_regions
    assert "eastasia" not in hd_regions
    assert "southeastasia" in hd_regions
    assert (
        "東南亞 · southeastasia",
        "southeastasia",
    ) in azure_region_options("zh-TW", hd_only=True)
    assert (
        "东南亚 · southeastasia",
        "southeastasia",
    ) in azure_region_options("zh-CN", hd_only=True)
    assert (
        "Southeast Asia · southeastasia",
        "southeastasia",
    ) in azure_region_options("en", hd_only=True)
    assert (
        "東南アジア · southeastasia",
        "southeastasia",
    ) in azure_region_options("ja-JP", hd_only=True)


def _assert_female_voice_catalog() -> None:
    traditional = azure_female_voices("zh-TW")
    simplified = azure_female_voices("zh-CN")
    assert traditional[0] == "zh-TW-HsiaoChenNeural"
    assert simplified[0] == "zh-CN-XiaoxiaoNeural"
    assert "zh-CN-XiaoxiaoNeural" in traditional
    assert "zh-TW-HsiaoChenNeural" in simplified
    assert traditional == (
        *AZURE_FEMALE_VOICES["zh-TW"],
        *AZURE_FEMALE_VOICES["zh-CN"],
    )
    assert simplified == (
        *AZURE_FEMALE_VOICES["zh-CN"],
        *AZURE_FEMALE_VOICES["zh-TW"],
    )
    assert azure_female_voices("en")[0] == "en-US-AvaMultilingualNeural"
    assert azure_female_voices("ja-JP")[0] == "ja-JP-NanamiNeural"
    all_hd_voices = azure_hd_female_voices("zh-TW")
    non_flash_hd_voices = azure_hd_female_voices(
        "zh-TW",
        include_flash=False,
    )
    assert non_flash_hd_voices == (
        "zh-CN-Xiaochen:DragonHDLatestNeural",
        "zh-CN-Xiaoyue:DragonHDOmniLatestNeural",
        "zh-CN-Maroonallegro:DragonHDOmniLatestNeural",
    )
    assert all(":DragonHD" in voice for voice in all_hd_voices)
    assert all("Flash" not in voice for voice in non_flash_hd_voices)
    assert len(non_flash_hd_voices) < len(all_hd_voices)
    assert all(
        voice.startswith("zh-CN-")
        for voice in azure_hd_female_voices("zh-TW")
    )
    assert all(
        voice.startswith("zh-CN-")
        for voice in azure_hd_female_voices("zh-CN")
    )
    assert all(
        voice.startswith("en-US-")
        for voice in azure_hd_female_voices("en")
    )
    assert all(
        voice.startswith("ja-JP-")
        for voice in azure_hd_female_voices("ja-JP")
    )
    assert azure_region_supports_hd_flash("southeastasia")
    assert not azure_region_supports_hd_flash("centralindia")


def _assert_ssml_safety() -> None:
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


def _assert_localized_errors_and_ui() -> None:
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
    assert "automatically" in ui_text(
        "en",
        "secret_auto_save_hint",
        "fallback",
    )
    assert "自动安全保存" in ui_text(
        "zh-CN",
        "secret_auto_save_hint",
        "fallback",
    )
    assert "自動的に安全に保存" in ui_text(
        "ja-JP",
        "secret_auto_save_hint",
        "fallback",
    )


def _create_engine() -> tuple[AzureSpeechTTS, list[bool], list[str]]:
    engine = AzureSpeechTTS()
    finished: list[bool] = []
    failures: list[str] = []
    engine.finished.connect(lambda: finished.append(True))
    engine.failed.connect(failures.append)
    return engine, finished, failures


def _assert_missing_credentials_do_not_request(
    engine: AzureSpeechTTS,
    failures: list[str],
) -> None:
    engine.speak(
        "主上，妾在。",
        "",
        "",
        "zh-TW-HsiaoChenNeural",
    )
    assert "尚未設定" in failures[-1]


def _assert_invalid_region_fails_locally(
    engine: AzureSpeechTTS,
    failures: list[str],
) -> None:
    engine.speak(
        "Ready.",
        "not-a-real-key",
        "https://invalid-region",
        "en-US-AvaMultilingualNeural",
    )
    assert failures[-1] == "The Azure Speech region is invalid."
    failures.clear()


def _assert_successful_streaming_synthesis(
    engine: AzureSpeechTTS,
    finished: list[bool],
    failures: list[str],
) -> None:
    measured_latencies: list[float] = []
    engine.synthesis_latency_measured.connect(measured_latencies.append)
    callbacks: list[object] = []
    push_stream = SimpleNamespace()
    configured_formats: list[object] = []
    spoken_ssml: list[str] = []

    class FakeSpeechConfig:
        def __init__(self, subscription: str, region: str) -> None:
            assert subscription == "not-a-real-key"
            assert region == "eastasia"

        def set_speech_synthesis_output_format(self, value: object) -> None:
            configured_formats.append(value)

    class FakeFuture:
        def get(self) -> object:
            return SimpleNamespace(reason="completed")

    class FakeSynthesizer:
        def __init__(self, **kwargs: object) -> None:
            assert kwargs["audio_config"].stream is push_stream

        def speak_ssml_async(self, ssml: str) -> FakeFuture:
            spoken_ssml.append(ssml)
            callbacks[0].write(memoryview(b"\x01\x00" * 480))
            callbacks[0].close()
            return FakeFuture()

    def push_audio_output_stream(callback: object) -> object:
        callbacks.append(callback)
        return push_stream

    fake_sdk = SimpleNamespace(
        SpeechConfig=FakeSpeechConfig,
        SpeechSynthesisOutputFormat=SimpleNamespace(
            Raw24Khz16BitMonoPcm="raw-24khz-pcm16"
        ),
        SpeechSynthesizer=FakeSynthesizer,
        ResultReason=SimpleNamespace(Canceled="canceled"),
        audio=SimpleNamespace(
            PushAudioOutputStream=push_audio_output_stream,
            PushAudioOutputStreamCallback=object,
            AudioOutputConfig=lambda stream: SimpleNamespace(stream=stream),
        ),
    )

    def fake_playback(read_chunk, *_args, on_first_audio=None, **_kwargs):
        assert on_first_audio is not None
        buffer = bytearray(1_024)
        assert read_chunk(buffer) == 960
        assert read_chunk(buffer) == 0
        on_first_audio()

    with (
        patch("azure_speech.speechsdk", fake_sdk),
        patch(
            "azure_speech.play_pcm16_stream_with_visemes",
            side_effect=fake_playback,
        ) as playback,
    ):
        engine._run(
            "主上，妾在。",
            "not-a-real-key",
            "eastasia",
            "zh-TW-HsiaoChenNeural",
        )

    playback.assert_called_once()
    assert configured_formats == ["raw-24khz-pcm16"]
    assert "主上，妾在。" in spoken_ssml[0]
    assert finished == [True]
    assert not failures
    assert engine.last_synthesis_latency_ms is not None
    assert measured_latencies == [engine.last_synthesis_latency_ms]


def run() -> None:
    _assert_region_normalization()
    _assert_region_catalog()
    _assert_female_voice_catalog()
    _assert_ssml_safety()
    _assert_localized_errors_and_ui()
    engine, finished, failures = _create_engine()
    _assert_missing_credentials_do_not_request(engine, failures)
    _assert_invalid_region_fails_locally(engine, failures)
    _assert_successful_streaming_synthesis(engine, finished, failures)
    print("AZURE_SPEECH_OK")


if __name__ == "__main__":
    run()
