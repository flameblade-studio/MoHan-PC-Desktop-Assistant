"""將對位後的 BGRA 素材鋪回不透明洋紅 BGR PNG。"""

from __future__ import annotations

lazy import argparse
lazy from pathlib import Path

lazy from .image_ops import flatten_on_magenta, load_image, save_png


def run(source: Path, destination: Path) -> None:
    save_png(destination, flatten_on_magenta(load_image(source)))
    print(f"flattened {destination}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args(argv)
    run(args.source, args.destination)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
