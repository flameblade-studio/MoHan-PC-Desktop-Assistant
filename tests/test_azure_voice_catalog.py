from __future__ import annotations

lazy import sys
lazy import threading
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


def _assert_invalidated_query_cannot_repopulate_cache() -> None:
    entered = threading.Event()
    release = threading.Event()

    class BlockingFuture:
        def get(self) -> object:
            entered.set()
            if not release.wait(timeout=2.0):
                raise TimeoutError("catalog test did not release")
            return SimpleNamespace(
                voices=(
                    _voice("zh-TW-NewWomanNeural", "zh-TW", "Female"),
                )
            )

    class BlockingSynthesizer:
        def __init__(self, **_kwargs: object) -> None:
            pass

        def get_voices_async(self) -> BlockingFuture:
            return BlockingFuture()

    fake_sdk = SimpleNamespace(
        SpeechConfig=lambda **kwargs: SimpleNamespace(**kwargs),
        SpeechSynthesizer=BlockingSynthesizer,
    )
    service = AzureVoiceCatalogService(sdk_loader=lambda: fake_sdk)
    results: list[object] = []
    worker = threading.Thread(
        target=lambda: results.append(
            service.query(
                "superseded-secret",
                "eastasia",
                "zh-TW",
                hd_only=False,
            )
        ),
        daemon=True,
    )
    worker.start()
    assert entered.wait(timeout=1.0)
    service.invalidate()
    release.set()
    worker.join(timeout=1.0)

    assert not worker.is_alive()
    assert len(results) == 1
    assert service._cache == {}


def run() -> None:
    FakeSynthesizer.query_count = 0
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
    same_credentials = service.query(
        "secret-never-cached",
        "westus2",
        "zh-TW",
        hd_only=True,
    )
    assert same_credentials is hd
    assert FakeSynthesizer.query_count == 2

    different_credentials = service.query(
        "a-different-secret",
        "westus2",
        "zh-TW",
        hd_only=True,
    )
    assert different_credentials is hd
    assert FakeSynthesizer.query_count == 2

    service.invalidate("westus2")
    refreshed_credentials = service.query(
        "a-different-secret",
        "westus2",
        "zh-TW",
        hd_only=True,
    )
    assert refreshed_credentials is not hd
    assert FakeSynthesizer.query_count == 3

    cache_representation = repr(service._cache)
    assert "secret-never-cached" not in cache_representation
    assert "a-different-secret" not in cache_representation
    assert "credential" not in repr(service._cache).lower()
    _assert_invalidated_query_cannot_repopulate_cache()
    print("AZURE_VOICE_CATALOG_OK")


if __name__ == "__main__":
    run()
