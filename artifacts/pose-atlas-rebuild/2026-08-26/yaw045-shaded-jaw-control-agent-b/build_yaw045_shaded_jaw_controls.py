from __future__ import annotations

import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps


ROOT = Path(__file__).resolve().parent
BASE = Path(r"D:\FlamebladeStudio\CodexProjects\2026-08-13\mohan-multisensory-vision")
CONTROL_DIR = BASE / r"artifacts\pose-atlas-rebuild\2026-08-26\yaw045-geometry-controls-agent-d\controls"
NPZ = BASE / r"artifacts\pose-atlas-rebuild\2026-08-25\ufbx-lod1-extractor-agent-a\candidate3-yaw-controls-24\candidate3-vertex-projections.npz"
WEIGHTS = BASE / r"artifacts\pose-atlas-rebuild\2026-08-25\skin-weight-parts-agent-a\vertex-skin-weights.tsv"
VERTICES = BASE / r"artifacts\pose-atlas-rebuild\2026-08-25\ufbx-lod1-extractor-agent-a\candidate3-yaw-controls-24\candidate3-renderer-vertices.bin"
VIEW = "yaw+045-pitch+00"
RENDERER_YAW = -45
THRESHOLD = 0.55


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def jaw_vertices() -> np.ndarray:
    totals: dict[int, float] = defaultdict(float)
    jaw: dict[int, float] = defaultdict(float)
    with WEIGHTS.open(encoding="utf-8") as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            vertex = int(row["vertex_index"])
            weight = float(row["weight"])
            totals[vertex] += weight
            if row["bone_name"] == "c_jaw":
                jaw[vertex] += weight
    selected = sorted(vertex for vertex, weight in jaw.items() if totals[vertex] and weight / totals[vertex] >= THRESHOLD)
    if not selected:
        raise RuntimeError("No c_jaw vertices passed the exact skin-weight threshold")
    return np.asarray(selected, dtype=np.int64)


def geometry_shading(normal: Image.Image, silhouette: Image.Image) -> tuple[Image.Image, Image.Image]:
    encoded = np.asarray(normal.convert("RGB"), dtype=np.float32) / 255.0
    normals = encoded * 2.0 - 1.0
    light = np.asarray([-0.35, -0.45, 0.82], dtype=np.float32)
    light /= np.linalg.norm(light)
    diffuse = np.clip(np.sum(normals * light, axis=2), 0.0, 1.0)
    shade = 0.22 + 0.78 * diffuse
    albedo = np.asarray([185.0, 195.0, 210.0], dtype=np.float32)
    shaded = np.clip(shade[..., None] * albedo, 0, 255).astype(np.uint8)
    mask = np.asarray(silhouette.convert("L"), dtype=np.uint8) > 0
    background = np.full_like(shaded, 22)
    background[mask] = shaded[mask]
    base = np.full_like(shaded, 22)
    base[mask] = np.asarray([174, 184, 200], dtype=np.uint8)
    return Image.fromarray(base, "RGB"), Image.fromarray(background, "RGB")


