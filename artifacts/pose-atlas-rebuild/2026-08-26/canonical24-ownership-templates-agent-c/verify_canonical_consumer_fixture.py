"""Run the accepted yaw000 v12 ownership fixture through the canonical consumer."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image


HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[3]


def alpha_pixels(path: Path) -> int:
    with Image.open(path) as image:
        if image.mode == "RGBA":
            alpha = np.asarray(image, dtype=np.uint8)[:, :, 3]
        else:
            alpha = np.asarray(image.convert("L"), dtype=np.uint8)
    return int(np.count_nonzero(alpha))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--fixture",
        type=Path,
        default=HERE / "canonical_consumer_v12_fixture.json",
    )
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--repo", type=Path, default=PROJECT)
    args = parser.parse_args()

    repo = args.repo.resolve()
    fixture = json.loads(args.fixture.read_text(encoding="utf-8"))
    view = str(fixture["view_id"])
    source_master = repo / fixture["master_rgba"]
    command = [
        sys.executable,
        str(HERE / "postprocess_one_canonical_view.py"),
        "--view-id",
        view,
        "--master",
        str(source_master),
        "--output-root",
        str(args.output_root.resolve()),
        "--outfit-guard",
        str(repo / fixture["outfit_guard"]),
        "--repo",
        str(repo),
    ]
    for seed in fixture["hair_seeds"]:
        command.extend(("--hair-seed", str(repo / seed)))
    subprocess.run(command, check=True)

    runs = tuple(args.output_root.glob(f"postprocess-{view}-*"))
    if len(runs) != 1:
        raise RuntimeError(f"expected one fixture run, got {len(runs)}")
    run = runs[0]
    results = tuple(run.glob("split/batch-*/batch-result.json"))
    if len(results) != 1:
        raise RuntimeError(f"expected one batch result, got {len(results)}")
    result = json.loads(results[0].read_text(encoding="utf-8"))["results"][0]
    expected = fixture["expected"]
    actual = {
        "source_file_sha256": sha256(source_master),
        "master_sha256": result["master_sha256"],
        "hair_pixels": alpha_pixels(run / "ownership" / f"{view}_hair_mask.png"),
        "outfit_pixels": result["outfit_alpha_pixels"],
        "ornament_pixels": result["ornament_alpha_pixels"],
        "core_file_count": result["core_file_count"],
        "ownership_overlap_pixels": result["ownership_overlap_pixels"],
        "core_outfit_overlap_pixels": result["core_outfit_overlap_pixels"],
        "core_ornament_overlap_pixels": result["core_ornament_overlap_pixels"],
        "recompose_diff_pixels": result["recompose_diff_pixels"],
        "recompose_max_channel_error": result["recompose_max_channel_error"],
    }
    mismatch = {
        key: {"expected": expected[key], "actual": actual.get(key)}
        for key in expected
        if actual.get(key) != expected[key]
    }
    if mismatch:
        raise RuntimeError(f"v12 fixture mismatch: {mismatch}")
    print(json.dumps({"status": "PASS_V12_CANONICAL_CONSUMER", "view_id": view, **actual}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
