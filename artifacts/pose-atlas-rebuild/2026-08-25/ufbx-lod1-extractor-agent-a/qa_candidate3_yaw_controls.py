from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont


YAWS = tuple(range(-180, 180, 15))
VIEW_IDS = tuple(f"yaw{yaw:+04d}-pitch+00" for yaw in YAWS)
KINDS = {"silhouette": "L", "depth": "L", "normal": "RGB"}
SIZE = (1024, 1536)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def mask_metrics(mask: np.ndarray) -> dict:
    ys, xs = np.where(mask)
    if not len(xs):
        raise ValueError("Empty silhouette")
    return {
        "foreground_pixels": int(mask.sum()),
        "bbox_xyxy_inclusive": [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())],
        "centroid_xy": [float(xs.mean()), float(ys.mean())],
    }


def contour_mae(a: np.ndarray, b: np.ndarray) -> dict:
    rows = np.flatnonzero(a.any(axis=1) & b.any(axis=1))
    left_errors = []
    right_errors = []
    for row in rows:
        ax = np.flatnonzero(a[row])
        bx = np.flatnonzero(b[row])
        left_errors.append(abs(int(ax[0]) - int(bx[0])))
        right_errors.append(abs(int(ax[-1]) - int(bx[-1])))
    return {
        "common_rows": int(len(rows)),
        "left_contour_mae_px": float(np.mean(left_errors)),
        "right_contour_mae_px": float(np.mean(right_errors)),
        "mean_lr_contour_mae_px": float((np.mean(left_errors) + np.mean(right_errors)) / 2),
    }


