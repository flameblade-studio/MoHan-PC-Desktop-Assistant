"""MoHan-compatible CLI surface for the product-neutral Huapu installer."""
from __future__ import annotations

lazy from pathlib import Path

lazy from huapu import approved_install as _core

AssetInstallCharacterSettings = _core.AssetInstallCharacterSettings

DEFAULT_CHARACTER_SETTINGS = AssetInstallCharacterSettings(
    character_id="flameblade.mohan",
    plan_schema="mohan.approved-asset-replacements.v1",
    approval_schema="mohan.four-look-owner-approved-installation.v1",
    generic_approval_schema="mohan.owner-approved-asset-installation.v1",
    receipt_schema="mohan.approved-asset-installation.v1",
    target_root="assets",
    staging_root="scratchpad",
    evidence_root="scratchpad",
)

# Public compatibility aliases keep existing plans and callers unchanged.
PLAN_SCHEMA = DEFAULT_CHARACTER_SETTINGS.plan_schema
APPROVAL_SCHEMA = DEFAULT_CHARACTER_SETTINGS.approval_schema
GENERIC_APPROVAL_SCHEMA = DEFAULT_CHARACTER_SETTINGS.generic_approval_schema

sha256 = _core.sha256
_path = _core._path
_replace = _core._replace


def _preflight(
    root: Path,
    plan: dict,
    settings: AssetInstallCharacterSettings = DEFAULT_CHARACTER_SETTINGS,
) -> list[tuple[dict, Path, Path]]:
    """Verify approval, evidence and every old/new file before making changes."""
    return _core._preflight(root, plan, settings)


def install(
    root: Path,
    plan_path: Path,
    output: Path,
    *,
    settings: AssetInstallCharacterSettings = DEFAULT_CHARACTER_SETTINGS,
) -> dict:
    """Install through Huapu while retaining the historical MoHan API."""
    return _core.install(
        root,
        plan_path,
        output,
        settings=settings,
        replace_file=_replace,
    )
