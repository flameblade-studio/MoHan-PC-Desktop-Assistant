"""用 candidate4-p25 重渲染 24 組控制圖（silhouette / normal / shaded-render）。

相機常數全部沿用 candidate3 的官方契約，一個都不重新推導——
新控制圖必須與既有的 yaw 符號約定、像素對位完全一致，否則整條產線的
座標語意就斷了。契約來源：candidate3-camera-anchor-control-manifest.json

    正交投影，畫布 1024x1536，scale 7.251301847932881 px/世界單位
    y 中心 83.94300423461144，pitch 0，yaw 繞 Y
    x' = cos(yaw)*x + sin(yaw)*z ; y' = y ; z' = -sin(yaw)*x + cos(yaw)*z
    formal yaw 對應的 renderer-native yaw 為其負值

shaded-render 不是自由創作，是既有 build_canonical24_control_bundles.py 的
shade() 逐式複製：光向 [-.35,-.45,.82] 正規化、value = .22+.78*clip(n·l,0,1)、
前景 value*[185,195,210]、背景 22。

出跑前先渲染 candidate3 與官方控制圖逐像素比對；比對不過就中止，
不拿一個沒被驗證的渲染器去產下游要用的權威輸入。
"""
import argparse
import os
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from thresholds import DEGENERATE_AREA, RENDER_IOU_MIN, RENDER_NORMAL_COSINE_MIN

ROOT = Path(os.environ.get(
    "MOHAN_VISION_ROOT",
    r"D:\FlamebladeStudio\CodexProjects\2026-08-13\mohan-multisensory-vision",
))
EXTRACT = ROOT / "artifacts/pose-atlas-rebuild/2026-08-25/ufbx-lod1-extractor-agent-a"
OFFICIAL = EXTRACT / "candidate3-yaw-controls-24/controls"
LIMB = ROOT / "work/second-gen-body/limb-morph"
OUT = ROOT / "work/second-gen-body/candidate6-controls"

WIDTH, HEIGHT = 1024, 1536
SCALE = 7.251301847932881
Y_CENTRE = 83.94300423461144
LIGHT = np.asarray([-0.35, -0.45, 0.82], np.float32)
LIGHT = LIGHT / np.linalg.norm(LIGHT)
FORMAL_YAWS = [0, 15, 30, 45, 60, 75, 90, 105, 120, 135, 150, 165, 180,
               -15, -30, -45, -60, -75, -90, -105, -120, -135, -150, -165]


def load_obj(path: Path):
    vertices, faces = [], []
    with path.open("r", encoding="utf-8") as stream:
        for line in stream:
            if line.startswith("v "):
                vertices.append([float(v) for v in line.split()[1:4]])
            elif line.startswith("f "):
                faces.append([int(t.split("/")[0]) - 1 for t in line.split()[1:4]])
    return np.asarray(vertices, np.float64), np.asarray(faces, np.int64)


def render(vertices: np.ndarray, faces: np.ndarray, native_yaw: float):
    angle = np.radians(native_yaw)
    cos, sin = np.cos(angle), np.sin(angle)
    view = np.empty_like(vertices)
    view[:, 0] = vertices[:, 0] * cos + vertices[:, 2] * sin
    view[:, 1] = vertices[:, 1]
    view[:, 2] = -vertices[:, 0] * sin + vertices[:, 2] * cos

    sx = WIDTH / 2.0 + view[:, 0] * SCALE
    sy = HEIGHT / 2.0 - (view[:, 1] - Y_CENTRE) * SCALE

    a, b, c = view[faces[:, 0]], view[faces[:, 1]], view[faces[:, 2]]
    normals = np.cross(b - a, c - a)
    lengths = np.linalg.norm(normals, axis=1)
    good = lengths > DEGENERATE_AREA
    normals[good] /= lengths[good][:, None]

    px = np.stack([sx[faces[:, 0]], sx[faces[:, 1]], sx[faces[:, 2]]], 1)
    py = np.stack([sy[faces[:, 0]], sy[faces[:, 1]], sy[faces[:, 2]]], 1)
    pz = np.stack([view[faces[:, 0], 2], view[faces[:, 1], 2], view[faces[:, 2], 2]], 1)

    depth = np.full((HEIGHT, WIDTH), -np.inf, np.float64)
    normal_buffer = np.zeros((HEIGHT, WIDTH, 3), np.float64)
    mask = np.zeros((HEIGHT, WIDTH), bool)

    for index in range(len(faces)):
        x0 = int(np.floor(px[index].min())); x1 = int(np.ceil(px[index].max()))
        y0 = int(np.floor(py[index].min())); y1 = int(np.ceil(py[index].max()))
        if x1 < 0 or y1 < 0 or x0 >= WIDTH or y0 >= HEIGHT:
            continue
        x0, y0 = max(x0, 0), max(y0, 0)
        x1, y1 = min(x1, WIDTH - 1), min(y1, HEIGHT - 1)
        if x1 < x0 or y1 < y0:
            continue
        gx, gy = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
        ax, ay = px[index, 0], py[index, 0]
        bx, by = px[index, 1], py[index, 1]
        cx, cy = px[index, 2], py[index, 2]
        area = (bx - ax) * (cy - ay) - (cx - ax) * (by - ay)
        if abs(area) < DEGENERATE_AREA:
            continue
        w0 = ((bx - gx) * (cy - gy) - (cx - gx) * (by - gy)) / area
        w1 = ((cx - gx) * (ay - gy) - (ax - gx) * (cy - gy)) / area
        w2 = 1.0 - w0 - w1
        inside = (w0 >= 0) & (w1 >= 0) & (w2 >= 0)
        if not inside.any():
            continue
        z = w0 * pz[index, 0] + w1 * pz[index, 1] + w2 * pz[index, 2]
        window = depth[y0:y1 + 1, x0:x1 + 1]
        better = inside & (z > window)
        if not better.any():
            continue
        window[better] = z[better]
        normal_buffer[y0:y1 + 1, x0:x1 + 1][better] = normals[index]
        mask[y0:y1 + 1, x0:x1 + 1][better] = True
    return normal_buffer, mask


