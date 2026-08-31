#!/usr/bin/env python3
"""Incrementally split only views24 masters whose renderer exit file is zero."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path


VIEWS = (
    "yaw-180-pitch+00", "yaw-165-pitch+00", "yaw-150-pitch+00",
    "yaw-135-pitch+00", "yaw-120-pitch+00", "yaw-105-pitch+00",
    "yaw-090-pitch+00", "yaw-075-pitch+00", "yaw-060-pitch+00",
    "yaw-045-pitch+00", "yaw-030-pitch+00", "yaw-015-pitch+00",
    "yaw+000-pitch+00", "yaw+015-pitch+00", "yaw+030-pitch+00",
    "yaw+045-pitch+00", "yaw+060-pitch+00", "yaw+075-pitch+00",
    "yaw+090-pitch+00", "yaw+105-pitch+00", "yaw+120-pitch+00",
    "yaw+135-pitch+00", "yaw+150-pitch+00", "yaw+165-pitch+00",
)
HERE = Path(__file__).resolve().parent
HOOK = HERE / "postprocess_views24_master_success.py"


def absolute_d_dir(value: str) -> Path:
    path = Path(value)
    if not path.is_absolute() or path.drive.upper() != "D:":
        raise argparse.ArgumentTypeError("must be an absolute D-drive directory")
    return path.resolve()


def existing_d_dir(value: str) -> Path:
    path = absolute_d_dir(value)
    if not path.is_dir():
        raise argparse.ArgumentTypeError("must be an existing D-drive directory")
    return path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def write_marker(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runner-output-dir", type=existing_d_dir, required=True)
    parser.add_argument("--layer-output-root", type=absolute_d_dir, required=True)
    parser.add_argument("--control-bundles-root", type=existing_d_dir, required=True)
    parser.add_argument("--repo", type=existing_d_dir, required=True)
    parser.add_argument(
        "--status-only",
        action="store_true",
        help="List ready/pending inputs without invoking the splitter or writing state.",
    )
    args = parser.parse_args()

    processed: list[str] = []
    already_processed: list[str] = []
    ready: list[str] = []
    pending: list[str] = []
    blocked: dict[str, str] = {}
    marker_root = args.layer_output_root / "queue-state"

    for view_id in VIEWS:
        master = args.runner_output_dir / f"{view_id}_composed-staging.png"
        exit_file = args.runner_output_dir / f"{view_id}_sd-cli.exitcode.txt"
        if not master.is_file() or not exit_file.is_file():
            pending.append(view_id)
            continue
        exit_text = exit_file.read_text(encoding="utf-8").strip()
        if exit_text != "0":
            blocked[view_id] = f"renderer exit code is {exit_text!r}, not 0"
            continue

        if args.status_only:
            ready.append(view_id)
            continue

        master_sha256 = sha256(master)
        marker = marker_root / f"{view_id}.processed.json"
        if marker.is_file():
            previous = json.loads(marker.read_text(encoding="utf-8"))
            if previous.get("master_sha256") != master_sha256:
                blocked[view_id] = "master changed after prior split; refusing overwrite"
            else:
                already_processed.append(view_id)
            continue

        command = [
            sys.executable,
            str(HOOK),
            "--view-id", view_id,
            "--runner-output-dir", str(args.runner_output_dir),
            "--layer-output-root", str(args.layer_output_root),
            "--control-bundles-root", str(args.control_bundles_root),
            "--repo", str(args.repo),
            "--upstream-exit-code-file", str(exit_file),
        ]
        completed = subprocess.run(command, text=True, capture_output=True)
        if completed.stdout:
            print(completed.stdout, end="")
        if completed.stderr:
            print(completed.stderr, file=sys.stderr, end="")
        if completed.returncode != 0:
            blocked[view_id] = f"postprocess hook exit {completed.returncode}"
            continue
        write_marker(
            marker,
            {
                "schema": "mohan.views24_incremental_split_marker.v1",
                "view_id": view_id,
                "master": str(master),
                "master_sha256": master_sha256,
                "renderer_exit_code_file": str(exit_file),
                "accepted": False,
            },
        )
        processed.append(view_id)

    result = {
        "status": "PASS_INCREMENTAL_QUEUE" if not blocked else "BLOCKED_INCREMENTAL_QUEUE",
        "processed": processed,
        "processed_count": len(processed),
        "already_processed": already_processed,
        "ready": ready,
        "ready_count": len(ready),
        "pending": pending,
        "pending_count": len(pending),
        "blocked": blocked,
        "accepted": False,
        "exact_600_created": False,
        "status_only": args.status_only,
    }
    print(json.dumps(result, ensure_ascii=False))
    return 0 if not blocked else 4


if __name__ == "__main__":
    raise SystemExit(main())
