from __future__ import annotations

import hashlib
import json
from pathlib import Path

from PIL import Image


HERE = Path(__file__).resolve().parent


def main() -> int:
    data = json.loads((HERE / "dataset-manifest.json").read_text(encoding="utf-8"))
    issues: list[str] = []
    records = data.get("records", [])
    if len(records) != data.get("counts", {}).get("total"):
        issues.append("record count mismatch")
    if data.get("source_files_copied") is not False or data.get("training_executed") is not False:
        issues.append("read-only/training policy mismatch")
    if len({item.get("path") for item in records}) != len(records):
        issues.append("duplicate path records")
    admitted_identity = []
    for item in records:
        path = Path(item["path"])
        if not path.is_file():
            issues.append(f"missing: {path}")
            continue
        if hashlib.sha256(path.read_bytes()).hexdigest().upper() != item["sha256"]:
            issues.append(f"hash drift: {path}")
        with Image.open(path) as image:
            if [image.width, image.height] != [item["width"], item["height"]] or image.mode != item["mode"]:
                issues.append(f"image metadata drift: {path}")
        if str(item["identity_lora"]).startswith("ADMIT"):
            admitted_identity.append(item)
        for key in ("character_label", "garment_label", "angle_label", "identity_lora", "garment_conditioning", "reason"):
            if not str(item.get(key, "")).strip():
                issues.append(f"missing {key}: {path}")
    if {item["name"] for item in admitted_identity} != {"idle_front", "idle_lean", "idle"}:
        issues.append("identity admission must be exactly the three idle crop-only authorities")
    if any("CROP_ONLY" not in item["identity_lora"] for item in admitted_identity):
        issues.append("identity authorities must remain crop-only")
    b00 = next(item for item in records if item["name"] == "B00")
    profile = next(item for item in records if item["name"] == "062")
    if b00["identity_lora"] != "EXCLUDE" or b00["garment_conditioning"] != "ADMIT":
        issues.append("B00 role separation mismatch")
    if profile["identity_lora"] != "EXCLUDE" or profile["garment_conditioning"] != "EXCLUDE":
        issues.append("062 must remain geometry-only")
    status = "PASS" if not issues else "FAIL"
    print(json.dumps({"status": status, "records": len(records), "identity_admitted_crop_only": len(admitted_identity), "issues": issues}, ensure_ascii=False))
    return 0 if not issues else 4


if __name__ == "__main__":
    raise SystemExit(main())
