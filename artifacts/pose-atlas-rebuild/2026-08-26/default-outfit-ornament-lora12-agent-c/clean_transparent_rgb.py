from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image


ROOT = Path(__file__).resolve().parent
MANIFEST = ROOT / "dataset-manifest.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def clean(path: Path) -> int:
    rgba = np.array(Image.open(path).convert("RGBA"), copy=True)
    transparent = rgba[:, :, 3] == 0
    contaminated = transparent & np.any(rgba[:, :, :3] != 0, axis=2)
    count = int(np.count_nonzero(contaminated))
    rgba[transparent, :3] = 0
    Image.fromarray(rgba, "RGBA").save(path)
    return count


def main() -> int:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    records = []
    for item in manifest["records"]:
        for key in ("outfit", "ornament"):
            path = Path(item[key])
            changed = clean(path)
            item[f"{key}_sha256"] = sha256(path)
            records.append({"file": str(path), "cleared_transparent_rgb_pixels": changed, "sha256": item[f"{key}_sha256"]})
    MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    report = ROOT / "transparent-rgb-clean-report.json"
    report.write_text(json.dumps({"status": "PASS", "exit_code": 0, "records": records}, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "PASS", "exit_code": 0, "files": len(records), "pixels_cleared": sum(item["cleared_transparent_rgb_pixels"] for item in records), "report": str(report)}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
