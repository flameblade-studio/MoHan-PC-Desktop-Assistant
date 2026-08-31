"""Build an evidence-only yaw-105 owner review contact sheet."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


PROJECT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
OUT = HERE / "yaw-105-owner-review-contact-sheet.jpg"
WORKPACK = HERE / "yaw-105-owner-review-workpack.json"


def open_rgb(relative: str) -> Image.Image:
    return Image.open(PROJECT / relative).convert("RGB")


def fit(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    result = image.copy()
    result.thumbnail(size, Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", size, (28, 32, 38))
    canvas.paste(result, ((size[0] - result.width) // 2, (size[1] - result.height) // 2))
    return canvas


def face_crop(image: Image.Image) -> Image.Image:
    width, height = image.size
    return image.crop((int(width * .23), int(height * .02), int(width * .77), int(height * .40)))


def main() -> int:
    data = json.loads(WORKPACK.read_text(encoding="utf-8"))
    sheet = Image.new("RGB", (1800, 2100), (20, 24, 30))
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default(size=24)
    small = ImageFont.load_default(size=19)
    draw.text((30, 18), "MoHan yaw-105 OWNER REVIEW ONLY - NO PROMOTION", fill=(255, 220, 120), font=font)

    candidate_labels = ["v1: shoe FAIL", "v2: non-local edit FAIL", "v3: PRIMARY REVIEW / alpha missing"]
    for index, (entry, label) in enumerate(zip(data["candidate_inventory"], candidate_labels)):
        image = fit(open_rgb(entry["path"]), (540, 780))
        x = 30 + index * 585
        sheet.paste(image, (x, 70))
        draw.text((x, 855), label, fill=(240, 240, 240), font=small)

    v3 = open_rgb(data["candidate_inventory"][2]["path"])
    identity_items = [
        (face_crop(v3), "v3 face crop / HOLD"),
        (open_rgb("assets/expressions/idle_front.png"), "idle_front authority"),
        (open_rgb("assets/expressions/idle_lean.png"), "idle_lean authority"),
        (open_rgb("assets/expressions/idle.png"), "idle authority"),
    ]
    for index, (image, label) in enumerate(identity_items):
        panel = fit(image, (405, 430))
        x = 30 + index * 435
        sheet.paste(panel, (x, 920))
        draw.text((x, 1355), label, fill=(220, 230, 245), font=small)

    for index, control in enumerate(data["angle_controls"]):
        panel = fit(open_rgb(control["path"]), (540, 600))
        x = 30 + index * 585
        sheet.paste(panel, (x, 1420))
        draw.text((x, 2025), control["view_id"] + " normal CONTROL ONLY", fill=(180, 220, 255), font=small)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(OUT, quality=94, subsampling=0)
    print(json.dumps({
        "output": str(OUT),
        "sha256": hashlib.sha256(OUT.read_bytes()).hexdigest().upper(),
        "size": list(sheet.size),
        "promotion_allowed": False,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
