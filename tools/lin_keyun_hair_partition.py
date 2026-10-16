"""Move clothing edges out of Lin Keyun hair while preserving native RGBA."""
from __future__ import annotations

lazy import argparse
lazy import hashlib
lazy import json
lazy import sys
lazy from collections import deque
lazy from pathlib import Path
lazy import numpy as np
lazy from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
HAIR_KINDS = ("hair-back", "hair-front")
MIN_HAIR_COMPONENT_PIXELS = 256
PALE_MIN_CHANNEL = 100
PALE_MAX_CHANNEL = 130
PALE_RED_BLUE_DISTANCE = 30
PALE_GREEN_BLUE_DISTANCE = 8


def _head_connected(visible: np.ndarray, head_bottom: int) -> np.ndarray:
    """Keep head-connected hair and substantial detached back-hair regions."""
    connected = np.zeros_like(visible)
    visited = np.zeros_like(visible)
    height, width = visible.shape
    for raw_y, raw_x in zip(*np.nonzero(visible), strict=True):
        y, x = int(raw_y), int(raw_x)
        if visited[y, x]:
            continue
        component = []
        pending = deque([(y, x)])
        visited[y, x] = True
        touches_head = False
        while pending:
            cy, cx = pending.popleft()
            component.append((cy, cx))
            touches_head |= cy <= head_bottom
            for dy, dx in ((-1, -1), (-1, 0), (-1, 1), (0, -1),
                           (0, 1), (1, -1), (1, 0), (1, 1)):
                ny, nx = cy + dy, cx + dx
                if (0 <= ny < height and 0 <= nx < width
                        and visible[ny, nx] and not visited[ny, nx]):
                    visited[ny, nx] = True
                    pending.append((ny, nx))
        # Authored back hair may be separated from the scalp by the body.
        # Only small isolated marks qualify as non-hair dark outlines.
        if touches_head or len(component) >= MIN_HAIR_COMPONENT_PIXELS:
            ys, xs = zip(*component, strict=True)
            connected[ys, xs] = True
    return connected


def clean_hair_layers(layers: dict[str, np.ndarray], face_core: np.ndarray) -> dict[str, int]:
    """Reassign cool, bright clothing edges and disconnected marks to garment.

    The face-core bottom supplies the neck boundary. Head highlights stay in
    hair; below it, pale low-chroma pixels are clothing rather than brown hair.
    All moved pixels retain their original RGBA and exclusive ownership.
    """
    head_rows = np.nonzero(face_core[..., 3])[0]
    head_bottom = int(head_rows.max()) if len(head_rows) else face_core.shape[0] // 4
    visible = np.zeros(face_core.shape[:2], dtype=bool)
    removals = {}
    for kind in HAIR_KINDS:
        pixels = layers[kind]
        rgb = pixels[..., :3].astype(np.int16)
        pale = ((rgb.min(axis=2) >= PALE_MIN_CHANNEL) & (rgb.max(axis=2) >= PALE_MAX_CHANNEL)
                & (rgb[..., 0] - rgb[..., 2] <= PALE_RED_BLUE_DISTANCE)
                & (rgb[..., 1] - rgb[..., 2] <= PALE_GREEN_BLUE_DISTANCE))
        pale[:head_bottom + 1] = False
        removals[kind] = pale & (pixels[..., 3] > 0)
        visible |= (pixels[..., 3] > 0) & ~pale
    connected = _head_connected(visible, head_bottom)
    counts = {}
    for kind in HAIR_KINDS:
        pixels = layers[kind]
        move = removals[kind] | ((pixels[..., 3] > 0) & ~connected)
        if np.any(move & (layers["garment"][..., 3] > 0)):
            raise ValueError("Hair cleanup requires exclusive garment pixel ownership")
        layers["garment"][move] = pixels[move]
        pixels[move] = 0
        counts[kind] = int(move.sum())
    return counts


def _compose(base: Image.Image, plan: dict, layers: dict[str, np.ndarray], hide: Image.Image) -> np.ndarray:
    pixels = np.array(base)
    pixels[np.asarray(hide)[..., 3] > 0] = 0
    cleared = Image.fromarray(pixels)
    result = Image.new("RGBA", base.size)
    for kind in plan["order"]:
        result = Image.alpha_composite(result, cleared if kind == "base" else Image.fromarray(layers[kind]))
    return np.array(result)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    root = ROOT / "assets/characters/lin-keyun/body"
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    physical = {}
    for view, plan in manifest["layer_views"].items():
        directory = Path(plan["layers"][0]["path"]).parent
        physical.setdefault(directory.name, (view, plan))
    rows = []
    for name, (_, plan) in sorted(physical.items()):
        folder = root / "views" / name
        layers = {r["kind"]: np.array(Image.open(ROOT / r["path"]).convert("RGBA")) for r in plan["layers"]}
        before = {k: v.copy() for k, v in layers.items()}
        core = np.array(Image.open(ROOT / "assets/body-packs/mohan-body-v2/source/final-core-masks" / (name + ".png")))
        counts = clean_hair_layers(layers, core)
        base_path = ROOT / "assets/body-packs/mohan-body-v2/source/bald-natural11" / name / "bald-natural.png"
        if not base_path.exists():
            base_path = ROOT / "assets/body-packs/mohan-body-v2/source/gestures3" / name / "bald-natural.png"
        base = Image.open(base_path).convert("RGBA")
        hide = Image.open(folder / "base-hide-mask.png").convert("RGBA")
        delta = np.abs(_compose(base, plan, before, hide).astype(np.int16)
                       - _compose(base, plan, layers, hide).astype(np.int16))
        maximum = int(delta.max())
        if maximum > 1:
            raise ValueError(f"Clothed reconstruction changed: {name}: {maximum}")
        destination = args.output / "views" / name
        destination.mkdir(parents=True, exist_ok=True)
        for kind, pixels in layers.items():
            Image.fromarray(pixels).save(destination / (kind + ".png"), compress_level=9)
        rows.append({"view": name, "moved_pixels": counts, "clothed_rgba_max": maximum})
    payload = {"views": rows, "rule": "body + default hair only", "source_manifest_sha256": hashlib.sha256((root / "manifest.json").read_bytes()).hexdigest()}
    (args.output / "cleanup.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(rows, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
