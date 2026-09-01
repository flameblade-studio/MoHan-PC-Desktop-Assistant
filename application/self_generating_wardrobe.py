from __future__ import annotations

lazy import copy
lazy import json
lazy import re
lazy import shutil
lazy from dataclasses import dataclass, replace
lazy from datetime import datetime
lazy from pathlib import Path
lazy from typing import Callable, Protocol

lazy from application.outfit_pack_builder import build_outfit_pack
lazy from application.wardrobe_storage import WardrobeStorageGuard
lazy from domain.outfit_pack import (
    POSE_ATLAS_SILHOUETTES,
    REQUIRED_SILHOUETTES,
    OutfitPack,
    OutfitPackError,
    install_outfit_pack,
    validated_asset_dimensions,
)

JOB_ID = re.compile(r"[a-z0-9](?:[a-z0-9-]{0,46}[a-z0-9])?\Z")
GENERATED_PACK_PREFIX = "generated-"
GENERATABLE_APPEARANCE_CATEGORIES = frozenset(
    {
        "garment",
        "hairstyle",
        "headwear",
        "weapon",
        "handheld",
        "jewelry",
        "foreground-effect",
    }
)


@dataclass(frozen=True, slots=True)
class FashionTrendSignal:
    source_url: str
    title: str
    abstract_traits: tuple[str, ...]
    license_note: str


@dataclass(frozen=True, slots=True)
class OutfitCreationRequest:
    job_id: str
    language: str
    weather: str
    temperature_c: float
    mood: str
    occasion: str
    creative_direction: str
    requested_at: datetime
    last_generated_at: datetime | None = None
    requested_categories: frozenset[str] = frozenset({"garment"})
    accessory_direction: str = ""
    user_initiated: bool = False

    def __post_init__(self) -> None:
        unknown = self.requested_categories - GENERATABLE_APPEARANCE_CATEGORIES
        if unknown:
            raise ValueError("Unknown generated appearance category.")
        if not self.requested_categories:
            raise ValueError("At least one appearance category is required.")


@dataclass(frozen=True, slots=True)
class GeneratedOutfitDraft:
    manifest: dict[str, object]
    assets: frozendict[str, bytes]
    generation_record: frozendict[str, object]


@dataclass(frozen=True, slots=True)
class OutfitGenerationPolicy:
    enabled: bool = False
    trend_search_enabled: bool = False
    install_after_audit: bool = True


@dataclass(frozen=True, slots=True)
class GeneratedOutfitResult:
    status: str
    job_directory: Path
    package_path: Path | None
    installed_pack: OutfitPack | None
    issues: tuple[str, ...]


class FashionTrendScout(Protocol):
    def discover(
        self,
        request: OutfitCreationRequest,
    ) -> tuple[FashionTrendSignal, ...]:
        raise NotImplementedError


FashionTrendScoutFactory = Callable[[str, str], FashionTrendScout]


class OutfitDraftGenerator(Protocol):
    def create(
        self,
        request: OutfitCreationRequest,
        trends: tuple[FashionTrendSignal, ...],
        required_views: tuple[str, ...],
    ) -> GeneratedOutfitDraft:
        raise NotImplementedError


class GeneratedOutfitAuditor(Protocol):
    def audit(
        self,
        job_directory: Path,
        manifest: dict[str, object],
    ) -> tuple[str, ...]:
        raise NotImplementedError


def _contextualized_request(
    request: OutfitCreationRequest,
) -> OutfitCreationRequest:
    if request.weather not in {"rain", "storm"}:
        return request
    direction = request.accessory_direction.strip() or (
        "Create an original handheld oil-paper umbrella with an ink-wash "
        "landscape mood; include anatomically valid grip, occlusion, and "
        "all required viewing angles. Do not copy an existing product."
    )
    return replace(
        request,
        requested_categories=request.requested_categories | {"handheld"},
        accessory_direction=direction,
    )


def _require_requested_categories(
    request: OutfitCreationRequest,
    manifest: dict[str, object],
) -> None:
    group_for = {
        "garment": "looks",
        "hairstyle": "hairstyles",
        "headwear": "headwear",
        "weapon": "accessories",
        "handheld": "accessories",
        "jewelry": "accessories",
        "foreground-effect": "accessories",
    }
    ensembles = manifest.get("ensembles")
    if not isinstance(ensembles, list) or not ensembles:
        raise OutfitPackError("Generated appearance has no complete ensemble.")
    selections = ensembles[0].get("selections")
    if not isinstance(selections, dict):
        raise OutfitPackError("Generated appearance selections are missing.")
    accessories = manifest.get("accessories")
    accessory_kinds = {
        item.get("accessory_kind")
        for item in accessories
        if isinstance(item, dict)
    } if isinstance(accessories, list) else set()
    for category in request.requested_categories:
        group = manifest.get(group_for[category])
        if not isinstance(group, list) or not group:
            raise OutfitPackError(
                f"Generated appearance omitted requested category: {category}."
            )
        if (
            category in {"weapon", "handheld", "jewelry", "foreground-effect"}
            and category not in accessory_kinds
        ):
            raise OutfitPackError(
                f"Generated appearance omitted requested category: {category}."
            )
        if selections.get(category) is None:
            raise OutfitPackError(
                f"Generated ensemble did not select requested category: {category}."
            )


