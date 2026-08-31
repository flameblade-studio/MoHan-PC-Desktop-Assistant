#!/usr/bin/env python3
"""Build a fail-closed 24-view clean-control queue for the image generator."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Final

from PIL import Image


CANVAS: Final = (1024, 1536)
VIEW_YAWS: Final = tuple(range(-180, 180, 15))
DOMAINS: Final = ("anatomy", "outfit", "hair", "ornament")


def view_id(yaw: int) -> str:
    return f"yaw{yaw:+04d}-pitch+00"


def selected_directory(yaw: int) -> str:
    if yaw == 45:
        return "yaw045-clean-semantic-hanfu-agent-c-v2"
    if yaw <= -105:
        return f"yaw{yaw:04d}-clean-semantic-hanfu-agent-c-v3"
    signless = f"yaw{yaw:03d}" if yaw >= 0 else f"yaw{yaw:04d}"
    return f"{signless}-clean-semantic-hanfu-agent-c-v1"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def validate_rgba(path: Path, expected_sha: str) -> None:
    if not path.is_file():
        raise FileNotFoundError(path)
    if sha256(path) != expected_sha.upper():
        raise ValueError(f"SHA256 mismatch: {path}")
    with Image.open(path) as image:
        if image.mode != "RGBA" or image.size != CANVAS:
            raise ValueError(
                f"Expected RGBA {CANVAS[0]}x{CANVAS[1]}: {path}; "
                f"got {image.mode} {image.size}"
            )


def build_queue(source_root: Path) -> dict[str, object]:
    jobs: list[dict[str, object]] = []
    for yaw in VIEW_YAWS:
        identity = view_id(yaw)
        directory = source_root / selected_directory(yaw)
        lineage_path = directory / f"{identity}_clean-semantic-hanfu-control.json"
        if not lineage_path.is_file():
            raise FileNotFoundError(lineage_path)
        lineage = json.loads(lineage_path.read_text(encoding="utf-8"))
        if lineage.get("view_id") != identity:
            raise ValueError(f"view_id mismatch: {lineage_path}")
        if lineage.get("canvas") != [*CANVAS]:
            raise ValueError(f"canvas mismatch: {lineage_path}")
        if lineage.get("ownership_overlap_pixels") != 0:
            raise ValueError(f"ownership overlap is nonzero: {lineage_path}")
        if lineage.get("source_rgb_texture_projected") is not False:
            raise ValueError(f"source RGB projection is forbidden: {lineage_path}")
        if lineage.get("formal") is not False or lineage.get("accepted") is not False:
            raise ValueError(f"control must remain non-formal/unaccepted: {lineage_path}")

        controls: dict[str, dict[str, str]] = {}
        for domain in DOMAINS:
            record = lineage["outputs"][domain]
            path = Path(record["path"]).resolve()
            validate_rgba(path, record["sha256"])
            controls[domain] = {
                "path": str(path),
                "sha256": record["sha256"].upper(),
            }

        combined = lineage["combined"]
        combined_path = Path(combined["path"]).resolve()
        validate_rgba(combined_path, combined["sha256"])
        jobs.append(
            {
                "view_id": identity,
                "yaw_degrees": yaw,
                "formal": False,
                "accepted": False,
                "combined_control": {
                    "path": str(combined_path),
                    "sha256": combined["sha256"].upper(),
                },
                "ownership_controls": controls,
                "lineage": {
                    "path": str(lineage_path.resolve()),
                    "sha256": sha256(lineage_path),
                },
            }
        )

    if len(jobs) != 24 or len({job["view_id"] for job in jobs}) != 24:
        raise ValueError("canonical queue must contain exactly 24 unique views")
    return {
        "schema": "mohan.clean-semantic-control-queue/v1",
        "formal": False,
        "accepted": False,
        "canvas": [*CANVAS],
        "job_count": len(jobs),
        "jobs": jobs,
    }


def atomic_write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent, prefix=f".{path.name}.", suffix=".tmp"
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(payload, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_name, path)
    except BaseException:
        Path(temporary_name).unlink(missing_ok=True)
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    arguments = parser.parse_args()
    queue = build_queue(arguments.source_root.resolve())
    atomic_write_json(arguments.output.resolve(), queue)
    print(json.dumps({"output": str(arguments.output.resolve()), "job_count": 24}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
