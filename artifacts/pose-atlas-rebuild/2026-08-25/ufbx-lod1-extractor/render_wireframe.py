from __future__ import annotations

import argparse
import struct
import zlib
from pathlib import Path


def png_chunk(kind: bytes, payload: bytes) -> bytes:
    return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF)


def save_png(path: Path, width: int, height: int, rgb: bytearray) -> None:
    rows = bytearray()
    stride = width * 3
    for y in range(height):
        rows.append(0)
        rows.extend(rgb[y * stride : (y + 1) * stride])
    data = b"\x89PNG\r\n\x1a\n"
    data += png_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
    data += png_chunk(b"IDAT", zlib.compress(bytes(rows), 9))
    data += png_chunk(b"IEND", b"")
    path.write_bytes(data)


def draw_line(rgb: bytearray, width: int, height: int, a: tuple[int, int], b: tuple[int, int], color: tuple[int, int, int]) -> None:
    x0, y0 = a
    x1, y1 = b
    dx = abs(x1 - x0)
    sx = 1 if x0 < x1 else -1
    dy = -abs(y1 - y0)
    sy = 1 if y0 < y1 else -1
    error = dx + dy
    while True:
        if 0 <= x0 < width and 0 <= y0 < height:
            offset = (y0 * width + x0) * 3
            rgb[offset : offset + 3] = bytes(color)
        if x0 == x1 and y0 == y1:
            return
        twice = error * 2
        if twice >= dy:
            error += dy
            x0 += sx
        if twice <= dx:
            error += dx
            y0 += sy


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("obj", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    vertices: list[tuple[float, float, float]] = []
    faces: list[tuple[int, int, int]] = []
    for line in args.obj.read_text(encoding="utf-8").splitlines():
        if line.startswith("v "):
            x, y, z = map(float, line.split()[1:4])
            vertices.append((x, y, z))
        elif line.startswith("f "):
            a, b, c = (int(part.split("/")[0]) - 1 for part in line.split()[1:4])
            faces.append((a, b, c))
    if len(vertices) != 18439 or len(faces) != 36874:
        raise RuntimeError(f"unexpected topology: {len(vertices)} vertices, {len(faces)} faces")

    width, height = 1400, 900
    rgb = bytearray([248, 249, 252]) * (width * height)
    panels = ((50, 50, 625, 800, 0, 1), (725, 50, 625, 800, 2, 1))
    colors = ((22, 78, 126), (92, 44, 120))
    for panel, color in zip(panels, colors):
        left, top, panel_w, panel_h, axis_x, axis_y = panel
        xs = [v[axis_x] for v in vertices]
        ys = [v[axis_y] for v in vertices]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        scale = min((panel_w - 30) / (max_x - min_x), (panel_h - 30) / (max_y - min_y))
        offset_x = left + panel_w / 2 - (min_x + max_x) * scale / 2
        offset_y = top + panel_h / 2 + (min_y + max_y) * scale / 2

        def project(index: int) -> tuple[int, int]:
            v = vertices[index]
            return round(offset_x + v[axis_x] * scale), round(offset_y - v[axis_y] * scale)

        for a, b, c in faces:
            pa, pb, pc = project(a), project(b), project(c)
            draw_line(rgb, width, height, pa, pb, color)
            draw_line(rgb, width, height, pb, pc, color)
            draw_line(rgb, width, height, pc, pa, color)

    save_png(args.output, width, height, rgb)
    print(f"vertices={len(vertices)} faces={len(faces)} output={args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
