from __future__ import annotations

lazy import json
lazy import sys
lazy from dataclasses import replace
lazy from datetime import datetime, timezone
lazy from pathlib import Path
lazy from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from application.self_generating_wardrobe import (
    FashionTrendSignal,
    GeneratedOutfitDraft,
    OutfitCreationRequest,
    OutfitGenerationPolicy,
    SelfGeneratingWardrobe,
    required_generation_views,
)
lazy from application.wardrobe_storage import WardrobeStorageGuard
lazy from domain.outfit_pack import REQUIRED_SILHOUETTES, OutfitPackError
lazy from tests.test_outfit_pack import _manifest, _png


class Scout:
    def discover(self, request: OutfitCreationRequest) -> tuple[FashionTrendSignal, ...]:
        return (
            FashionTrendSignal(
                "https://example.test/trend",
                "Season palette",
                ("soft-blue", "light-fabric"),
                "abstract trend only",
            ),
        )


class Generator:
    def __init__(self) -> None:
        self.requests: list[OutfitCreationRequest] = []

    def create(
        self,
        request: OutfitCreationRequest,
        trends: tuple[FashionTrendSignal, ...],
        required_views: tuple[str, ...],
    ) -> GeneratedOutfitDraft:
        assert required_views == REQUIRED_SILHOUETTES
        self.requests.append(request)
        manifest, assets = _manifest(_png())
        return GeneratedOutfitDraft(
            manifest,
            frozendict(assets),
            frozendict({"provider": "test", "trend_count": len(trends)}),
        )


class Auditor:
    def __init__(self, issues: tuple[str, ...] = ()) -> None:
        self.issues = issues

    def audit(
        self,
        job_directory: Path,
        manifest: dict[str, object],
    ) -> tuple[str, ...]:
        assert (job_directory / "source").is_dir()
        return self.issues


def request(job_id: str) -> OutfitCreationRequest:
    return OutfitCreationRequest(
        job_id,
        "zh-TW",
        "clear",
        28.0,
        "cheerful",
        "everyday",
        "原創現代服裝",
        datetime(2026, 8, 15, tzinfo=timezone.utc),
    )


def run() -> None:
    assert required_generation_views() == REQUIRED_SILHOUETTES
    with TemporaryDirectory() as temporary:
        root = Path(temporary)
        store, drafts = root / "store", root / "drafts"
        wardrobe = SelfGeneratingWardrobe(
            drafts,
            store,
            Scout(),
            Generator(),
            Auditor(),
            OutfitGenerationPolicy(True, True, True),
            WardrobeStorageGuard(store, drafts),
        )
        result = wardrobe.create(request("summer-look"))
        assert result.status == "installed"
        assert result.package_path is not None and result.package_path.is_file()
        assert result.installed_pack is not None
        assert result.installed_pack.pack_id == "generated-summer-look"
        assert not (result.job_directory / "source").exists()
        assert (result.job_directory / "generation-record.json").is_file()
        assert (result.job_directory / "validated.json").is_file()
        rainy_generator = Generator()
        rainy_request = request("rain-look")
        rainy_request = replace(rainy_request, weather="rain")
        rainy = SelfGeneratingWardrobe(
            drafts,
            store,
            Scout(),
            rainy_generator,
            Auditor(),
            OutfitGenerationPolicy(True, False, True),
            WardrobeStorageGuard(store, drafts),
        ).create(rainy_request)
        assert rainy.status == "installed"
        assert rainy_generator.requests[0].requested_categories == frozenset(
            {"garment", "handheld"}
        )
        assert "oil-paper umbrella" in rainy_generator.requests[0].accessory_direction
        record = json.loads(
            (rainy.job_directory / "generation-record.json").read_text(
                encoding="utf-8"
            )
        )
        assert record["appearance_origin"] == "mohan-autonomous-generation"
        protected = store / "packages" / "generated-protected.mohan-outfit"
        protected.write_bytes(b"user-owned-content")
        try:
            SelfGeneratingWardrobe(
                drafts,
                store,
                Scout(),
                Generator(),
                Auditor(),
                OutfitGenerationPolicy(True, False, True),
                WardrobeStorageGuard(store, drafts),
            ).create(request("protected"))
        except OutfitPackError:
            pass
        else:
            raise AssertionError("generated content must not replace an existing pack")
        assert protected.read_bytes() == b"user-owned-content"
        blocked = SelfGeneratingWardrobe(
            drafts,
            store,
            Scout(),
            Generator(),
            Auditor(),
            OutfitGenerationPolicy(),
            WardrobeStorageGuard(store, drafts),
        )
        try:
            blocked.create(request("disabled-look"))
        except OutfitPackError:
            pass
        else:
            raise AssertionError("cost-bearing outfit generation requires enablement")
        failed = SelfGeneratingWardrobe(
            drafts,
            store,
            Scout(),
            Generator(),
            Auditor(("hand-audit",)),
            OutfitGenerationPolicy(True, False, True),
            WardrobeStorageGuard(store, drafts),
        ).create(request("failed-look"))
        assert failed.status == "quarantined"
        assert (failed.job_directory / "quarantined.json").is_file()
    print("SELF_GENERATING_WARDROBE_OK")


if __name__ == "__main__":
    run()
