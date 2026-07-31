from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtGui import QImage


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets" / "expressions"
POSES = {
    "": "idle.png",
    "_lean": "idle_lean.png",
    "_front": "idle_front.png",
}
LAYERS = (
    "sleeve_left",
    "sleeve_right",
    "hair_left",
    "hair_right",
    "ornament",
    "face",
    "eyes",
)


def run() -> None:
    checked = 0
    for suffix, source_name in POSES.items():
        source = QImage(str(ASSETS / source_name)).convertToFormat(
            QImage.Format_RGBA8888
        )
        assert not source.isNull()
        source_bytes = bytes(source.bits())
        for layer_name in LAYERS:
            path = ASSETS / f"v120_{layer_name}{suffix}.png"
            assert path.exists(), path
            layer = QImage(str(path)).convertToFormat(
                QImage.Format_RGBA8888
            )
            assert not layer.isNull()
            assert layer.size() == source.size()
            layer_bytes = bytes(layer.bits())
            visible_count = 0
            feather_count = 0
            for offset in range(0, len(layer_bytes), 4):
                alpha = layer_bytes[offset + 3]
                if alpha == 0:
                    assert layer_bytes[offset : offset + 3] == b"\x00\x00\x00", (
                        f"transparent RGB contamination: {path}"
                    )
                    continue
                visible_count += 1
                assert (
                    layer_bytes[offset : offset + 3]
                    == source_bytes[offset : offset + 3]
                ), (
                    f"non-original color introduced: {path}"
                )
                if alpha < 220:
                    feather_count += 1
            assert visible_count > 100, path
            assert feather_count > 80, f"hard edge lacks feather: {path}"
            checked += 1
    assert checked == 21
    print("V120_ASSET_INTEGRITY_OK")


if __name__ == "__main__":
    run()
