from __future__ import annotations

lazy import sys
lazy import threading
lazy import time
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
    _PushAudioReader,
    _SynthesisRequest,
    azure_female_voices,
    azure_hd_female_voices,
    azure_speech_error_message,
    build_azure_ssml,
    normalize_azure_region,
)
lazy from azure_voice_catalog import AzureVoiceCatalog
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
    assert all(voice.startswith("zh-CN-") for voice in azure_hd_female_voices("zh-TW"))
    assert all(voice.startswith("zh-CN-") for voice in azure_hd_female_voices("zh-CN"))
    assert all(voice.startswith("en-US-") for voice in azure_hd_female_voices("en"))
    assert all(voice.startswith("ja-JP-") for voice in azure_hd_female_voices("ja-JP"))
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
    assert not hasattr(AzureSpeechTTS, "register_verified_voices")


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
    assert ui_text("en", "azure_engine", "fallback") == ("Azure Speech (Preview)")
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


def _assert_cross_language_voice_uses_ui_error_locale() -> None:
    engine, _finished, failures = _create_engine()
    engine.speak(
        "跨語系測試。",
        "",
        "",
        "zh-CN-XiaoxiaoNeural",
        "zh-TW",
    )
    assert "金鑰" in failures[-1]
    assert "密钥" not in failures[-1]


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
            _SynthesisRequest(
                text="主上，妾在。",
                api_key="not-a-real-key",
                region="eastasia",
                voice="zh-TW-HsiaoChenNeural",
                locale="zh-TW",
            ),
            0,
        )

    playback.assert_called_once()
    assert configured_formats == ["raw-24khz-pcm16"]
    assert "主上，妾在。" in spoken_ssml[0]
    assert finished == [True]
    assert not failures
    assert engine.last_synthesis_latency_ms is not None
    assert measured_latencies == [engine.last_synthesis_latency_ms]


def _assert_operation_ids_are_monotonic() -> None:
    engine = AzureSpeechTTS()
    operation_ids: list[int] = []
    engine.operation_started.connect(operation_ids.append)
    with patch("azure_speech.threading.Thread") as thread_type:
        engine.speak(
            "第一輪",
            "not-a-real-key",
            "eastasia",
            "zh-TW-HsiaoChenNeural",
        )
        engine.speak(
            "第二輪",
            "not-a-real-key",
            "eastasia",
            "zh-TW-HsiaoChenNeural",
        )

    assert operation_ids == [1, 2]
    assert thread_type.call_count == 2


def _assert_new_operation_cancels_previous_playback() -> None:
    engine = AzureSpeechTTS()
    operation_ids: list[int] = []
    engine.operation_started.connect(operation_ids.append)
    reader = _PushAudioReader()
    synthesizer = SimpleNamespace(stop_speaking_async=lambda: None)
    stopped: list[bool] = []
    synthesizer.stop_speaking_async = lambda: stopped.append(True)
    reader.write(memoryview(b"\x01\x00" * 480))
    engine._active_reader = reader
    engine._active_synthesizer = synthesizer

    with patch("azure_speech.threading.Thread"):
        engine.speak(
            "新語音",
            "not-a-real-key",
            "eastasia",
            "zh-TW-HsiaoChenNeural",
        )

    assert operation_ids == [1]
    assert reader.read(bytearray(960)) == 0
    assert stopped == [True]
    assert engine._active_reader is None
    assert engine._active_synthesizer is None


