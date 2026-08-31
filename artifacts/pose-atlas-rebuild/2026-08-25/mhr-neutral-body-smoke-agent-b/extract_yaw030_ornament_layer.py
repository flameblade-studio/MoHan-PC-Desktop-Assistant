"""Extract an auditable yaw+030 ornament candidate from untouched raw RGB."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw


SIZE = (1024, 1536)
PERIOD = 22
ORNAMENT_ROI = (450, 65, 640, 230)
POLYGONS = {
    "silver_plume": [(487, 101), (518, 94), (531, 146), (486, 150)],
    "silver_swan": [(514, 82), (575, 82), (579, 141), (510, 145)],
    "silver_lower_loop": [(516, 115), (590, 111), (594, 150), (516, 154)],
    "pin_left": [(462, 107), (527, 131), (524, 143), (460, 117)],
    "pin_right": [(562, 121), (630, 115), (633, 136), (562, 143)],
    "blue_flower": [(578, 96), (630, 96), (635, 151), (580, 151)],
    "tassel_left": [(590, 124), (608, 124), (609, 222), (589, 222)],
    "tassel_right": [(602, 124), (624, 124), (625, 222), (602, 222)],
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def bbox(mask: np.ndarray) -> list[int] | None:
    ys, xs = np.where(mask)
    return None if not len(xs) else [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())]


def polygon_mask(points: list[tuple[int, int]]) -> np.ndarray:
    image = Image.new("L", SIZE, 0); ImageDraw.Draw(image).polygon(points, fill=255)
    return np.asarray(image, dtype=np.uint8) > 0


def raw_checker_model(raw: np.ndarray) -> np.ndarray:
    height, width = raw.shape[:2]
    yy, xx = np.indices((height, width))
    background_zone = ((xx < 250) | (xx >= 800)) & (yy < 650)
    phase = np.zeros((PERIOD, PERIOD, 3), dtype=np.float32)
    for ry in range(PERIOD):
        for rx in range(PERIOD):
            sample = raw[(yy % PERIOD == ry) & (xx % PERIOD == rx) & background_zone]
            if len(sample) < 64:
                raise RuntimeError(f"insufficient raw-only checker sample at phase {rx},{ry}")
            phase[ry, rx] = np.median(sample, axis=0)
    return phase[yy % PERIOD, xx % PERIOD]


def remove_tiny_components(alpha: np.ndarray, minimum: int = 2) -> tuple[np.ndarray, np.ndarray]:
    active = alpha > 0
    seen = np.zeros(active.shape, bool)
    keep = np.zeros(active.shape, bool)
    height, width = active.shape
    for y, x in zip(*np.where(active & ~seen)):
        if seen[y, x]:
            continue
        queue = deque([(int(y), int(x))]); seen[y, x] = True; component: list[tuple[int, int]] = []
        while queue:
            cy, cx = queue.popleft(); component.append((cy, cx))
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    ny, nx = cy + dy, cx + dx
                    if 0 <= ny < height and 0 <= nx < width and active[ny, nx] and not seen[ny, nx]:
                        seen[ny, nx] = True; queue.append((ny, nx))
        if len(component) >= minimum:
            for cy, cx in component: keep[cy, cx] = True
    removed = active & ~keep
    output = alpha.copy(); output[removed] = 0
    return output, removed


def overlay(raw: np.ndarray, mask: np.ndarray, color: tuple[int, int, int], path: Path) -> None:
    image = raw.copy().astype(np.float32)
    image[mask] = image[mask] * 0.35 + np.asarray(color, np.float32) * 0.65
    Image.fromarray(np.clip(image, 0, 255).astype(np.uint8), "RGB").crop(ORNAMENT_ROI).resize((760, 660), Image.Resampling.NEAREST).save(path)


def checker(size: tuple[int, int], tile: int = 16) -> Image.Image:
    image = Image.new("RGBA", size, (232, 232, 232, 255)); draw = ImageDraw.Draw(image)
    for y in range(0, size[1], tile):
        for x in range(0, size[0], tile):
            if (x // tile + y // tile) % 2:
                draw.rectangle((x, y, x + tile - 1, y + tile - 1), fill=(184, 184, 184, 255))
    return image


def composite(image: Image.Image, background: Image.Image) -> Image.Image:
    result = background.copy(); result.alpha_composite(image); return result.convert("RGB")


def four_background_4x(image: Image.Image, path: Path, label: str) -> None:
    backgrounds = {
        "black": Image.new("RGBA", SIZE, (0, 0, 0, 255)),
        "green": Image.new("RGBA", SIZE, (0, 255, 0, 255)),
        "magenta": Image.new("RGBA", SIZE, (255, 0, 255, 255)),
        "checker": checker(SIZE),
    }
    crop = ORNAMENT_ROI; width, height = crop[2] - crop[0], crop[3] - crop[1]
    panels = []
    for name, background in backgrounds.items():
        panel = composite(image, background).crop(crop).resize((width * 4, height * 4), Image.Resampling.NEAREST)
        draw = ImageDraw.Draw(panel); draw.rectangle((0, 0, panel.width, 30), fill=(0, 0, 0)); draw.text((8, 9), f"{label} / {name} / 4x", fill=(255, 255, 255)); panels.append(panel)
    sheet = Image.new("RGB", (sum(panel.width for panel in panels), max(panel.height for panel in panels)), (20, 20, 20)); x = 0
    for panel in panels: sheet.paste(panel, (x, 0)); x += panel.width
    sheet.save(path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw", type=Path, required=True)
    parser.add_argument("--person-v3", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(); args.output.mkdir(parents=True, exist_ok=True)
    missing = [str(path) for path in (args.raw, args.person_v3) if not path.is_file()]
    if missing:
        print(json.dumps({"status": "FAIL_MISSING_INPUT", "missing": missing})); return 3
    raw_image = Image.open(args.raw).convert("RGB"); person = Image.open(args.person_v3).convert("RGBA")
    if raw_image.size != SIZE or person.size != SIZE:
        print(json.dumps({"status": "FAIL_SIZE", "raw": raw_image.size, "person": person.size})); return 4
    raw = np.asarray(raw_image, dtype=np.uint8); modeled = raw_checker_model(raw.astype(np.float32))
    residual = np.linalg.norm(raw.astype(np.float32) - modeled, axis=2)
    masks = {name: polygon_mask(points) for name, points in POLYGONS.items()}
    manual_union = np.logical_or.reduce(list(masks.values()))
    silver_region = masks["silver_plume"] | masks["silver_swan"] | masks["silver_lower_loop"] | masks["pin_left"] | masks["pin_right"]
    blue_region = masks["blue_flower"] | masks["tassel_left"] | masks["tassel_right"]
    rgb = raw.astype(np.int16); channel_min = rgb.min(axis=2); channel_max = rgb.max(axis=2)
    silver_evidence = silver_region & (residual >= 16.0) & (channel_min >= 105) & ((channel_max - channel_min) <= 85)
    blue_evidence = blue_region & (residual >= 14.0) & (rgb[:, :, 2] >= rgb[:, :, 0] + 8) & (channel_max >= 55)
    silver_alpha = np.clip((residual - 12.0) / 22.0 * 255.0, 0, 255) * np.clip((channel_min - 90.0) / 85.0, 0, 1)
    blue_alpha = np.clip((residual - 10.0) / 24.0 * 255.0, 0, 255) * np.clip((rgb[:, :, 2] - rgb[:, :, 0] - 4.0) / 28.0, 0, 1)
    alpha = np.zeros(residual.shape, np.float32)
    alpha[silver_evidence] = silver_alpha[silver_evidence]
    alpha[blue_evidence] = np.maximum(alpha[blue_evidence], blue_alpha[blue_evidence])
    alpha = np.rint(np.clip(alpha, 0, 255)).astype(np.uint8)
    alpha, tiny_removed = remove_tiny_components(alpha, minimum=2)
    outside = (alpha > 0) & ~manual_union
    if outside.any():
        print(json.dumps({"status": "FAIL_MASK_SCOPE", "outside": int(outside.sum())})); return 5

    overlay(raw, manual_union, (255, 210, 0), args.output / "01-manual-polygons-overlay.png")
    overlay(raw, silver_evidence, (0, 255, 0), args.output / "02-silver-evidence-overlay.png")
    overlay(raw, blue_evidence, (0, 180, 255), args.output / "03-blue-evidence-overlay.png")
    overlay(raw, tiny_removed, (255, 0, 255), args.output / "04-tiny-removal-overlay.png")
    overlay(raw, alpha > 0, (255, 80, 0), args.output / "05-final-mask-overlay.png")

    layer = np.zeros((SIZE[1], SIZE[0], 4), dtype=np.uint8); layer[:, :, :3] = raw; layer[:, :, 3] = alpha; layer[alpha == 0, :3] = 0
    layer_image = Image.fromarray(layer, "RGBA"); layer_path = args.output / "yaw+030-pitch+00_ornament.candidate.png"; layer_image.save(layer_path)
    recomposed = person.copy(); recomposed.alpha_composite(layer_image); recomposed_path = args.output / "yaw+030-pitch+00.recomposed-v3-plus-ornament.png"; recomposed.save(recomposed_path)
    layer_sheet = args.output / "ornament-layer-four-background-4x.png"; four_background_4x(layer_image, layer_sheet, "ornament layer")
    composite_sheet = args.output / "recomposed-four-background-4x.png"; four_background_4x(recomposed, composite_sheet, "recomposed")

    report = {
        "schema": "mohan-yaw030-ornament-isolation/v1",
        "status": "PASS_TECHNICAL_MASK_SCOPE_GATE",
        "inputs": {"raw": {"path": str(args.raw.resolve()), "sha256": sha256(args.raw)}, "person_v3": {"path": str(args.person_v3.resolve()), "sha256": sha256(args.person_v3)}},
        "manual_polygons": {name: points for name, points in POLYGONS.items()},
        "operations": [
            {"id": 1, "operation": "manual polygon whitelist", "overlay": "01-manual-polygons-overlay.png", "pixels": int(manual_union.sum())},
            {"id": 2, "operation": "silver residual/luminance evidence", "overlay": "02-silver-evidence-overlay.png", "pixels": int(silver_evidence.sum())},
            {"id": 3, "operation": "blue residual/chroma evidence", "overlay": "03-blue-evidence-overlay.png", "pixels": int(blue_evidence.sum())},
            {"id": 4, "operation": "remove components smaller than 2 pixels", "overlay": "04-tiny-removal-overlay.png", "pixels": int(tiny_removed.sum())},
            {"id": 5, "operation": "final Alpha mask", "overlay": "05-final-mask-overlay.png", "pixels": int((alpha > 0).sum())}
        ],
        "alpha": {"bbox": bbox(alpha > 0), "nonzero_pixels": int((alpha > 0).sum()), "solid_pixels": int((alpha >= 128).sum()), "partial_pixels": int(((alpha > 0) & (alpha < 255)).sum()), "outside_manual_polygon_pixels": int(outside.sum()), "transparent_rgb_nonzero_pixels": int(np.any(layer[:, :, :3][alpha == 0] != 0, axis=1).sum())},
        "outputs": {"ornament_layer": {"path": str(layer_path.resolve()), "sha256": sha256(layer_path)}, "recomposed": {"path": str(recomposed_path.resolve()), "sha256": sha256(recomposed_path)}, "layer_four_background_4x": {"path": str(layer_sheet.resolve()), "sha256": sha256(layer_sheet)}, "recomposed_four_background_4x": {"path": str(composite_sheet.resolve()), "sha256": sha256(composite_sheet)}},
        "rgb_contract": "Every Alpha>0 ornament pixel is byte-identical to raw RGB; no generation, mirror or repaint.",
        "manual_art_gate": "pending",
        "non_claims": ["Candidate ornament layer only", "The person-v3 baseline still contains its prior ornament pixels", "No formal asset, identity, angle, 24-view or 600-layer acceptance"],
        "forbidden_components_used_or_downloaded": []
    }
    qa_path = args.output / "qa.json"; qa_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "alpha_pixels": report["alpha"]["nonzero_pixels"], "bbox": report["alpha"]["bbox"], "layer": str(layer_path), "recomposed": str(recomposed_path), "qa": str(qa_path)}, ensure_ascii=False)); return 0


if __name__ == "__main__":
    raise SystemExit(main())
