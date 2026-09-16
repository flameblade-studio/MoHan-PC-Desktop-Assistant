"""Capture the existing runtime inputs as a reviewable, source-pinned manifest."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from tools.art_pipeline.source_bound_stage import SCHEMA, VIEW_PATTERN, digest

SHARED_DIRECTORIES = (
    "assets/official-packs", "assets/pose-atlas/v5-base-layered",
    "assets/makeup-foundation-safe-regions", "assets/makeup-eye-apertures",
)
VIEW_DIRECTORIES = (
    "assets/pose-atlas/v5-base", "assets/pose-atlas/v5-body-overlays",
    "assets/pose-atlas/v5-hand-overlays", "assets/pose-atlas/v5-appearance-silhouettes",
    "assets/pose-atlas/v5-appearance-replacement-masks",
)


def capture_manifest(root: Path, view: str) -> dict:
    """Capture shared loader inputs and only the selected view's native data."""
    if not VIEW_PATTERN.fullmatch(view):
        raise ValueError("Use a canonical view identifier.")
    paths = {root / "assets/makeup-safe-regions.json"}
    for directory in SHARED_DIRECTORIES:
        paths.update(path for path in (root / directory).rglob("*") if path.is_file())
    for directory in VIEW_DIRECTORIES:
        paths.update(
            path for path in (root / directory).rglob(f"{view}*")
            if path.is_file() and path.name.startswith((f"{view}.", f"{view}_"))
        )
    for path in paths:
        if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
            raise ValueError(f"Captured input escapes its canonical repository: {path}")
    files = [
        {"source": path.relative_to(root).as_posix(), "target": path.relative_to(root).as_posix(),
         "sha256": digest(path.read_bytes())}
        for path in sorted(paths)
    ]
    native_target = f"assets/pose-atlas/v5-base/{view}.png"
    native = next(pin for pin in files if pin["target"] == native_target)
    return {
        "schema": SCHEMA, "view_id": view, "native": native,
        "pack_id": "mohan.official.blue-white-hanfu", "ensemble_id": "blue-white-hanfu",
        "makeup": "classic", "files": files, "pack_updates": [],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--view", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    args = parser.parse_args()
    args.root = args.root.resolve()
    args.output = args.output.resolve()
    if not args.output.is_relative_to(args.root / "scratchpad"):
        raise ValueError("Manifest output must be under the repository scratchpad.")
    manifest = capture_manifest(args.root, args.view)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(manifest, indent=2) + "\n")
    print(f"Captured {len(manifest['files'])} pinned inputs: {args.output}")


if __name__ == "__main__":
    main()
