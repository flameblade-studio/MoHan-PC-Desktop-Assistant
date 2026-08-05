from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from speech_providers import (
    AZURE_SPEECH_PROVIDER,
    LEGACY_WINDOWS_LOCAL_PROVIDER,
    OPENAI_REALTIME_PROVIDER,
    OPENAI_SPEECH_PROVIDER,
    SYSTEM_LOCAL_PROVIDER,
    WINDOWS_LOCAL_PROVIDER,
    OpenAISpeechProvider,
    SpeechProviderRegistry,
    SpeechRequest,
    WindowsSpeechProvider,
    create_builtin_speech_registry,
    migrate_speech_provider_setting,
    normalize_speech_provider_id,
)


class FakeLocalEngine:
    def __init__(self) -> None:
        self.calls: list[tuple[object, ...]] = []

    def speak(self, *args: object) -> None:
        self.calls.append(args)


class FakeCloudEngine(FakeLocalEngine):
    pass


class FakeSettings:
    def __init__(self, value: str):
        self.value = value
        self.writes: list[tuple[str, object]] = []

    def setting(self, key: str, default: object = None) -> object:
        del key, default
        return self.value

    def set_setting(self, key: str, value: object) -> None:
        self.writes.append((key, value))
        self.value = str(value)


def run() -> None:
    assert SYSTEM_LOCAL_PROVIDER == "system-local"
    assert LEGACY_WINDOWS_LOCAL_PROVIDER == "windows-local"
    assert normalize_speech_provider_id("windows-local") == (
        SYSTEM_LOCAL_PROVIDER
    )
    old_settings = FakeSettings("windows-local")
    assert migrate_speech_provider_setting(old_settings) == (
        SYSTEM_LOCAL_PROVIDER
    )
    assert old_settings.writes == [
        ("voice_engine", SYSTEM_LOCAL_PROVIDER)
    ]
    assert normalize_speech_provider_id("Windows 本機語音") == (
        WINDOWS_LOCAL_PROVIDER
    )
    assert normalize_speech_provider_id("Windows 本机语音") == (
        WINDOWS_LOCAL_PROVIDER
    )
    assert normalize_speech_provider_id("OpenAI natural voice") == (
        OPENAI_SPEECH_PROVIDER
    )
    assert normalize_speech_provider_id("unknown-provider") == (
        SYSTEM_LOCAL_PROVIDER
    )

    local = FakeLocalEngine()
    cloud = FakeCloudEngine()
    azure = FakeCloudEngine()
    registry = create_builtin_speech_registry(local, cloud, azure)
    assert registry.provider_ids() == (
        WINDOWS_LOCAL_PROVIDER,
        OPENAI_SPEECH_PROVIDER,
        AZURE_SPEECH_PROVIDER,
    )
    assert registry.output_provider_id(
        OPENAI_REALTIME_PROVIDER,
        realtime_running=False,
    ) == WINDOWS_LOCAL_PROVIDER
    assert registry.output_provider_id(
        OPENAI_REALTIME_PROVIDER,
        realtime_running=True,
    ) == OPENAI_SPEECH_PROVIDER
    assert registry.output_provider_id(
        OPENAI_REALTIME_PROVIDER,
        realtime_running=True,
        cloud_available=False,
    ) == WINDOWS_LOCAL_PROVIDER
    assert registry.output_provider_id(
        OPENAI_SPEECH_PROVIDER,
        realtime_running=False,
        cloud_available=False,
    ) == WINDOWS_LOCAL_PROVIDER
    assert registry.output_provider_id(
        AZURE_SPEECH_PROVIDER,
        realtime_running=False,
        configured_provider_ids=(WINDOWS_LOCAL_PROVIDER,),
    ) == WINDOWS_LOCAL_PROVIDER
    assert registry.output_provider_id(
        AZURE_SPEECH_PROVIDER,
        realtime_running=False,
        configured_provider_ids=(
            WINDOWS_LOCAL_PROVIDER,
            AZURE_SPEECH_PROVIDER,
        ),
    ) == AZURE_SPEECH_PROVIDER
    assert registry.fallback_provider_id(OPENAI_SPEECH_PROVIDER) == (
        WINDOWS_LOCAL_PROVIDER
    )
    assert registry.fallback_provider_id(WINDOWS_LOCAL_PROVIDER) is None

    request = SpeechRequest(
        text="主上，妾在。",
        voice="female-test",
        rate=-2,
        api_key="not-a-real-key",
        instructions="calm",
    )
    registry.provider(WINDOWS_LOCAL_PROVIDER).speak(request)
    registry.provider(OPENAI_SPEECH_PROVIDER).speak(request)
    registry.provider(AZURE_SPEECH_PROVIDER).speak(
        SpeechRequest(
            text=request.text,
            voice="zh-TW-HsiaoChenNeural",
            api_key=request.api_key,
            options={"region": "eastasia"},
        )
    )
    assert local.calls == [("主上，妾在。", "female-test", -2)]
    assert cloud.calls == [
        ("主上，妾在。", "not-a-real-key", "female-test", "calm")
    ]
    assert azure.calls == [
        (
            "主上，妾在。",
            "not-a-real-key",
            "eastasia",
            "zh-TW-HsiaoChenNeural",
        )
    ]

    assert WindowsSpeechProvider(local).capabilities.offline
    assert (
        WindowsSpeechProvider(local).capabilities.verified_female_catalog
    )
    assert not (
        OpenAISpeechProvider(cloud).capabilities.verified_female_catalog
    )
    assert OpenAISpeechProvider(cloud).capabilities.requires_api_key
    duplicate = SpeechProviderRegistry((WindowsSpeechProvider(local),))
    try:
        duplicate.register(WindowsSpeechProvider(local))
    except ValueError:
        pass
    else:
        raise AssertionError("Duplicate provider IDs must be rejected")

    print("SPEECH_PROVIDER_REGISTRY_OK")


if __name__ == "__main__":
    run()
