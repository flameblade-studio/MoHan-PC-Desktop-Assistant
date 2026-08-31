"""Precisely repair the two visible B00 thumbnail specks in-place.

The authoritative RGBA is backed up before replacement.  Only the explicit
thumbnail pixels below may change; alpha and every RGB pixel outside that set
are invariants.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
from datetime import datetime
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw


SIZE = (1024, 1536)
TARGETS = {
    "left_thumbnail": ((260, 793), (261, 793), (260, 794), (261, 794), (260, 795), (261, 795)),
    "right_thumbnail": ((767, 791), (768, 791), (767, 792), (768, 792), (767, 793), (768, 793)),
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def local_skin_colour(source: np.ndarray, x: int, y: int) -> np.ndarray:
    """Return a robust nearby skin colour without sampling the dark speck."""
    local = source[y - 3 : y + 4, x - 3 : x + 4]
    rgb = local[:, :, :3].reshape(-1, 3)
    alpha = local[:, :, 3].reshape(-1)
    brightness = rgb.mean(axis=1)
    candidates = rgb[(alpha >= 96) & (brightness >= 72) & (brightness <= 185)]
    if len(candidates) < 5:
        raise RuntimeError(f"insufficient local skin samples at {(x, y)}")
    return np.median(candidates, axis=0).astype(np.uint8)


def contact(source: np.ndarray, repaired: np.ndarray, output: Path) -> None:
    panels: list[Image.Image] = []
    for label, points in TARGETS.items():
        xs = [point[0] for point in points]
        ys = [point[1] for point in points]
        x0, y0 = min(xs) - 14, min(ys) - 14
        x1, y1 = max(xs) + 15, max(ys) + 15
        for state, pixels in (("BEFORE", source), ("AFTER", repaired)):
            crop = Image.fromarray(pixels, "RGBA").crop((x0, y0, x1, y1))
            background = Image.new("RGBA", crop.size, (160, 160, 160, 255))
            background.alpha_composite(crop)
            enlarged = background.convert("RGB").resize(
                (crop.width * 20, crop.height * 20), Image.Resampling.NEAREST
            )
            draw = ImageDraw.Draw(enlarged)
            for x, y in points:
                left = (x - x0) * 20
                top = (y - y0) * 20
                draw.rectangle((left, top, left + 19, top + 19), outline=(255, 255, 0), width=3)
            draw.rectangle((0, 0, enlarged.width - 1, 31), fill=(20, 20, 20))
            draw.text((7, 8), f"{label} {state} 20x", fill=(255, 255, 255))
            panels.append(enlarged)
    canvas = Image.new("RGB", (panels[0].width * 2, panels[0].height * 2), (32, 36, 40))
    for index, panel in enumerate(panels):
        canvas.paste(panel, ((index % 2) * panel.width, (index // 2) * panel.height))
    output.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--authority", type=Path, required=True)
    parser.add_argument("--artifact-dir", type=Path, required=True)
    args = parser.parse_args()

    authority = args.authority.resolve()
    artifact_dir = args.artifact_dir.resolve()
    artifact_dir.mkdir(parents=True, exist_ok=True)
    with Image.open(authority) as image:
        if image.mode != "RGBA" or image.size != SIZE:
            raise ValueError(f"expected RGBA {SIZE}: {authority}")
        source = np.asarray(image, dtype=np.uint8).copy()

    original_sha = sha256(authority)
    stamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    backup = artifact_dir / f"{authority.stem}.before-thumb-nail-fix.{stamp}{authority.suffix}"
    shutil.copy2(authority, backup)
    if sha256(backup) != original_sha:
        raise RuntimeError("backup SHA does not match authority")

    repaired = source.copy()
    changed: list[dict[str, object]] = []
    all_targets = {point for points in TARGETS.values() for point in points}
    for label, points in TARGETS.items():
        for x, y in points:
            before = repaired[y, x, :3].copy()
            after = local_skin_colour(source, x, y)
            repaired[y, x, :3] = after
            changed.append(
                {
                    "side": label,
                    "x": x,
                    "y": y,
                    "before_rgb": before.tolist(),
                    "after_rgb": after.tolist(),
                }
            )

    changed_mask = np.any(source[:, :, :3] != repaired[:, :, :3], axis=2)
    expected_mask = np.zeros(changed_mask.shape, dtype=bool)
    for x, y in all_targets:
        expected_mask[y, x] = True
    alpha_diff = int(np.count_nonzero(source[:, :, 3] != repaired[:, :, 3]))
    outside_rgb_diff = int(np.count_nonzero(changed_mask & ~expected_mask))
    changed_pixels = int(np.count_nonzero(changed_mask))
    if alpha_diff or outside_rgb_diff or changed_pixels != len(all_targets):
        raise RuntimeError(
            "authority repair invariant failed: "
            f"alpha_diff={alpha_diff} outside_rgb_diff={outside_rgb_diff} "
            f"changed_pixels={changed_pixels} expected={len(all_targets)}"
        )

    temporary = authority.with_suffix(authority.suffix + ".thumb-nail-fix.tmp")
    Image.fromarray(repaired, "RGBA").save(temporary, format="PNG")
    os.replace(temporary, authority)
    new_sha = sha256(authority)

    contact_path = artifact_dir / "thumb-nails-before-after-20x.png"
    contact(source, repaired, contact_path)
    evidence = {
        "authority": str(authority),
        "backup": str(backup),
        "original_sha256": original_sha,
        "new_sha256": new_sha,
        "changed_pixel_count": changed_pixels,
        "alpha_diff_pixels": alpha_diff,
        "rgb_diff_outside_targets": outside_rgb_diff,
        "changed_pixels": changed,
        "contact": str(contact_path),
    }
    evidence_path = artifact_dir / "thumb-nail-authority-repair.json"
    evidence_path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        "PASS_B00_THUMB_NAIL_AUTHORITY_REPAIR "
        f"changed_pixels={changed_pixels} alpha_diff=0 rgb_outside_diff=0 "
        f"original_sha256={original_sha} new_sha256={new_sha} "
        f"backup={backup} contact={contact_path} evidence={evidence_path}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