def encode_normal(normal_buffer: np.ndarray, mask: np.ndarray) -> Image.Image:
    encoded = np.zeros((HEIGHT, WIDTH, 3), np.uint8)
    values = np.clip((normal_buffer + 1.0) * 0.5 * 255.0, 0, 255).astype(np.uint8)
    encoded[mask] = values[mask]
    return Image.fromarray(encoded, "RGB")


def shade(normal_image: Image.Image, silhouette: Image.Image):
    """逐式複製 build_canonical24_control_bundles.py 的 shade()。"""
    encoded = np.asarray(normal_image.convert("RGB"), dtype=np.float32) / 255
    normals = encoded * 2 - 1
    value = .22 + .78 * np.clip(np.sum(normals * LIGHT, axis=2), 0, 1)
    mask = np.asarray(silhouette.convert("L")) > 0
    base = np.full((*mask.shape, 3), 22, dtype=np.uint8)
    shaded = base.copy()
    base[mask] = [174, 184, 200]
    lit = np.clip(value[..., None] * np.asarray([185, 195, 210]), 0, 255).astype(np.uint8)
    shaded[mask] = lit[mask]
    return Image.fromarray(base, "RGB"), Image.fromarray(shaded, "RGB")


def validate() -> bool:
    """先用官方 candidate3 驗證這支渲染器，不過就不准往下產。"""
    vertices, faces = load_obj(EXTRACT / "body-morph-candidate3/candidate3.obj")
    print("── 渲染器驗證（candidate3 對官方控制圖）──")
    ok = True
    for formal in (0, 90, -90):
        native = -formal
        name = f"yaw{native:+04d}-pitch+00"
        official_sil = OFFICIAL / f"{name}_silhouette.png"
        official_nrm = OFFICIAL / f"{name}_normal.png"
        if not official_sil.exists():
            print(f"  {name}: 官方檔不存在，略過")
            continue
        normal_buffer, mask = render(vertices, faces, native)
        mine = mask
        theirs = np.asarray(Image.open(official_sil).convert("L")) > 0
        intersection = np.logical_and(mine, theirs).sum()
        union = np.logical_or(mine, theirs).sum()
        iou = intersection / union if union else 0.0
        their_normal = np.asarray(Image.open(official_nrm).convert("RGB"), np.float32) / 255 * 2 - 1
        both = mine & theirs
        cosine = float(np.mean(np.sum(their_normal[both] * normal_buffer[both], axis=1))) \
            if both.any() else 0.0
        good = iou >= RENDER_IOU_MIN and cosine >= RENDER_NORMAL_COSINE_MIN
        ok &= good
        print(f"  {name}  剪影 IoU {iou:.4f}   法線平均餘弦 {cosine:+.4f}   "
              f"{'OK' if good else '← 不符'}")
    print("  → 渲染器可信\n" if ok else "  → 渲染器與官方不符，中止\n")
    return ok


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=LIMB / "candidate6-p25-armsdown-dqs.obj")
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--skip-validation", action="store_true")
    args = parser.parse_args()
    global OUT
    if args.out is not None:
        OUT = args.out

    if not args.skip_validation and not validate():
        raise SystemExit(1)

    OUT.mkdir(parents=True, exist_ok=True)
    vertices, faces = load_obj(args.source)
    print(f"來源 {args.source.name}：{len(vertices)} 頂點、{len(faces)} 三角形")
    for formal in FORMAL_YAWS:
        native = -formal
        formal_name = f"yaw{formal:+04d}-pitch+00"
        target = OUT / f"{formal_name}_shaded-render.png"
        if target.exists():
            print(f"  skip {formal_name}", flush=True)
            continue
        normal_buffer, mask = render(vertices, faces, native)
        silhouette = Image.fromarray((mask * 255).astype(np.uint8), "L")
        normal_image = encode_normal(normal_buffer, mask)
        _base, shaded = shade(normal_image, silhouette)
        silhouette.save(OUT / f"{formal_name}_silhouette.png")
        normal_image.save(OUT / f"{formal_name}_normal.png")
        shaded.save(target)
        print(f"  done {formal_name}  前景 {mask.mean()*100:5.2f}%", flush=True)
    print("C4_CONTROLS_DONE")


if __name__ == "__main__":
    main()