def main() -> int:
    inputs = {
        "depth": CONTROL_DIR / f"{VIEW}_depth.png",
        "normal": CONTROL_DIR / f"{VIEW}_normal.png",
        "silhouette": CONTROL_DIR / f"{VIEW}_silhouette.png",
    }
    for path in (*inputs.values(), NPZ, WEIGHTS, VERTICES):
        if not path.is_file():
            raise FileNotFoundError(path)
    depth = Image.open(inputs["depth"]).convert("L")
    normal = Image.open(inputs["normal"]).convert("RGB")
    silhouette = Image.open(inputs["silhouette"]).convert("L")
    if not all(image.size == (1024, 1536) for image in (depth, normal, silhouette)):
        raise RuntimeError("Control dimensions are not 1024x1536")

    base, shaded = geometry_shading(normal, silhouette)
    base_path = ROOT / f"{VIEW}_base-render.png"
    shaded_path = ROOT / f"{VIEW}_shaded-render.png"
    base.save(base_path)
    shaded.save(shaded_path)

    jaw = jaw_vertices()
    with np.load(NPZ, allow_pickle=False) as data:
        yaws = data["yaw_degrees"]
        rows = np.where(yaws == RENDERER_YAW)[0]
        if len(rows) != 1:
            raise RuntimeError("Renderer -45 row is missing or ambiguous")
        row = int(rows[0])
        points = data["screen_xy"][row, jaw]
        depths = data["camera_depth"][row, jaw]
    anchor_offset = int(np.argmax(points[:, 1]))
    anchor_vertex = int(jaw[anchor_offset])
    anchor_xy = points[anchor_offset]
    overlay = shaded.copy()
    draw = ImageDraw.Draw(overlay)
    for x, y in points:
        draw.ellipse((x - 1.5, y - 1.5, x + 1.5, y + 1.5), fill=(255, 215, 0))
    ax, ay = map(float, anchor_xy)
    draw.ellipse((ax - 8, ay - 8, ax + 8, ay + 8), outline=(255, 40, 40), width=4)
    draw.line((ax - 16, ay, ax + 16, ay), fill=(255, 40, 40), width=2)
    draw.line((ax, ay - 16, ax, ay + 16), fill=(255, 40, 40), width=2)
    draw.text((20, 20), f"c_jaw exact-weight vertices={len(jaw)} | lowest projected Y candidate v{anchor_vertex}", fill="white", font=ImageFont.load_default())
    draw.text((20, 38), "CANDIDATE ONLY - not a formal FLAME/MediaPipe menton landmark", fill=(255, 120, 120), font=ImageFont.load_default())
    overlay_path = ROOT / f"{VIEW}_jaw-menton-candidate-overlay.png"
    overlay.save(overlay_path)

    panels = [
        ("BASE RENDER", base),
        ("SHADED RENDER", shaded),
        ("DEPTH", depth.convert("RGB")),
        ("NORMAL", normal),
        ("SILHOUETTE", silhouette.convert("RGB")),
        ("c_jaw / MENTON CANDIDATE", overlay),
    ]
    contact = Image.new("RGB", (1200, 1200), (28, 30, 34))
    contact_draw = ImageDraw.Draw(contact)
    for index, (label, image) in enumerate(panels):
        row, column = divmod(index, 3)
        thumb = ImageOps.contain(image, (370, 540), Image.Resampling.LANCZOS)
        x, y = column * 400 + 15, row * 600 + 40
        contact.paste(thumb, (x + (370 - thumb.width) // 2, y))
        contact_draw.text((column * 400 + 15, row * 600 + 15), label, fill="white", font=ImageFont.load_default())
    contact_path = ROOT / f"{VIEW}_geometry-contact.png"
    contact.save(contact_path)

    outputs = [base_path, shaded_path, overlay_path, contact_path]
    evidence = {
        "schema": "mohan.yaw045.mesh_shaded_jaw_control.v1",
        "status": "PASS_3D_CONTROL_STAGING_ONLY",
        "formal_view_id": VIEW,
        "renderer_yaw_degrees": RENDERER_YAW,
        "mirror": False,
        "flux_started": False,
        "sources": {name: {"path": str(path), "sha256": sha256(path)} for name, path in inputs.items()},
        "mesh_sources": {
            "vertices_bin": {"path": str(VERTICES), "sha256": sha256(VERTICES), "vertex_count": 18439},
            "projection_npz": {"path": str(NPZ), "sha256": sha256(NPZ), "renderer_row": row},
            "skin_weights": {"path": str(WEIGHTS), "sha256": sha256(WEIGHTS)},
        },
        "jaw_candidate": {
            "method": "exact c_jaw FBX skin-weight share >= 0.55; anchor is maximum screen Y at renderer -45",
            "candidate_vertex_count": int(len(jaw)),
            "anchor_vertex_index": anchor_vertex,
            "anchor_screen_xy": [float(ax), float(ay)],
            "anchor_camera_depth": float(depths[anchor_offset]),
            "formal_anatomical_landmark": False,
            "warning": "Exact mesh-derived contour candidate only; no FLAME/MediaPipe mapping is claimed.",
        },
        "outputs": {path.name: {"path": str(path), "sha256": sha256(path), "size": list(Image.open(path).size)} for path in outputs},
        "formal_asset_promotion": False,
    }
    evidence_path = ROOT / "yaw045-shaded-jaw-control-evidence.json"
    evidence_path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": evidence["status"], "anchor_vertex": anchor_vertex, "contact": str(contact_path), "contact_sha256": sha256(contact_path)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
