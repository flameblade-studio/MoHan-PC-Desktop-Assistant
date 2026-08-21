from __future__ import annotations

lazy import argparse
lazy import json
lazy import os
lazy import re
lazy import sys
lazy from dataclasses import dataclass
lazy from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

lazy from full_body_asset_audit import audit_full_body_assets
lazy from pose_atlas_manifest_builder import (
    PoseAtlasBuildConfig,
    build_pose_atlas_manifest,
)
lazy from pose_atlas_release_gate import (
    PoseAtlasAuditInputs,
    PoseLoadReleaseEvidence,
    audit_pose_atlas_release,
    manifest_sha256,
)

VERSION_PATTERN = re.compile(r"^(\d+)\.(\d+)\.(\d+)(?:-rc\.[1-9]\d*)?$")
TRUE_VALUES = frozenset({"1", "true", "yes", "on"})
VERSION_RANGE_LENGTH = 2


@dataclass(frozen=True, slots=True)
class SummaryReport:
    passed: bool
    problems: tuple[str, ...] = ()


def requires_v4_gate(version: str, explicit_flag: bool = False) -> bool:
    match = VERSION_PATTERN.fullmatch(version)
    if match is None:
        raise ValueError("invalid_release_version")
    return explicit_flag or tuple(int(value) for value in match.groups()) >= (4, 0, 0)


def run_preflight(
    version: str,
    asset_root: Path,
    audit_evidence_path: Path,
    *,
    explicit_v4: bool = False,
) -> tuple[int, str]:
    if not requires_v4_gate(version, explicit_v4):
        return 0, _json({"schema_version": 1, "status": "not-required", "version": version})
    try:
        bundle = _read_bundle(audit_evidence_path)
        config = _build_config(bundle)
    except (OSError, UnicodeError, json.JSONDecodeError, TypeError, ValueError):
        return 1, _blocked("audit_evidence_invalid")
    build = build_pose_atlas_manifest(asset_root, config)
    if not build.passed or build.manifest is None:
        codes = tuple(issue.code for issue in build.issues) or ("manifest_build_failed",)
        return 1, _blocked(*codes)
    evidence_by_view = dict(build.asset_evidence)
    body_report = audit_full_body_assets(
        tuple(
            evidence_by_view[record.view_id].evidence
            for record in build.records
            if evidence_by_view[record.view_id].evidence is not None
        )
    )
    try:
        identity = _summary(bundle, "identity")
        pose_atlas = _summary(bundle, "pose_atlas")
        load = _load_evidence(bundle, build.manifest)
    except (KeyError, TypeError, ValueError):
        return 1, _blocked("audit_evidence_incomplete")
    release_views = build.release_views()
    result = audit_pose_atlas_release(
        build.manifest,
        load,
        release_views,
        PoseAtlasAuditInputs(body_report, identity, pose_atlas),
    )
    return (0 if result.releasable else 1), result.to_json()


def _read_bundle(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        raise ValueError("unsupported_audit_evidence")
    return payload


def _build_config(bundle: dict[str, object]) -> PoseAtlasBuildConfig:
    manifest = _object(bundle, "manifest")
    return PoseAtlasBuildConfig(
        _text(manifest, "pack_id"),
        _text(manifest, "source_evidence"),
        _text(manifest, "identity_evidence"),
        _text(manifest, "body_profile_id"),
        _version_range(manifest, "body_profile_version_range"),
        _text(manifest, "rig_id"),
        _version_range(manifest, "rig_version_range"),
    )


def _summary(bundle: dict[str, object], name: str) -> SummaryReport:
    payload = _object(bundle, name)
    passed = payload.get("passed")
    problems = payload.get("problems", [])
    if not isinstance(passed, bool) or not _string_list(problems):
        raise TypeError("invalid_audit_summary")
    return SummaryReport(passed, tuple(problems))


def _load_evidence(
    bundle: dict[str, object],
    manifest,
) -> PoseLoadReleaseEvidence:
    payload = _object(bundle, "load")
    passed = payload.get("passed")
    revision = payload.get("source_revision_sha256")
    problems = payload.get("problems", [])
    if (
        not isinstance(passed, bool)
        or not isinstance(revision, str)
        or not _string_list(problems)
    ):
        raise TypeError("invalid_load_evidence")
    return PoseLoadReleaseEvidence(
        passed,
        manifest_sha256(manifest),
        revision,
        tuple(problems),
    )


def _object(parent: dict[str, object], name: str) -> dict[str, object]:
    value = parent.get(name)
    if not isinstance(value, dict):
        raise TypeError(f"invalid_{name}")
    return value


def _text(parent: dict[str, object], name: str) -> str:
    value = parent.get(name)
    if not isinstance(value, str) or not value.strip():
        raise TypeError(f"invalid_{name}")
    return value


def _version_range(parent: dict[str, object], name: str) -> tuple[int, int]:
    value = parent.get(name)
    if (
        not isinstance(value, list)
        or len(value) != VERSION_RANGE_LENGTH
        or any(not isinstance(item, int) or isinstance(item, bool) for item in value)
        or value[0] >= value[1]
    ):
        raise TypeError(f"invalid_{name}")
    return value[0], value[1]


def _string_list(value: object) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) for item in value)


def _blocked(*codes: str) -> str:
    return _json(
        {
            "schema_version": 1,
            "status": "blocked",
            "issues": [{"code": code} for code in dict.fromkeys(codes)],
        }
    )


def _json(payload: dict[str, object]) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


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
