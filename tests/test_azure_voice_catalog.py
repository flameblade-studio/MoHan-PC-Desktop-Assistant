from __future__ import annotations

lazy import sys
lazy from pathlib import Path
lazy from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from azure_voice_catalog import AzureVoiceCatalogService


class FakeSynthesizer:
    voices: tuple[object, ...] = ()
    query_count = 0

    def __init__(self, **_kwargs: object) -> None:
        pass

    def get_voices_async(self):
        type(self).query_count += 1
        return SimpleNamespace(
            get=lambda: SimpleNamespace(voices=self.voices)
        )


def _voice(short_name: str, locale: str, gender: str) -> object:
    return SimpleNamespace(
        short_name=short_name,
        locale=locale,
        gender=SimpleNamespace(name=gender),
    )


def run() -> None:
    FakeSynthesizer.voices = (
        _voice("zh-CN-NewWomanNeural", "zh-CN", "Female"),
        _voice("zh-TW-NewWomanNeural", "zh-TW", "Female"),
        _voice("zh-CN-NewManNeural", "zh-CN", "Male"),
        _voice("zh-CN-NewWoman:MAI-Voice-2", "zh-CN", "Female"),
        _voice(
            "zh-CN-NewWoman:DragonHDLatestNeural",
            "zh-CN",
            "Female",
        ),
        _voice(
            "zh-CN-NewWoman:DragonHDFlashLatestNeural",
            "zh-CN",
            "Female",
        ),
    )
    fake_sdk = SimpleNamespace(
        SpeechConfig=lambda **kwargs: SimpleNamespace(**kwargs),
        SpeechSynthesizer=FakeSynthesizer,
    )
    now = [10.0]
    service = AzureVoiceCatalogService(
        cache_seconds=60.0,
        clock=lambda: now[0],
        sdk_loader=lambda: fake_sdk,
    )
    normal = service.query(
        "secret-never-cached",
        "westus2",
        "zh-TW",
        hd_only=False,
    )
    assert normal.voices == (
        "zh-TW-NewWomanNeural",
        "zh-CN-NewWomanNeural",
    )
    hd = service.query(
        "secret-never-cached",
        "westus2",
        "zh-TW",
        hd_only=True,
    )
    assert hd.voices == ("zh-CN-NewWoman:DragonHDLatestNeural",)
    assert all("Man" not in voice for voice in (*normal.voices, *hd.voices))
    service.query(
        "a-different-secret",
        "westus2",
        "zh-TW",
        hd_only=True,
    )
    assert FakeSynthesizer.query_count == 2
    assert all(
        "secret" not in repr(key)
        for key in service._cache
    )
    print("AZURE_VOICE_CATALOG_OK")


if __name__ == "__main__":
    run()
