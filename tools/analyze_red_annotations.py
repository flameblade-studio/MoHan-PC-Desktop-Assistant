from __future__ import annotations

import sys
from collections import deque
from pathlib import Path

from PIL import Image


def boxes(path: Path) -> list[tuple[int, int, int, int]]:
    image = Image.open(path).convert("RGB")
    red = {
        (x, y)
        for y in range(image.height)
        for x in range(image.width)
        if (
            image.getpixel((x, y))[0] > 220
            and image.getpixel((x, y))[1] < 90
            and image.getpixel((x, y))[2] < 90
        )
    }
    result = []
    while red:
        start = red.pop()
        queue = deque((start,))
        component = [start]
        while queue:
            x, y = queue.popleft()
            for neighbor in (
                (x - 1, y),
                (x + 1, y),
                (x, y - 1),
                (x, y + 1),
            ):
                if neighbor in red:
                    red.remove(neighbor)
                    queue.append(neighbor)
                    component.append(neighbor)
        if len(component) < 8:
            continue
        xs = [point[0] for point in component]
        ys = [point[1] for point in component]
        result.append((min(xs), min(ys), max(xs) + 1, max(ys) + 1))
    return sorted(result, key=lambda box: (box[1], box[0]))


if __name__ == "__main__":
    source = Path(sys.argv[1])
    image = Image.open(source)
    row_height = image.height / 22
    for box in boxes(source):
        center_y = (box[1] + box[3]) / 2
        row = min(22, max(1, int(center_y / row_height) + 1))
        column = min(
            4,
            max(1, int(((box[0] + box[2]) / 2) / (image.width / 4)) + 1),
        )
        print(f"row={row:02d} col={column} box={box}")
