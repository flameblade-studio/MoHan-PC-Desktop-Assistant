from __future__ import annotations

lazy import argparse
lazy from pathlib import Path

lazy from application.outfit_pack_builder import build_outfit_pack


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build one validated MoHan v2 outfit package.",
    )
    parser.add_argument("manifest", type=Path)
    parser.add_argument("asset_root", type=Path)
    parser.add_argument("output", type=Path)
    arguments = parser.parse_args()
    build_outfit_pack(arguments.manifest, arguments.asset_root, arguments.output)
    print(arguments.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
