"""Build a review-only B00 candidate that removes both connected dark specks."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw


SIZE = (1024, 1536)
# Manually localized connected dark regions seen in the 20x authority crops.
REGIONS = {
    "left_thumbnail": ((253, 788), (264, 801)),
    "right_thumbnail": ((761, 787), (772, 801)),
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def make_contact(source: np.ndarray, output: np.ndarray, path: Path) -> None:
    panels: list[Image.Image] = []
    for label, ((x0, y0), (x1, y1)) in REGIONS.items():
        crop_box = (x0 - 12, y0 - 12, x1 + 12, y1 + 12)
        for state, pixels in (("BEFORE", source), ("AFTER", output)):
            crop = Image.fromarray(pixels, "RGBA").crop(crop_box)
            gray = Image.new("RGBA", crop.size, (160, 160, 160, 255))
            gray.alpha_composite(crop)
            panel = gray.convert("RGB").resize(
                (crop.width * 20, crop.height * 20), Image.Resampling.NEAREST
            )
            draw = ImageDraw.Draw(panel)
            draw.rectangle((0, 0, panel.width - 1, 31), fill=(18, 18, 18))
            draw.text((7, 8), f"{label} {state} 20x", fill=(255, 255, 255))
            panels.append(panel)
    canvas = Image.new("RGB", (panels[0].width * 2, panels[0].height * 2), (30, 34, 38))
    for index, panel in enumerate(panels):
        canvas.paste(panel, ((index % 2) * panel.width, (index // 2) * panel.height))
    canvas.save(path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--contact", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    args = parser.parse_args()

    with Image.open(args.input) as image:
        if image.mode != "RGBA" or image.size != SIZE:
            raise ValueError(f"expected RGBA {SIZE}: {args.input}")
        source = np.asarray(image, dtype=np.uint8).copy()

    core_mask = np.zeros(source.shape[:2], dtype=np.uint8)
    region_records: list[dict[str, object]] = []
    for label, ((x0, y0), (x1, y1)) in REGIONS.items():
        local = source[y0:y1, x0:x1]
        brightness = local[:, :, :3].mean(axis=2)
        dark = ((brightness < 95) & (local[:, :, 3] >= 96)).astype(np.uint8)
        component_count, labels, stats, _centroids = cv2.connectedComponentsWithStats(
            dark, 8
        )
        if component_count < 2:
            raise RuntimeError(f"no localized dark component for {label}")
        darkest_y, darkest_x = np.unravel_index(np.argmin(brightness), brightness.shape)
        selected_label = int(labels[darkest_y, darkest_x])
        if selected_label == 0:
            selected_label = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
        selected = labels == selected_label
        allowed = (local[:, :, 3] >= 96) & (brightness < 135)
        selected = (
            cv2.dilate(selected.astype(np.uint8), np.ones((3, 3), np.uint8), iterations=1)
            > 0
        ) & allowed
        core_mask[y0:y1, x0:x1] |= selected.astype(np.uint8) * 255
        yy, xx = np.where(selected)
        region_records.append(
            {
                "side": label,
                "search_roi": [x0, y0, x1, y1],
                "mask_pixel_count": int(np.count_nonzero(selected)),
                "coordinates": [
                    [x0 + int(local_x), y0 + int(local_y)]
                    for local_y, local_x in zip(yy, xx)
                ],
            }
        )

    output = source.copy()
    for _label, ((x0, y0), (x1, y1)) in REGIONS.items():
        donor = source[y0 - 6 : y1 + 6, x0 - 6 : x1 + 6]
        donor_rgb = donor[:, :, :3].reshape(-1, 3)
        donor_alpha = donor[:, :, 3].reshape(-1)
        donor_brightness = donor_rgb.mean(axis=1)
        skin = donor_rgb[
            (donor_alpha >= 96)
            & (donor_brightness >= 105)
            & (donor_brightness <= 195)
            & (donor_rgb[:, 0] > donor_rgb[:, 1])
        ]
        if len(skin) < 20:
            raise RuntimeError(f"insufficient donor skin samples for {_label}")
        normal_skin = np.median(skin, axis=0).astype(np.float32)
        work = source[:, :, :3].copy()
        # Transparent RGB must never act as a white inpaint donor.
        work[source[:, :, 3] < 240] = normal_skin.astype(np.uint8)
        local_mask = np.zeros(source.shape[:2], dtype=np.uint8)
        local_mask[y0:y1, x0:x1] = core_mask[y0:y1, x0:x1]
        inpainted = cv2.cvtColor(
            cv2.inpaint(
                cv2.cvtColor(work, cv2.COLOR_RGB2BGR),
                local_mask,
                3,
                cv2.INPAINT_TELEA,
            ),
            cv2.COLOR_BGR2RGB,
        )
        feather = cv2.GaussianBlur(local_mask, (3, 3), 0.55).astype(np.float32) / 255.0
        feather[local_mask == 0] = 0.0
        weight = feather[:, :, None]
        original = source[:, :, :3].astype(np.float32)
        blended = np.rint(original * (1.0 - weight) + inpainted.astype(np.float32) * weight)
        selected = local_mask > 0
        output[selected, :3] = np.clip(blended[selected], 0, 255).astype(np.uint8)

    rgb_diff = np.any(source[:, :, :3] != output[:, :, :3], axis=2)
    alpha_diff = int(np.count_nonzero(source[:, :, 3] != output[:, :, 3]))
    outside_diff = int(np.count_nonzero(rgb_diff & (core_mask == 0)))
    changed = int(np.count_nonzero(rgb_diff))
    expected = int(np.count_nonzero(core_mask))
    if alpha_diff or outside_diff or changed != expected:
        raise RuntimeError(
            f"candidate invariant failed alpha={alpha_diff} outside={outside_diff} "
            f"changed={changed} expected={expected}"
        )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(output, "RGBA").save(args.output)
    make_contact(source, output, args.contact)
    evidence = {
        "status": "OWNER_REVIEW_REQUIRED_NOT_AUTHORITY_V5_IRREGULAR_MASK",
        "input": str(args.input.resolve()),
        "output": str(args.output.resolve()),
        "input_sha256": sha256(args.input),
        "output_sha256": sha256(args.output),
        "alpha_diff_pixels": alpha_diff,
        "rgb_diff_outside_regions": outside_diff,
        "changed_pixel_count": changed,
        "regions": region_records,
        "contact": str(args.contact.resolve()),
    }
    args.evidence.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        "PASS_B00_THUMB_NAIL_CANDIDATE_V5_OWNER_REVIEW_REQUIRED "
        f"changed_pixels={changed} alpha_diff=0 rgb_outside_diff=0 "
        f"input_sha256={evidence['input_sha256']} output_sha256={evidence['output_sha256']} "
        f"output={args.output.resolve()} contact={args.contact.resolve()}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
