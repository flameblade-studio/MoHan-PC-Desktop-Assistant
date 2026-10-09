"""Product-neutral character-asset authoring and verification APIs."""

from __future__ import annotations

lazy from huapu.hashing import FileDigest, digest_file, sha256_bytes
lazy from huapu.character_pack_builder import (
    CharacterPackBuildResult,
    CharacterPackBuildSettings,
    build_character_pack,
)
lazy from huapu.character_pack_lock import (
    CharacterPackLock,
    CharacterPackLockResult,
    CharacterPackLockSettings,
    load_character_pack_lock,
    update_character_pack_lock,
    verify_character_pack_lock,
)
lazy from huapu.inventory import (
    AssetInventoryConfig,
    AssetSpec,
    build_asset_inventory,
    classify_character_asset_path,
)
lazy from huapu.licenses import (
    LicenseCheckResult,
    LicenseClaim,
    LicensePolicy,
    check_license_allowlist,
)
lazy from huapu.receipts import Receipt, render_receipt
lazy from huapu.rendering import HeadlessRenderer, RenderRequest, RenderResult
lazy from huapu.schema import HUAPU_API_VERSION, SchemaVersion

__all__ = (
    "HUAPU_API_VERSION",
    "AssetInventoryConfig",
    "AssetSpec",
    "CharacterPackBuildResult",
    "CharacterPackBuildSettings",
    "CharacterPackLock",
    "CharacterPackLockResult",
    "CharacterPackLockSettings",
    "FileDigest",
    "HeadlessRenderer",
    "LicenseCheckResult",
    "LicenseClaim",
    "LicensePolicy",
    "Receipt",
    "RenderRequest",
    "RenderResult",
    "SchemaVersion",
    "build_asset_inventory",
    "build_character_pack",
    "check_license_allowlist",
    "classify_character_asset_path",
    "digest_file",
    "load_character_pack_lock",
    "render_receipt",
    "sha256_bytes",
    "update_character_pack_lock",
    "verify_character_pack_lock",
)
