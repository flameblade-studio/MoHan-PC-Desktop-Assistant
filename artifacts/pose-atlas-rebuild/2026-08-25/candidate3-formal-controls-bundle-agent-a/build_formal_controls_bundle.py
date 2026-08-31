from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps


OUT = Path(__file__).resolve().parent
RUN = OUT.parent
SOURCE = RUN / "ufbx-lod1-extractor-agent-a" / "candidate3-yaw-controls-24" / "controls"
MAPPING = RUN / "candidate3-yaw-sign-audit-agent-a" / "formal-view-id-to-candidate3-control-file-id.json"
BUNDLE = OUT / "formal-controls"
YAWS = list(range(-180, 180, 15))
KINDS = ("silhouette", "depth", "normal")
EXPECTED = {"silhouette": ((1024, 1536), "L"), "depth": ((1024, 1536), "L"), "normal": ((1024, 1536), "RGB")}


def view_id(yaw: int) -> str:
    return f"yaw{yaw:+04d}-pitch+00"


def mapped_yaw(formal_yaw: int) -> int:
    negated = -formal_yaw
    return -180 if negated == 180 else negated


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fail(message: str) -> int:
    print(f"FAIL: {message}")
    return 4


def make_contact(records: list[dict]) -> Path:
    tile_w, tile_h = 256, 400
    canvas = Image.new("RGB", (tile_w * 6, tile_h * 4 + 44), "white")
    draw = ImageDraw.Draw(canvas)
    draw.text((8, 8), "CANDIDATE3 FORMAL CONTROLS - NORMALS - MAPPED, NOT FINAL ART", fill="black")
    for index, record in enumerate(records):
        row, col = divmod(index, 6)
        x, y = col * tile_w, 44 + row * tile_h
        normal = Path(record["outputs"]["normal"]["absolute_path"])
        image = ImageOps.contain(Image.open(normal).convert("RGB"), (tile_w - 8, tile_h - 52), Image.Resampling.LANCZOS)
        canvas.paste(image, (x + (tile_w - image.width) // 2, y + 42))
        draw.text((x + 4, y + 4), record["formal_view_id"], fill="black")
        draw.text((x + 4, y + 21), f"source {record['source_control_file_id']}", fill="darkgreen")
    path = OUT / "formal-controls-normal-contact-sheet.png"
    canvas.save(path)
    return path


def main() -> int:
    if not MAPPING.is_file():
        return fail(f"mapping missing: {MAPPING}")
    mapping_doc = json.loads(MAPPING.read_text(encoding="utf-8"))
    mapped = {item["formal_view_id"]: item["control_file_id"] for item in mapping_doc.get("views", [])}
    if len(mapped) != 24:
        return fail(f"mapping view count is {len(mapped)}, expected 24")
    BUNDLE.mkdir(parents=True, exist_ok=True)
    records = []
    for ordinal, formal_yaw in enumerate(YAWS):
        formal_id = view_id(formal_yaw)
        source_yaw = mapped_yaw(formal_yaw)
        source_id = view_id(source_yaw)
        if mapped.get(formal_id) != source_id:
            return fail(f"mapping mismatch for {formal_id}: {mapped.get(formal_id)} != {source_id}")
        outputs = {}
        for kind in KINDS:
            source = SOURCE / f"{source_id}_{kind}.png"
            target = BUNDLE / f"{formal_id}_{kind}.png"
            if not source.is_file():
                return fail(f"source missing: {source}")
            with Image.open(source) as image:
                size, mode = image.size, image.mode
            if (size, mode) != EXPECTED[kind]:
                return fail(f"source format mismatch: {source}: {size}/{mode}")
            shutil.copyfile(source, target)
            source_hash, output_hash = sha(source), sha(target)
            if source_hash != output_hash:
                return fail(f"copy hash mismatch: {source} -> {target}")
            outputs[kind] = {
                "path": str(target.relative_to(OUT)).replace("\\", "/"),
                "absolute_path": str(target),
                "source_path": str(source),
                "source_sha256": source_hash,
                "output_sha256": output_hash,
                "width": size[0],
                "height": size[1],
                "mode": mode,
            }
        records.append({
            "ordinal": ordinal,
            "formal_view_id": formal_id,
            "formal_yaw_degrees": formal_yaw,
            "source_control_file_id": source_id,
            "source_renderer_yaw_degrees": source_yaw,
            "outputs": outputs,
        })
    actual = sorted(BUNDLE.glob("*.png"))
    expected_names = {f"{view_id(yaw)}_{kind}.png" for yaw in YAWS for kind in KINDS}
    actual_names = {path.name for path in actual}
    if len(actual) != 72 or actual_names != expected_names:
        return fail(f"exact count/name gate failed: count={len(actual)} missing={sorted(expected_names-actual_names)} extra={sorted(actual_names-expected_names)}")
    contact = make_contact(records)
    manifest = {
        "schema": "mohan.candidate3-formal-controls-bundle/v1",
        "status": "PASS_GEOMETRY_CONTROLS_ONLY",
        "formal_art_status": "NOT_FINAL_ART",
        "view_count": 24,
        "controls_per_view": 3,
        "exact_png_count": 72,
        "view_order": [view_id(yaw) for yaw in YAWS],
        "mapping_rule": "source_renderer_yaw=-formal_yaw; +180 canonicalized to -180",
        "mapping_evidence": {"path": str(MAPPING), "sha256": sha(MAPPING)},
        "source_controls_root": str(SOURCE),
        "bundle_root": str(BUNDLE),
        "contact_sheet": {"path": str(contact), "sha256": sha(contact)},
        "views": records,
    }
    manifest_path = OUT / "formal-controls-manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    validation = {
        "status": "PASS",
        "exit_code": 0,
        "exact_count": len(actual),
        "expected_count": 72,
        "missing": [],
        "extra": [],
        "all_dimensions_and_modes_valid": True,
        "all_copy_hashes_equal_sources": True,
        "manifest": {"path": str(manifest_path), "sha256": sha(manifest_path)},
        "contact_sheet": {"path": str(contact), "sha256": sha(contact)},
    }
    validation_path = OUT / "validation.json"
    validation_path.write_text(json.dumps(validation, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("status=PASS_GEOMETRY_CONTROLS_ONLY")
    print("views=24")
    print("controls_per_view=3")
    print("exact_png_count=72")
    print("dimensions=1024x1536")
    print("copy_hashes_equal_sources=true")
    print(f"manifest={manifest_path}")
    print(f"contact={contact}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
