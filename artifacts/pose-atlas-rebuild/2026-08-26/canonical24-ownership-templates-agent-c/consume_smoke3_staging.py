"""Consume available views24_generate Smoke3 outputs without blank fallbacks."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from PIL import Image


SMOKE3_VIEWS = ("yaw+000-pitch+00", "yaw+045-pitch+00", "yaw+090-pitch+00")
CANONICAL_VIEWS = tuple(f"yaw{yaw:+04d}-pitch+00" for yaw in range(-180, 180, 15))
SIZE = (1024, 1536)
HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[3]
POSTPROCESS = HERE / "postprocess_one_canonical_view.py"


def absolute_d_dir(value: str) -> Path:
    path = Path(value)
    if not path.is_absolute() or path.drive.upper() != "D:":
        raise argparse.ArgumentTypeError("must be an absolute D-drive directory")
    return path.resolve()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", type=absolute_d_dir, required=True)
    parser.add_argument("--output-root", type=absolute_d_dir, required=True)
    parser.add_argument(
        "--outfit-guard-root",
        type=Path,
        action="append",
        required=True,
        help="May be repeated; the first root containing the view mask wins.",
    )
    parser.add_argument("--repo", type=Path, default=PROJECT)
    parser.add_argument(
        "--view-id",
        action="append",
        choices=CANONICAL_VIEWS,
        default=[],
        help="Process exactly these canonical views; default is the Smoke3 trio.",
    )
    parser.add_argument(
        "--accepted-view",
        action="append",
        choices=CANONICAL_VIEWS,
        default=[],
        help="May be repeated only after the named view passes the art gate.",
    )
    args = parser.parse_args()
    views = tuple(args.view_id) if args.view_id else SMOKE3_VIEWS
    if len(set(views)) != len(views):
        raise ValueError("duplicate --view-id")
    if args.output_root.exists():
        raise FileExistsError(f"refusing to overwrite staging output: {args.output_root}")
    args.output_root.mkdir(parents=True)

    legacy = args.repo / "assets/pose-atlas/v4-layered"
    processed: list[dict[str, object]] = []
    missing: list[str] = []
    failed: list[dict[str, str]] = []
    for view in views:
        registered_master = args.input_dir / "registered-birefnet-rgba" / f"{view}.png"
        composed_master = args.input_dir / f"{view}_composed-staging.png"
        master = registered_master if registered_master.is_file() else composed_master
        if not master.is_file():
            missing.append(view)
            continue
        with Image.open(master) as image:
            if image.size != SIZE:
                failed.append({"view_id": view, "error": f"invalid canvas {image.size}"})
                continue
            has_alpha = image.mode == "RGBA" and image.getextrema()[3][0] < 255
        registered_alpha = args.input_dir / "registered-birefnet-alpha" / f"{view}.png"
        composed_alpha = args.input_dir / f"{view}.birefnet-alpha.png"
        alpha = registered_alpha if registered_alpha.is_file() else composed_alpha
        if not has_alpha and not alpha.is_file():
            failed.append({"view_id": view, "error": "RGB/opaque input requires BiRefNet alpha sidecar"})
            continue
        guard_roots = tuple(
            root if root.is_absolute() else args.repo / root
            for root in args.outfit_guard_root
        )
        outfit_guard = next(
            (
                root / f"{view}_default_outfit_mask.png"
                for root in guard_roots
                if (root / f"{view}_default_outfit_mask.png").is_file()
            ),
            None,
        )
        if outfit_guard is None:
            checked = ", ".join(str(root) for root in guard_roots)
            failed.append({"view_id": view, "error": f"missing outfit guard in: {checked}"})
            continue

        command = [
            sys.executable, str(POSTPROCESS), "--view-id", view,
            "--master", str(master), "--output-root", str(args.output_root / view),
            "--outfit-guard", str(outfit_guard), "--repo", str(args.repo),
        ]
        if alpha.is_file():
            command.extend(("--birefnet-alpha", str(alpha)))
        if view in args.accepted_view:
            command.append("--accepted")
        for hair_layer in ("hair_back", "hair_left", "hair_right"):
            seed = legacy / f"{view}_{hair_layer}.png"
            if seed.is_file():
                command.extend(("--hair-seed", str(seed)))
        # Do not inject the legacy ornament layer.  It contains hair pixels in
        # the accepted yaw000 fixture and changes the v12 ownership boundary.
        # Ornament ownership is extracted from the accepted master plus its
        # fixed physical-side anchor inside postprocess_one_canonical_view.
        try:
            completed = subprocess.run(command, check=True, text=True, capture_output=True)
            run_dirs = tuple((args.output_root / view).glob(f"postprocess-{view}-*"))
            if len(run_dirs) != 1:
                raise RuntimeError(f"expected one postprocess run, got {len(run_dirs)}")
            result_files = tuple(run_dirs[0].glob("split/batch-*/batch-result.json"))
            if len(result_files) != 1:
                raise RuntimeError(f"expected one batch-result, got {len(result_files)}")
            batch_result = json.loads(result_files[0].read_text(encoding="utf-8"))
            if batch_result.get("views_processed") != 1:
                raise RuntimeError("postprocess did not produce exactly one real view")
            result = batch_result["results"][0]
            required_zero = (
                "ownership_overlap_pixels",
                "core_outfit_overlap_pixels",
                "core_ornament_overlap_pixels",
                "recompose_diff_pixels",
                "recompose_max_channel_error",
            )
            nonzero = {key: result.get(key) for key in required_zero if result.get(key) != 0}
            if nonzero:
                raise RuntimeError(f"ownership/recompose gate failed: {nonzero}")
            core_files = tuple(run_dirs[0].glob("split/batch-*/**/core25/*.png"))
            if len(core_files) != 25:
                raise RuntimeError(f"expected 25 real core layers, got {len(core_files)}")
            view_root = result_files[0].parent / view
            pack_root = view_root / "yunchangge-pack"
            required_outputs = (
                view_root / f"{view}_core25-only.png",
                view_root / f"{view}_core25-plus-pack.png",
                pack_root / f"{view}_default_outfit.png",
                pack_root / f"{view}_ornament.png",
                run_dirs[0] / f"{view}.manifest-fragment.json",
            )
            absent = [str(path) for path in required_outputs if not path.is_file()]
            if absent:
                raise RuntimeError(f"missing separated outputs: {absent}")
            processed.append({
                "view_id": view,
                "accepted": view in args.accepted_view,
                "core_layers": 25,
                "output": str(run_dirs[0]),
                "core": str(required_outputs[0]),
                "outfit": str(required_outputs[2]),
                "ornament": str(required_outputs[3]),
                "fragment": str(required_outputs[4]),
                "ownership_overlap_pixels": 0,
                "recompose_diff_pixels": 0,
            })
            print(completed.stdout, end="")
        except Exception as error:
            failed.append({"view_id": view, "error": str(error)})

    status = {
        "processed": processed,
        "missing": missing,
        "failed": failed,
        "blank_layers_created": 0,
    }
    print(json.dumps(status, ensure_ascii=False))
    if missing or failed:
        return 3
    if len(processed) != len(views):
        return 4
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
