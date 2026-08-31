"""把 candidate3 與三個 candidate4 版本並排渲染，供擁有者用眼睛挑。

數字已經證明軀幹沒被動到、四肢命中目標，但「哪個百分位好看」是美術判斷，
不是量測能回答的。所以要出圖。

正交投影＋z-buffer＋Lambert 著色，與產線用的 CPU 光柵化器同一套原理
（真 15 度旋轉、固定正交相機），這裡只需要正面與側面兩個視角做比較。
"""
import os
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from thresholds import DEGENERATE_AREA, DEGENERATE_AREA_LOOSE

ROOT = Path(os.environ.get(
    "MOHAN_VISION_ROOT",
    r"D:\FlamebladeStudio\CodexProjects\2026-08-13\mohan-multisensory-vision",
))
LIMB = ROOT / "work/second-gen-body/limb-morph"
EXTRACT = ROOT / "artifacts/pose-atlas-rebuild/2026-08-25/ufbx-lod1-extractor-agent-a"
WIDTH, HEIGHT = 300, 700
LIGHT = np.asarray([0.35, 0.55, 0.76])
LIGHT = LIGHT / np.linalg.norm(LIGHT)


def load_obj(path: Path):
    vertices, faces = [], []
    with path.open("r", encoding="utf-8") as stream:
        for line in stream:
            if line.startswith("v "):
                vertices.append([float(v) for v in line.split()[1:4]])
            elif line.startswith("f "):
                faces.append([int(t.split("/")[0]) - 1 for t in line.split()[1:4]])
    return np.asarray(vertices, np.float64), np.asarray(faces, np.int64)


def render(vertices: np.ndarray, faces: np.ndarray, yaw_degrees: float) -> Image.Image:
    angle = np.radians(yaw_degrees)
    cos, sin = np.cos(angle), np.sin(angle)
    rotated = vertices.copy()
    rotated[:, 0] = vertices[:, 0] * cos + vertices[:, 2] * sin
    rotated[:, 2] = -vertices[:, 0] * sin + vertices[:, 2] * cos

    low = rotated.min(axis=0)
    high = rotated.max(axis=0)
    scale = (HEIGHT * 0.94) / (high[1] - low[1])
    centre_x = (low[0] + high[0]) / 2.0
    screen_x = (rotated[:, 0] - centre_x) * scale + WIDTH / 2.0
    screen_y = HEIGHT - (rotated[:, 1] - low[1]) * scale - HEIGHT * 0.03

    colour = np.full((HEIGHT, WIDTH, 3), 236, np.float32)
    depth = np.full((HEIGHT, WIDTH), -np.inf, np.float32)
    a, b, c = rotated[faces[:, 0]], rotated[faces[:, 1]], rotated[faces[:, 2]]
    normals = np.cross(b - a, c - a)
    lengths = np.linalg.norm(normals, axis=1)
    keep = lengths > DEGENERATE_AREA
    normals[keep] /= lengths[keep][:, None]
    shade = np.clip(np.abs(normals @ LIGHT), 0.0, 1.0) * 0.72 + 0.22

    px = np.stack([screen_x[faces[:, 0]], screen_x[faces[:, 1]], screen_x[faces[:, 2]]], 1)
    py = np.stack([screen_y[faces[:, 0]], screen_y[faces[:, 1]], screen_y[faces[:, 2]]], 1)
    pz = np.stack([rotated[faces[:, 0], 2], rotated[faces[:, 1], 2], rotated[faces[:, 2], 2]], 1)
    order = np.argsort(pz.mean(axis=1))          # 由遠到近，配合 z-buffer
    for index in order:
        x0, x1 = int(np.floor(px[index].min())), int(np.ceil(px[index].max()))
        y0, y1 = int(np.floor(py[index].min())), int(np.ceil(py[index].max()))
        if x1 < 0 or y1 < 0 or x0 >= WIDTH or y0 >= HEIGHT:
            continue
        x0, y0 = max(x0, 0), max(y0, 0)
        x1, y1 = min(x1, WIDTH - 1), min(y1, HEIGHT - 1)
        if x1 < x0 or y1 < y0:
            continue
        xs = np.arange(x0, x1 + 1)
        ys = np.arange(y0, y1 + 1)
        gx, gy = np.meshgrid(xs + 0.5, ys + 0.5)
        ax, ay = px[index, 0], py[index, 0]
        bx, by = px[index, 1], py[index, 1]
        cx, cy = px[index, 2], py[index, 2]
        area = (bx - ax) * (cy - ay) - (cx - ax) * (by - ay)
        if abs(area) < DEGENERATE_AREA_LOOSE:
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
        colour[y0:y1 + 1, x0:x1 + 1][better] = shade[index] * 232
    return Image.fromarray(colour.clip(0, 255).astype(np.uint8), "RGB")


def font(size: int):
    for name in ("msjh.ttc", "msyh.ttc"):
        try:
            return ImageFont.truetype(rf"C:\Windows\Fonts\{name}", size)
        except OSError:
            continue
    return ImageFont.load_default()


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    panels = [
        (EXTRACT / "body-morph-candidate3/candidate3.obj", "candidate3 現況", "上臂 34.4 cm（P94）"),
        (LIMB / "candidate4-p50.obj", "candidate4 P50", "上臂 26.8 cm"),
        (LIMB / "candidate4-p25.obj", "candidate4 P25", "上臂 24.5 cm"),
        (LIMB / "candidate4-p10.obj", "candidate4 P10", "上臂 22.5 cm"),
    ]
    columns = []
    for path, title, note in panels:
        if not path.exists():
            print(f"缺 {path.name}")
            continue
        vertices, faces = load_obj(path)
        front = render(vertices, faces, 0.0)
        side = render(vertices, faces, 90.0)
        pair = Image.new("RGB", (WIDTH * 2, HEIGHT), (236, 236, 236))
        pair.paste(front, (0, 0))
        pair.paste(side, (WIDTH, 0))
        columns.append((pair, title, note))
        print(f"渲染 {title}")

    gap, top = 12, 56
    sheet = Image.new("RGB",
                      (sum(c.width for c, _, _ in columns) + gap * (len(columns) - 1),
                       HEIGHT + top), (250, 250, 250))
    draw = ImageDraw.Draw(sheet)
    big, small = font(22), font(16)
    x = 0
    for pair, title, note in columns:
        sheet.paste(pair, (x, top))
        draw.text((x + 8, 8), title, fill=(15, 15, 15), font=big)
        draw.text((x + 8, 33), note, fill=(95, 95, 95), font=small)
        x += pair.width + gap
    out = LIMB / "candidate4-comparison.png"
    sheet.save(out)
    print(f"\n{out}  {sheet.size}")


if __name__ == "__main__":
    main()