def _assert_stale_operation_events_are_suppressed() -> None:
    engine = AzureSpeechTTS()
    started_operations: list[int] = []
    operation_events: list[tuple[object, ...]] = []
    legacy_events: list[tuple[object, ...]] = []
    engine.operation_started.connect(started_operations.append)
    engine.operation_synthesis_latency_measured.connect(
        lambda operation_id, latency: operation_events.append((
            "latency",
            operation_id,
            latency,
        ))
    )
    engine.operation_viseme_cue.connect(
        lambda operation_id, level, vowel: operation_events.append((
            "viseme",
            operation_id,
            level,
            vowel,
        ))
    )
    engine.operation_finished.connect(
        lambda operation_id: operation_events.append(("finished", operation_id))
    )
    engine.operation_failed.connect(
        lambda operation_id, message: operation_events.append((
            "failed",
            operation_id,
            message,
        ))
    )
    engine.synthesis_latency_measured.connect(
        lambda latency: legacy_events.append(("latency", latency))
    )
    engine.viseme_cue.connect(
        lambda level, vowel: legacy_events.append(("viseme", level, vowel))
    )
    engine.finished.connect(lambda: legacy_events.append(("finished",)))
    engine.failed.connect(lambda message: legacy_events.append(("failed", message)))

    with patch("azure_speech.threading.Thread"):
        engine.speak(
            "舊語音",
            "not-a-real-key",
            "eastasia",
            "zh-TW-HsiaoChenNeural",
        )
        engine.speak(
            "新語音",
            "not-a-real-key",
            "eastasia",
            "zh-TW-HsiaoChenNeural",
        )
    old_operation, current_operation = started_operations

    engine._record_synthesis_latency(old_operation, 0.0)
    engine._emit_viseme(old_operation, 0.9, "A")
    engine._emit_finished(old_operation)
    engine._emit_failed(old_operation, "stale failure")
    assert operation_events == []
    assert legacy_events == []

    engine._record_synthesis_latency(current_operation, 0.0)
    engine._emit_viseme(current_operation, 0.4, "I")
    engine._emit_finished(current_operation)
    engine._emit_failed(current_operation, "current failure")
    assert [event[0] for event in operation_events] == [
        "latency",
        "viseme",
        "finished",
        "failed",
    ]
    assert [event[0] for event in legacy_events] == [
        "latency",
        "viseme",
        "finished",
        "failed",
    ]


