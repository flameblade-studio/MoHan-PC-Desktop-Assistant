from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(r"D:\FlamebladeStudio\CodexProjects\2026-08-13\mohan-multisensory-vision")
HERE = Path(__file__).resolve().parent
MAPPING = HERE / "yunchangge-vnext-field-mapping.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def main() -> int:
    payload = json.loads(MAPPING.read_text(encoding="utf-8"))
    errors: list[str] = []
    if payload.get("status") != "BLOCKED_NOT_WIRED":
        errors.append("status must remain blocked")
    if payload.get("promotion_allowed") is not False or payload.get("runtime_wired") is not False:
        errors.append("promotion/runtime flags must be false")
    required_slots = {
        "core_skin", "body_geometry", "outerwear", "innerwear", "skirt",
        "sleeve_left", "sleeve_right", "shoe_left", "shoe_right",
        "fixed_hair_ornament", "replaceable_headwear",
    }
    actual_slots = {entry["vnext_slot"] for entry in payload.get("mapping", [])}
    if not required_slots.issubset(actual_slots):
        errors.append("required vNext mapping entries missing")
    for evidence in payload.get("evidence", []):
        path = ROOT / evidence["path"]
        if not path.is_file():
            errors.append(f"missing evidence: {path}")
            continue
        if sha256(path) != evidence["sha256"]:
            errors.append(f"hash drift: {path}")
        line_count = len(path.read_text(encoding="utf-8").splitlines())
        if any(not isinstance(line, int) or line < 1 or line > line_count for line in evidence["lines"]):
            errors.append(f"invalid evidence line: {path}")
    result = {
        "status": "VALID_BLOCKED_REPORT" if not errors else "INVALID_REPORT",
        "errors": errors,
        "mapping_sha256": sha256(MAPPING),
        "promotion_allowed": False,
        "runtime_wired": False,
    }
    (HERE / "validation-result.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, ensure_ascii=False))
    return 4 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
