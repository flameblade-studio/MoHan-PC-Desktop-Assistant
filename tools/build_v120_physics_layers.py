from __future__ import annotations

lazy import sys
lazy from pathlib import Path

lazy import numpy as np
lazy from PIL import Image, ImageFilter

POSES = {
    "": "idle.png",
    "_lean": "idle_lean.png",
    "_front": "idle_front.png",
}

# The masks are deliberately built from the original full-resolution pixels.
# Existing segmented layers only identify the intended moving region; their
# colors are never reused. This prevents the magenta/grey fringe seen in v1.19.
LAYER_SETTINGS = {
    "sleeve_left": (19, 13.0, 238),
    "sleeve_right": (19, 13.0, 238),
    "hair_left": (11, 8.0, 236),
    "hair_right": (11, 8.0, 236),
    "ornament": (7, 5.0, 244),
}

ATTENTION_SPECS = {
    "": {
        "face": (575, 500, 112, 150),
        "eyes": ((496, 438, 25, 16), (601, 458, 25, 16)),
    },
    "_lean": {
        "face": (571, 500, 112, 150),
        "eyes": ((477, 439, 25, 16), (578, 459, 25, 16)),
    },
    "_front": {
        "face": (625, 482, 116, 148),
        "eyes": ((551, 447, 25, 16), (661, 447, 25, 16)),
    },
}


def zero_transparent_rgb(array: np.ndarray) -> np.ndarray:
    transparent = array[..., 3] == 0
    array[transparent, :3] = 0
    return array


def expanded_mask(old_layer: Image.Image, radius: int, blur: float, peak: int) -> Image.Image:
    alpha = old_layer.getchannel("A")
    size = max(3, radius | 1)
    mask = alpha.filter(ImageFilter.MaxFilter(size))
    mask = mask.filter(ImageFilter.GaussianBlur(blur))
    values = np.asarray(mask, dtype=np.float32)
    if values.max() > 0:
        values = np.clip(values * (peak / values.max()), 0, 255)
    return Image.fromarray(values.astype(np.uint8), "L")


def ellipse_mask(
    size: tuple[int, int],
    ellipses: tuple[tuple[int, int, int, int], ...],
    feather: float,
) -> Image.Image:
    width, height = size
    yy, xx = np.mgrid[0:height, 0:width]
    result = np.zeros((height, width), dtype=np.float32)
    for center_x, center_y, radius_x, radius_y in ellipses:
        distance = np.sqrt(
            ((xx - center_x) / radius_x) ** 2
            + ((yy - center_y) / radius_y) ** 2
        )
        weight = np.clip((1.0 - distance) / feather, 0.0, 1.0)
        result = np.maximum(result, weight)
    return Image.fromarray(np.round(result * 242).astype(np.uint8), "L")


def save_layer(source: Image.Image, mask: Image.Image, output: Path) -> None:
    source_array = np.asarray(source.convert("RGBA")).copy()
    original_alpha = source_array[..., 3].astype(np.float32) / 255.0
    mask_alpha = np.asarray(mask, dtype=np.float32) / 255.0
    source_array[..., 3] = np.round(original_alpha * mask_alpha * 255.0).astype(
        np.uint8
    )
    zero_transparent_rgb(source_array)
    Image.fromarray(source_array, "RGBA").save(output, optimize=True)


# Generation-1 entry point.  It reads the ``physics_*`` cutouts as mask hints;
# those files left the repository with the generation-2 bare base
# (2026-09-02), so ``tools/build_half_body_v120.py`` is the live producer.
# The helpers above stay because that builder imports them.
def main() -> int:
    assets = Path(sys.argv[1])
    for suffix, source_name in POSES.items():
        source = Image.open(assets / source_name).convert("RGBA")
        for layer_name, (radius, blur, peak) in LAYER_SETTINGS.items():
            old_name = f"physics_{layer_name}{suffix}.png"
            old_layer = Image.open(assets / old_name).convert("RGBA")
            mask = expanded_mask(old_layer, radius, blur, peak)
            save_layer(
                source,
                mask,
                assets / f"v120_{layer_name}{suffix}.png",
            )

        face_center_x, face_center_y, face_radius_x, face_radius_y = (
            ATTENTION_SPECS[suffix]["face"]
        )
        face_mask = ellipse_mask(
            source.size,
            ((face_center_x, face_center_y, face_radius_x, face_radius_y),),
            0.34,
        )
        eye_mask = ellipse_mask(
            source.size,
            ATTENTION_SPECS[suffix]["eyes"],
            0.52,
        )
        save_layer(source, face_mask, assets / f"v120_face{suffix}.png")
        save_layer(source, eye_mask, assets / f"v120_eyes{suffix}.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