def _assert_audio_queue_is_bounded_under_pressure() -> None:
    reader = _PushAudioReader()
    payload = b"\x01\x00" * (65_536 * 80 // 2)
    writer = threading.Thread(
        target=reader.write,
        args=(memoryview(payload),),
        daemon=True,
    )
    writer.start()
    buffer = bytearray(65_536)
    consumed = bytearray()
    while writer.is_alive() or not reader._chunks.empty():
        read = reader.read(buffer)
        assert read <= len(buffer)
        consumed.extend(buffer[:read])
        assert reader._chunks.qsize() <= reader._chunks.maxsize == 64
    writer.join(timeout=1.0)
    reader.close()

    assert not writer.is_alive()
    assert bytes(consumed) == payload
    assert reader.read(buffer) == 0


class _CredentialBoundCatalogService:
    def __init__(self, dynamic_voice: str) -> None:
        self.dynamic_voice = dynamic_voice
        self.queries: list[tuple[str, str, str, bool]] = []

    def query(
        self,
        api_key: str,
        region: str,
        language: str,
        *,
        hd_only: bool,
    ) -> AzureVoiceCatalog:
        self.queries.append((api_key, region, language, hd_only))
        expected_hd_only = ":DragonHD" in self.dynamic_voice
        permitted = (
            api_key == "key-a"
            and region == "eastasia"
            and hd_only == expected_hd_only
        )
        return AzureVoiceCatalog(
            region=region,
            language=language,
            hd_only=hd_only,
            voices=(self.dynamic_voice,) if permitted else ("zh-CN-OtherNeural",),
            source="azure",
        )

    def invalidate(self, _region: str | None = None) -> None:
        return


def _assert_dynamic_voice_trust_is_credential_bound() -> None:
    dynamic_voice = "zh-CN-XiaobeiNeural"
    catalog_service = _CredentialBoundCatalogService(dynamic_voice)
    engine = AzureSpeechTTS(catalog_service=catalog_service)

    verified = engine._verified_ssml_for_request(
        "已驗證",
        "key-a",
        "eastasia",
        dynamic_voice,
    )
    assert dynamic_voice in verified.decode("utf-8")
    for api_key, region in (
        ("key-b", "eastasia"),
        ("key-a", "westus2"),
    ):
        try:
            engine._verified_ssml_for_request(
                "不可沿用",
                api_key,
                region,
                dynamic_voice,
            )
        except ValueError as exc:
            assert str(exc) == "unsupported_voice"
        else:
            raise AssertionError("Dynamic voice trust crossed Azure resources")

    assert catalog_service.queries == [
        ("key-a", "eastasia", "zh-CN", False),
        ("key-b", "eastasia", "zh-CN", False),
        ("key-a", "westus2", "zh-CN", False),
    ]
    assert not hasattr(engine, "_verified_dynamic_voices")
    assert "key-a" not in repr(engine.__dict__)

    hd_voice = "zh-CN-Xiaobei:DragonHDLatestNeural"
    hd_catalog_service = _CredentialBoundCatalogService(hd_voice)
    hd_engine = AzureSpeechTTS(catalog_service=hd_catalog_service)
    hd_ssml = hd_engine._verified_ssml_for_request(
        "HD 已驗證",
        "key-a",
        "eastasia",
        hd_voice,
    )
    assert hd_voice in hd_ssml.decode("utf-8")
    assert hd_catalog_service.queries == [
        ("key-a", "eastasia", "zh-CN", True),
    ]


class _BlockingCatalogService:
    def __init__(self, dynamic_voice: str) -> None:
        self.dynamic_voice = dynamic_voice
        self.entered = threading.Event()
        self.release = threading.Event()
        self.query_thread_id: int | None = None

    def query(
        self,
        _api_key: str,
        region: str,
        language: str,
        *,
        hd_only: bool,
    ) -> AzureVoiceCatalog:
        self.query_thread_id = threading.get_ident()
        self.entered.set()
        if not self.release.wait(timeout=2.0):
            raise TimeoutError("test catalog release timed out")
        return AzureVoiceCatalog(
            region=region,
            language=language,
            hd_only=hd_only,
            voices=(self.dynamic_voice,),
            source="azure",
        )

    def invalidate(self, _region: str | None = None) -> None:
        return


class _ObservedAzureSpeechTTS(AzureSpeechTTS):
    def __init__(self, catalog_service: _BlockingCatalogService) -> None:
        super().__init__(catalog_service=catalog_service)
        self.worker_finished = threading.Event()

    def _run(
        self,
        request: _SynthesisRequest,
        operation_id: int,
    ) -> None:
        try:
            super()._run(request, operation_id)
        finally:
            self.worker_finished.set()


def _assert_dynamic_voice_query_does_not_block_speak() -> None:
    dynamic_voice = "zh-CN-XiaobeiNeural"
    catalog_service = _BlockingCatalogService(dynamic_voice)
    engine = _ObservedAzureSpeechTTS(catalog_service)
    caller_thread_id = threading.get_ident()

    started = time.perf_counter()
    engine.speak("背景驗證", "key-a", " EastAsia ", dynamic_voice)
    elapsed = time.perf_counter() - started

    assert elapsed < 0.25
    assert catalog_service.entered.wait(timeout=1.0)
    assert catalog_service.query_thread_id != caller_thread_id
    engine.stop()
    catalog_service.release.set()
    assert engine.worker_finished.wait(timeout=1.0)


def run() -> None:
    _assert_region_normalization()
    _assert_region_catalog()
    _assert_female_voice_catalog()
    _assert_ssml_safety()
    _assert_localized_errors_and_ui()
    _assert_cross_language_voice_uses_ui_error_locale()
    engine, _finished, failures = _create_engine()
    _assert_missing_credentials_do_not_request(engine, failures)
    _assert_invalid_region_fails_locally(engine, failures)
    streaming_engine, streaming_finished, streaming_failures = _create_engine()
    _assert_successful_streaming_synthesis(
        streaming_engine,
        streaming_finished,
        streaming_failures,
    )
    _assert_operation_ids_are_monotonic()
    _assert_new_operation_cancels_previous_playback()
    _assert_stale_operation_events_are_suppressed()
    _assert_audio_queue_is_bounded_under_pressure()
    _assert_dynamic_voice_trust_is_credential_bound()
    _assert_dynamic_voice_query_does_not_block_speak()
    print("AZURE_SPEECH_OK")


def test_azure_speech_regressions() -> None:
    run()


if __name__ == "__main__":
    run()