def _write_draft(job_directory: Path, draft: GeneratedOutfitDraft) -> Path:
    created = False
    try:
        job_directory.mkdir(parents=True, exist_ok=False)
        created = True
        asset_root = job_directory / "source"
        for archive_path, data in draft.assets.items():
            validated_asset_dimensions(archive_path, data)
            destination = (asset_root / Path(*archive_path.split("/"))).resolve()
            try:
                destination.relative_to(asset_root.resolve())
            except ValueError:
                raise OutfitPackError("Generated outfit asset escaped quarantine.") from None
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(data)
        manifest_path = job_directory / "authoring.json"
        manifest_path.write_text(
            json.dumps(draft.manifest, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        (job_directory / "generation-record.json").write_text(
            json.dumps(
                dict(draft.generation_record),
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            ),
            encoding="utf-8",
        )
        return manifest_path
    except (OSError, OutfitPackError):
        if created:
            shutil.rmtree(job_directory, ignore_errors=True)
        raise


def _generated_draft(
    request: OutfitCreationRequest,
    draft: GeneratedOutfitDraft,
) -> GeneratedOutfitDraft:
    manifest = copy.deepcopy(draft.manifest)
    manifest["id"] = f"{GENERATED_PACK_PREFIX}{request.job_id}"
    record = dict(draft.generation_record)
    record.update(
        {
            "appearance_origin": "mohan-autonomous-generation",
            "managed_by": "self-generating-wardrobe",
            "job_id": request.job_id,
        }
    )
    return GeneratedOutfitDraft(
        manifest,
        draft.assets,
        frozendict(record),
    )


class SelfGeneratingWardrobe:
    """Quarantine-first path from original design intent to a validated pack."""

    def __init__(
        self,
        quarantine_root: Path,
        outfit_store: Path,
        trend_scout: FashionTrendScout,
        generator: OutfitDraftGenerator,
        auditor: GeneratedOutfitAuditor,
        policy: OutfitGenerationPolicy,
        storage_guard: WardrobeStorageGuard,
    ) -> None:
        self.quarantine_root = Path(quarantine_root)
        self.outfit_store = Path(outfit_store)
        self.trend_scout = trend_scout
        self.generator = generator
        self.auditor = auditor
        self.policy = policy
        self.storage_guard = storage_guard

    def create(self, request: OutfitCreationRequest) -> GeneratedOutfitResult:
        if not self.policy.enabled:
            raise OutfitPackError("Self-generated outfits are not enabled.")
        if not JOB_ID.fullmatch(request.job_id):
            raise OutfitPackError("Invalid outfit generation job identifier.")
        request = _contextualized_request(request)
        storage = self.storage_guard.inspect(
            request.requested_at,
            request.last_generated_at,
            special_occasion=(
                request.user_initiated
                or request.occasion in {
                    "birthday", "christmas", "valentines",
                }
            ),
        )
        if not storage.allowed:
            return GeneratedOutfitResult(
                "capacity-blocked",
                self.quarantine_root / request.job_id,
                None,
                None,
                (storage.reason,),
            )
        job_directory = self.quarantine_root / request.job_id
        if job_directory.exists():
            raise OutfitPackError("Outfit generation job already exists.")
        generated_pack_id = f"{GENERATED_PACK_PREFIX}{request.job_id}"
        generated_destination = (
            self.outfit_store
            / "packages"
            / f"{generated_pack_id}.mohan-outfit"
        )
        if generated_destination.exists():
            raise OutfitPackError(
                "Generated appearance identity is already installed; "
                "existing content was preserved."
            )
        # 趨勢搜尋失敗時 discover() 會把 last_status 設成 "failed" 並回傳空
        # tuple，而那個狀態沒有任何消費者——付費影像生成照樣往下跑，使用者
        # 看到的仍是「使用趨勢搜尋生成成功」。空結果與失敗必須分開。
        trends: tuple = ()
        if self.policy.trend_search_enabled:
            trends = self.trend_scout.discover(request)
            status = getattr(self.trend_scout, "last_status", "")
            if status == "failed":
                raise OutfitPackError(
                    "趨勢搜尋失敗，已停止本次生成——避免在缺少趨勢輸入的情況下"
                    "呼叫付費影像生成並宣稱使用了趨勢。"
                )
        draft = _generated_draft(
            request,
            self.generator.create(
                request,
                trends,
                REQUIRED_SILHOUETTES,
            ),
        )
        _require_requested_categories(request, draft.manifest)
        manifest_path = _write_draft(job_directory, draft)
        issues = self.auditor.audit(job_directory, draft.manifest)
        if issues:
            (job_directory / "quarantined.json").write_text(
                json.dumps({"issues": issues}, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            return GeneratedOutfitResult(
                "quarantined",
                job_directory,
                None,
                None,
                issues,
            )
        pack_id = draft.manifest.get("id")
        pack_version = draft.manifest.get("pack_version")
        if not isinstance(pack_id, str) or not isinstance(pack_version, str):
            raise OutfitPackError("Generated outfit identity is missing.")
        package_path = job_directory / f"{pack_id}-{pack_version}.mohan-outfit"
        build_outfit_pack(
            manifest_path,
            job_directory / "source",
            package_path,
        )
        installed = None
        result_path = package_path
        if self.policy.install_after_audit:
            installed = install_outfit_pack(package_path, self.outfit_store)
            result_path = (
                self.outfit_store
                / "packages"
                / f"{installed.pack_id}.mohan-outfit"
            )
            if not result_path.is_file():
                raise OutfitPackError("Installed generated outfit is missing.")
            shutil.rmtree(job_directory / "source")
            package_path.unlink()
            (job_directory / "validated.json").write_text(
                json.dumps(
                    {
                        "pack_id": installed.pack_id,
                        "pack_version": installed.pack_version,
                        "installed_path": str(result_path),
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
        return GeneratedOutfitResult(
            "installed" if installed is not None else "validated",
            job_directory,
            result_path,
            installed,
            (),
        )


def required_generation_views() -> tuple[str, ...]:
    """Expose the complete contract to generation providers."""

    assert set(POSE_ATLAS_SILHOUETTES).issubset(REQUIRED_SILHOUETTES)
    return REQUIRED_SILHOUETTES
