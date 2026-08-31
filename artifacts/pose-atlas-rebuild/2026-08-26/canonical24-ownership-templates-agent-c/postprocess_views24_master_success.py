#!/usr/bin/env python3
"""Fail-closed success hook from one views24 master to the 25-layer splitter."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

from PIL import Image


CANVAS = (1024, 1536)
BODY_CENTER = (512, 1292)
HERE = Path(__file__).resolve().parent
CONSUMER = HERE / "consume_flux2_klein_master.py"


def absolute_d_dir(value: str) -> Path:
    path = Path(value)
    if not path.is_absolute() or path.drive.upper() != "D:":
        raise argparse.ArgumentTypeError("must be an absolute D-drive directory")
    return path.resolve()


def absolute_file(value: str) -> Path:
    path = Path(value)
    if not path.is_absolute() or not path.is_file():
        raise argparse.ArgumentTypeError("must be an existing absolute file")
    return path.resolve()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def validate_control_bundle(control_root: Path, view_id: str) -> tuple[Path, Path]:
    bundle = control_root / view_id
    manifest_path = bundle / "control-bundle.json"
    anchor_path = bundle / f"{view_id}_registration-anchor.json"
    if not manifest_path.is_file() or not anchor_path.is_file():
        raise FileNotFoundError(f"missing 3D bundle manifest/anchor for {view_id}")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    anchor = json.loads(anchor_path.read_text(encoding="utf-8"))
    if manifest.get("formal_view_id") != view_id:
        raise ValueError("3D bundle formal_view_id does not match master view_id")
    if anchor.get("view_id") != view_id:
        raise ValueError("3D registration anchor view_id does not match master view_id")
    if tuple(anchor.get("canvas", ())) != CANVAS:
        raise ValueError("3D registration anchor canvas is not 1024x1536")
    if tuple(anchor.get("body_center", ())) != BODY_CENTER:
        raise ValueError("3D registration anchor body_center is not [512,1292]")
    if anchor.get("offset") != [0, 0] or anchor.get("full_canvas_registered") is not True:
        raise ValueError("3D registration anchor is not full-canvas offset0")
    if bool(anchor.get("mirror")) != bool(manifest.get("mirror")):
        raise ValueError("3D bundle and registration anchor mirror state disagree")

    files = manifest.get("files")
    if not isinstance(files, dict):
        raise ValueError("3D bundle files table missing")
    for key in ("depth", "normal", "silhouette", "part_id", "registration_anchor"):
        record = files.get(key)
        if not isinstance(record, dict):
            raise ValueError(f"3D bundle required control missing: {key}")
        physical = Path(record.get("path", ""))
        if not physical.is_file() or physical.parent.resolve() != bundle.resolve():
            raise ValueError(f"3D bundle control is absent or outside view bundle: {key}")
        if key != "registration_anchor" and tuple(record.get("size", ())) != CANVAS:
            raise ValueError(f"3D bundle control has wrong canvas: {key}")
    return manifest_path, anchor_path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--view-id", required=True)
    parser.add_argument("--runner-output-dir", type=absolute_d_dir, required=True)
    parser.add_argument("--layer-output-root", type=absolute_d_dir, required=True)
    parser.add_argument("--control-bundles-root", type=absolute_d_dir, required=True)
    parser.add_argument("--repo", type=absolute_d_dir, required=True)
    parser.add_argument("--upstream-exit-code-file", type=absolute_file, required=True)
    parser.add_argument("--birefnet-alpha", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    exit_code_text = args.upstream_exit_code_file.read_text(encoding="utf-8").strip()
    if exit_code_text != "0":
        raise RuntimeError(
            f"views24 upstream exit-code file is not exactly 0: {exit_code_text!r}"
        )

    bundle_manifest, registration_anchor = validate_control_bundle(
        args.control_bundles_root, args.view_id
    )

    master = args.runner_output_dir / f"{args.view_id}_composed-staging.png"
    if not master.is_file():
        raise FileNotFoundError(master)
    with Image.open(master) as image:
        if image.size != CANVAS or image.mode != "RGBA":
            raise ValueError(
                f"master must be RGBA 1024x1536, got {image.mode} {image.size}"
            )
        if image.getextrema()[3][0] == 255 and args.birefnet_alpha is None:
            raise ValueError("opaque master requires --birefnet-alpha")
    master_sha256 = sha256(master)

    print(
        json.dumps(
            {
                "status": "HOOK_INPUT_VERIFIED",
                "view_id": args.view_id,
                "master": str(master),
                "master_sha256": master_sha256,
                "upstream_exit_code_file": str(args.upstream_exit_code_file),
                "upstream_exit_code": 0,
                "accepted": False,
            },
            ensure_ascii=False,
        )
    )

    command = [
        sys.executable,
        str(CONSUMER),
        "--view-id",
        args.view_id,
        "--master",
        str(master),
        "--output-root",
        str(args.layer_output_root),
        "--control-bundles-root",
        str(args.control_bundles_root),
        "--repo",
        str(args.repo),
    ]
    if args.birefnet_alpha is not None:
        alpha = args.birefnet_alpha.resolve()
        if not alpha.is_file():
            raise FileNotFoundError(alpha)
        command.extend(("--birefnet-alpha", str(alpha)))

    # Intentionally no --accepted flag: generated masters remain owner-review staging.
    if args.dry_run:
        print(
            json.dumps(
                {
                    "status": "DRY_RUN_READY",
                    "view_id": args.view_id,
                    "master": str(master),
                    "master_sha256": master_sha256,
                    "accepted": False,
                    "control_bundle": str(bundle_manifest),
                    "registration_anchor": str(registration_anchor),
                    "body_center": list(BODY_CENTER),
                    "consumer_command": command,
                },
                ensure_ascii=False,
            )
        )
        return 0

    completed = subprocess.run(command, text=True, capture_output=True)
    if completed.stdout:
        print(completed.stdout, end="")
    if completed.stderr:
        print(completed.stderr, file=sys.stderr, end="")
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
