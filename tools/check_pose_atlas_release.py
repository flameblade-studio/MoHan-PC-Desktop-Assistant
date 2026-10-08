"""Run the MoHan PoseAtlas release gate through product-neutral Huapu orchestration."""

from __future__ import annotations

lazy import argparse
lazy import os
lazy import sys
lazy from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

lazy from huapu import pose_release as _core
lazy from tools import huapu_mohan_pose_release as _adapter

TRUE_VALUES = frozenset({"1", "true", "yes", "on"})
SummaryReport = _adapter.SummaryReport


def requires_v4_gate(version: str, explicit_flag: bool = False) -> bool:
    return _core.requires_release_gate(
        version,
        minimum=(4, 0, 0),
        explicit_flag=explicit_flag,
    )


def run_preflight(
    version: str,
    asset_root: Path,
    audit_evidence_path: Path,
    *,
    explicit_v4: bool = False,
) -> tuple[int, str]:
    return _core.run_release_preflight(
        version,
        asset_root,
        audit_evidence_path,
        minimum=(4, 0, 0),
        release_audit=_adapter.run_mohan_release_audit,
        explicit_flag=explicit_v4,
    )


_read_bundle = _core._read_bundle
_blocked = _core._blocked
_json = _core._json


def _environment_v4_flag() -> bool:
    value = os.environ.get("MOHAN_FULL_BODY_V4", "").strip().lower()
    if not value:
        return False
    if value not in TRUE_VALUES:
        raise ValueError("invalid_full_body_v4_flag")
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", required=True)
    parser.add_argument("--asset-root", type=Path, required=True)
    parser.add_argument("--audit-evidence", type=Path, required=True)
    parser.add_argument("--full-body-v4", action="store_true")
    args = parser.parse_args(argv)
    try:
        explicit = args.full_body_v4 or _environment_v4_flag()
        code, output = run_preflight(
            args.version,
            args.asset_root,
            args.audit_evidence,
            explicit_v4=explicit,
        )
    except ValueError as error:
        code, output = 2, _blocked(str(error))
    print(output)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
