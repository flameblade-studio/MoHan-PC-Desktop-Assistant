from __future__ import annotations

import datetime as dt
import hashlib
import json
from pathlib import Path


PROJECT = Path(r"D:\FlamebladeStudio\CodexProjects\2026-08-13\mohan-multisensory-vision")
ROOT = PROJECT / "artifacts" / "pose-atlas-rebuild" / "2026-08-25"
EVIDENCE_ROOT = ROOT / "yunchangge-vnext-three-domain-compat-agent-c"
FORM = EVIDENCE_ROOT / "yaw-105-v3-alpha-owner-authorization.json"
REPORT = EVIDENCE_ROOT / "yaw-105-v3-alpha-owner-authorization-validation.json"
SOURCE = (
    ROOT
    / "yaw-105-candidate-v2-shoe-local-edit-main"
    / "yaw-105-pitch+00.candidate-v3.deterministic-shoe-roi-composite.png"
)
SOURCE_SHA256 = "10F705A4CA4F2B5FC4FB7D96C2BB69E7EC18AA25209841CBB76979BA0F47C86C"
DECISION_PHRASE = "APPROVE_ALPHA_ONLY_STAGING_FOR_THIS_EXACT_SHA"

EXPECTED_KEYS = {
    "schema",
    "candidate_id",
    "source_path",
    "source_sha256",
    "decision_phrase",
    "authorize_birefnet_alpha_only",
    "authorized_by",
    "authorized_at",
    "owner_visible_approval_evidence",
    "scope",
    "staging_only",
    "preserve_subject_rgb",
    "formal_asset_write",
    "identity_status",
    "angle_status",
    "promotion_allowed",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def valid_iso_timestamp(value: object) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    try:
        dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return True


def validate(record: dict[str, object]) -> list[str]:
    errors: list[str] = []
    missing = sorted(EXPECTED_KEYS - set(record))
    extra = sorted(set(record) - EXPECTED_KEYS)
    errors.extend(f"missing field: {key}" for key in missing)
    errors.extend(f"unexpected field: {key}" for key in extra)
    required_values = {
        "schema": "mohan.yaw105.v3.alpha-owner-authorization/v1",
        "candidate_id": "yaw-105-pitch+00.candidate-v3.deterministic-shoe-roi-composite",
        "source_path": str(SOURCE),
        "source_sha256": SOURCE_SHA256,
        "decision_phrase": DECISION_PHRASE,
        "authorize_birefnet_alpha_only": True,
        "authorized_by": "CHOU MING HUA",
        "scope": "ALPHA_ONLY_ISOLATED_STAGING",
        "staging_only": True,
        "preserve_subject_rgb": True,
        "formal_asset_write": False,
        "identity_status": "HOLD_NOT_ACCEPTED",
        "angle_status": "HOLD_NOT_ACCEPTED",
        "promotion_allowed": False,
    }
    errors.extend(
        f"field mismatch: {key}"
        for key, expected in required_values.items()
        if record.get(key) != expected
    )
    if not valid_iso_timestamp(record.get("authorized_at")):
        errors.append("authorized_at must be a non-empty ISO-8601 timestamp")
    evidence = record.get("owner_visible_approval_evidence")
    if not isinstance(evidence, str) or not evidence.strip():
        errors.append("owner_visible_approval_evidence must be a non-empty evidence reference")
    if not SOURCE.is_file():
        errors.append(f"source file missing: {SOURCE}")
    elif sha256(SOURCE) != SOURCE_SHA256:
        errors.append("source file SHA256 drift")
    return errors


def main() -> int:
    errors: list[str] = []
    record: dict[str, object] = {}
    if not FORM.is_file():
        errors.append(f"authorization form missing: {FORM}")
    else:
        try:
            loaded = json.loads(FORM.read_text(encoding="utf-8"))
            if not isinstance(loaded, dict):
                errors.append("authorization form root must be an object")
            else:
                record = loaded
                errors.extend(validate(record))
        except (OSError, json.JSONDecodeError) as error:
            errors.append(f"authorization form cannot be read: {error}")
    report = {
        "schema": "mohan.yaw105.v3.alpha-owner-authorization-validation/v1",
        "status": "PASS_EXACT_SHA_ALPHA_ONLY_AUTHORIZATION" if not errors else "BLOCK",
        "form": str(FORM),
        "form_sha256": sha256(FORM) if FORM.is_file() else None,
        "source": str(SOURCE),
        "expected_source_sha256": SOURCE_SHA256,
        "actual_source_sha256": sha256(SOURCE) if SOURCE.is_file() else None,
        "authorization_valid": not errors,
        "inference_run": False,
        "identity_status": "HOLD_NOT_ACCEPTED",
        "angle_status": "HOLD_NOT_ACCEPTED",
        "promotion_allowed": False,
        "errors": errors,
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not errors else 4


if __name__ == "__main__":
    raise SystemExit(main())