def build_contact_sheet(controls: Path, output: Path) -> None:
    panel_w, panel_h = 256, 384
    header = 52
    sheet = Image.new("RGB", (panel_w * 6, header + panel_h * 4), "white")
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default(size=14)
    title = "CANDIDATE3 GEOMETRY CONTROL ONLY - NOT FINAL ART"
    draw.text((18, 15), title, fill=(170, 20, 20), font=font)
    for index, view in enumerate(VIEW_IDS):
        normal = Image.open(controls / f"{view}_normal.png").convert("RGB").resize((panel_w, panel_h))
        silhouette = Image.open(controls / f"{view}_silhouette.png").convert("RGB").resize((80, 120))
        depth = Image.open(controls / f"{view}_depth.png").convert("RGB").resize((80, 120))
        x = (index % 6) * panel_w
        y = header + (index // 6) * panel_h
        sheet.paste(normal, (x, y))
        sheet.paste(silhouette, (x + 4, y + 28))
        sheet.paste(depth, (x + panel_w - 84, y + 28))
        panel_draw = ImageDraw.Draw(sheet)
        panel_draw.rectangle((x, y, x + panel_w - 1, y + panel_h - 1), outline=(50, 50, 50))
        panel_draw.rectangle((x + 3, y + 3, x + 154, y + 25), fill=(255, 255, 255))
        panel_draw.text((x + 7, y + 6), view, fill=(10, 10, 10), font=font)
        panel_draw.text((x + 7, y + 151), "S", fill=(255, 255, 255), font=font)
        panel_draw.text((x + panel_w - 78, y + 151), "D", fill=(255, 255, 255), font=font)
    sheet.save(output)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--controls", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--contact-sheet", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()

    errors = []
    records = []
    masks = []
    actual_names = {path.name for path in args.controls.glob("*.png")}
    expected_names = {f"{view}_{kind}.png" for view in VIEW_IDS for kind in KINDS}
    if actual_names != expected_names:
        errors.append({"file_set": {"missing": sorted(expected_names - actual_names), "extra": sorted(actual_names - expected_names)}})
    for view in VIEW_IDS:
        view_mask = None
        for kind, expected_mode in KINDS.items():
            path = args.controls / f"{view}_{kind}.png"
            if not path.is_file():
                continue
            with Image.open(path) as image:
                mode = image.mode
                size = image.size
                array = np.asarray(image)
            if size != SIZE or mode != expected_mode:
                errors.append({"format": [view, kind, list(size), mode]})
            nonzero = np.any(array != 0, axis=2) if array.ndim == 3 else array != 0
            entry = {
                "view_id": view,
                "kind": kind,
                "path": str(path.resolve()),
                "width": size[0],
                "height": size[1],
                "mode": mode,
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
                "nonzero_pixels": int(nonzero.sum()),
            }
            if nonzero.any():
                ys, xs = np.where(nonzero)
                entry["bbox_xyxy_inclusive"] = [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())]
                if xs.min() == 0 or ys.min() == 0 or xs.max() == size[0] - 1 or ys.max() == size[1] - 1:
                    errors.append({"touches_canvas": [view, kind, entry["bbox_xyxy_inclusive"]]})
            records.append(entry)
            if kind == "silhouette":
                view_mask = nonzero
                entry.update(mask_metrics(nonzero))
        if view_mask is not None:
            masks.append(view_mask)

    transitions = []
    if len(masks) == 24:
        for index, view in enumerate(VIEW_IDS):
            following = (index + 1) % 24
            a, b = masks[index], masks[following]
            intersection = int(np.logical_and(a, b).sum())
            union = int(np.logical_or(a, b).sum())
            ay, ax = np.where(a)
            by, bx = np.where(b)
            contour = contour_mae(a, b)
            transition = {
                "from": view,
                "to": VIEW_IDS[following],
                "wrap": index == 23,
                "iou": intersection / union,
                "xor_over_union": int(np.logical_xor(a, b).sum()) / union,
                "centroid_shift_px": float(np.hypot(ax.mean() - bx.mean(), ay.mean() - by.mean())),
                **contour,
            }
            transition["continuity_gate"] = transition["iou"] >= 0.80 and transition["centroid_shift_px"] <= 24.0
            if not transition["continuity_gate"]:
                errors.append({"continuity": transition})
            transitions.append(transition)
    build_contact_sheet(args.controls, args.contact_sheet)
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    source_hash = manifest.get("source", {}).get("vertices", {}).get("sha256", "").upper()
    report = {
        "status": "PASS_GEOMETRY_CONTROLS_ONLY_NOT_FINAL_ART" if not errors else "FAIL",
        "notice": "CANDIDATE3 GEOMETRY CONTROL ONLY - NOT FINAL ART",
        "forbidden_components_used": False,
        "candidate3_source_sha256": source_hash,
        "expected_candidate3_source_sha256": "23C5ECB3E943089954459F9F16E5551F0413571F5BACF85E3C3A6DCF155318A4",
        "candidate3_source_matches": source_hash == "23C5ECB3E943089954459F9F16E5551F0413571F5BACF85E3C3A6DCF155318A4",
        "exact_png_count": len(actual_names),
        "per_kind_counts": {kind: sum(record["kind"] == kind for record in records) for kind in KINDS},
        "canvas": list(SIZE),
        "modes": KINDS,
        "depth_quantization": "8-bit grayscale; 0 background, visible range normalized to 1..255 using fixed radial range",
        "camera": "fixed orthographic, Y-up, yaw step 15 degrees",
        "transitions": transitions,
        "observed": {
            "iou_range": [min(item["iou"] for item in transitions), max(item["iou"] for item in transitions)],
            "centroid_shift_px_range": [min(item["centroid_shift_px"] for item in transitions), max(item["centroid_shift_px"] for item in transitions)],
            "mean_lr_contour_mae_px_range": [min(item["mean_lr_contour_mae_px"] for item in transitions), max(item["mean_lr_contour_mae_px"] for item in transitions)],
        },
        "wrap_transition": transitions[-1],
        "contact_sheet": {"path": str(args.contact_sheet.resolve()), "sha256": sha256(args.contact_sheet), "size": list(Image.open(args.contact_sheet).size), "mode": Image.open(args.contact_sheet).mode},
        "manifest": {"path": str(args.manifest.resolve()), "sha256": sha256(args.manifest)},
        "errors": errors,
        "records": records,
    }
    if not report["candidate3_source_matches"]:
        report["errors"].append({"candidate3_source_hash_mismatch": source_hash})
        report["status"] = "FAIL"
    args.report.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({
        "status": report["status"],
        "png_count": report["exact_png_count"],
        "iou_range": report["observed"]["iou_range"],
        "centroid_shift_range": report["observed"]["centroid_shift_px_range"],
        "contour_mae_range": report["observed"]["mean_lr_contour_mae_px_range"],
        "wrap": report["wrap_transition"],
        "contact_sheet": report["contact_sheet"],
    }, indent=2))
    if report["status"] == "FAIL":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
