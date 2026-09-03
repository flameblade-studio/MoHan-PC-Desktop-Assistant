"""Scaffold an authoring manifest for a makeup-only ``.mohan-outfit`` pack.

The scaffold declares one makeup item with any number of variants and the full
31-silhouette × 3-slot layer set each variant needs.  ``sha256``, ``width`` and
``height`` are left blank on purpose: ``tools/build_outfit_pack.py`` fills them
from the PNG files the artist drops under ``<asset_root>/assets/`` and rejects
the pack if a file is missing, off-canvas or paints outside the safe region.

Example (the official built-in item)::

    py -3.15 tools/scaffold_makeup_pack_manifest.py assets/makeup/builtin/manifest.json \
        --pack-id mohan.makeup.builtin --pack-name "墨寒內建妝容|墨寒内置妆容|MoHan built-in makeup|墨寒内蔵メイク" \
        --item-id mohan-face --item-name "墨寒妝容|墨寒妆容|MoHan face makeup|墨寒メイク" \
        --variant "classic:原妝|原妆|Classic|原妝" --variant "light:淡雅|淡雅|Light|淡雅"
"""

from __future__ import annotations

lazy import argparse
lazy import json
lazy import sys
lazy from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

lazy from domain.outfit_pack import (
    AUTHORING_TEMPLATE,
    AUTHORING_VERSION,
    BODY_PROFILE_ID,
    BODY_PROFILE_VERSION,
    FORMAT,
    REQUIRED_SILHOUETTES,
    VERSION,
)

LANGUAGE_ORDER = ("zh-TW", "zh-CN", "en", "ja-JP")
SLOT_Z_ORDER = (("cheeks", 0), ("eyes", 1), ("lips", 2))


def localized(spec: str) -> dict[str, str]:
    parts = [part.strip() for part in spec.split("|")]
    if len(parts) != len(LANGUAGE_ORDER) or any(not part for part in parts):
        raise SystemExit(f"Names need four '|'-separated values (zh-TW|zh-CN|en|ja-JP): {spec!r}")
    return dict(zip(LANGUAGE_ORDER, parts, strict=True))


def variant_entry(item_id: str, spec: str) -> dict[str, object]:
    variant_id, separator, names = spec.partition(":")
    if not separator:
        raise SystemExit(f"Variant needs the form id:zh-TW|zh-CN|en|ja-JP: {spec!r}")
    poses = {
        silhouette: [
            {
                "slot": slot,
                "path": f"assets/{item_id}-{variant_id}-{silhouette}-{slot}.png",
                "sha256": "",
                "width": 0,
                "height": 0,
                "anchor": [0, 0],
                "z_order": z_order,
            }
            for slot, z_order in SLOT_Z_ORDER
        ]
        for silhouette in REQUIRED_SILHOUETTES
    }
    return {"id": variant_id, "display_names": localized(names), "intensity": 1.0, "poses": poses}


def scaffold(arguments: argparse.Namespace) -> dict[str, object]:
    return {
        "format": FORMAT,
        "version": VERSION,
        "id": arguments.pack_id,
        "pack_version": arguments.pack_version,
        "app_range": arguments.app_range,
        "display_names": localized(arguments.pack_name),
        "compatible_body_profile": {"id": BODY_PROFILE_ID, "version": BODY_PROFILE_VERSION},
        "source": {
            "kind": "original",
            "author": arguments.author,
            "license": arguments.license,
            "reference_included": False,
        },
        "authoring": {"template": AUTHORING_TEMPLATE, "version": AUTHORING_VERSION},
        "looks": [],
        "hairstyles": [],
        "headwear": [],
        "makeup": [{
            "id": arguments.item_id,
            "display_names": localized(arguments.item_name),
            "variants": [variant_entry(arguments.item_id, spec) for spec in arguments.variant],
        }],
        "accessories": [],
        "ensembles": [],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("output", type=Path)
    parser.add_argument("--pack-id", required=True)
    parser.add_argument("--pack-name", required=True, help="zh-TW|zh-CN|en|ja-JP")
    parser.add_argument("--item-id", required=True)
    parser.add_argument("--item-name", required=True, help="zh-TW|zh-CN|en|ja-JP")
    parser.add_argument("--variant", action="append", required=True, help="id:zh-TW|zh-CN|en|ja-JP (repeatable)")
    parser.add_argument("--author", default="Flameblade Studio")
    parser.add_argument("--license", default="CC BY 4.0")
    parser.add_argument("--pack-version", default="1.0.0")
    parser.add_argument("--app-range", default=">=4.0.0,<5.0.0")
    arguments = parser.parse_args(argv)
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(
        json.dumps(scaffold(arguments), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(arguments.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
