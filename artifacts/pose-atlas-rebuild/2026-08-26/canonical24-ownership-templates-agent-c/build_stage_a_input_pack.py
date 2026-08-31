#!/usr/bin/env python3
"""Materialize a fail-closed Stage-A pack from the canonical control queue."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import tempfile
import uuid
from pathlib import Path
from typing import Final

from PIL import Image, ImageChops, ImageFilter, ImageOps


CANVAS: Final = (1024, 1536)
DOMAINS: Final = ("anatomy", "outfit", "hair", "ornament")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def require_hash(path: Path, expected: str) -> None:
    if not path.is_file():
        raise FileNotFoundError(path)
    actual = sha256(path)
    if actual != expected.upper():
        raise ValueError(f"SHA256 mismatch: {path}; expected={expected}; actual={actual}")


def require_image(path: Path, *, mode: str | None = None) -> None:
    with Image.open(path) as image:
        if image.size != CANVAS:
            raise ValueError(f"canvas mismatch: {path}; got={image.size}")
        if mode is not None and image.mode != mode:
            raise ValueError(f"mode mismatch: {path}; got={image.mode}; expected={mode}")


def copy_verified(source: Path, destination: Path, expected: str) -> str:
    require_hash(source, expected)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    require_hash(destination, expected)
    return expected.upper()


def build_softedge(combined_path: Path, destination: Path) -> str:
    with Image.open(combined_path) as image:
        alpha = image.getchannel("A")
    hard_edge = alpha.filter(ImageFilter.FIND_EDGES)
    soft_edge = hard_edge.filter(ImageFilter.GaussianBlur(radius=1.25))
    soft_edge = ImageOps.autocontrast(soft_edge, cutoff=(0.0, 0.2))
    soft_edge.convert("RGB").save(destination)
    require_image(destination, mode="RGB")
    return sha256(destination)


def verify_domain_recomposition(job: dict[str, object]) -> None:
    layers = []
    for domain in DOMAINS:
        path = Path(job["ownership_controls"][domain]["path"])
        require_image(path, mode="RGBA")
        layers.append(Image.open(path).convert("RGBA"))
    try:
        recomposed = Image.new("RGBA", CANVAS, (0, 0, 0, 0))
        for layer in layers:
            recomposed = Image.alpha_composite(recomposed, layer)
        with Image.open(job["combined_control"]["path"]) as combined:
            difference = ImageChops.difference(recomposed, combined.convert("RGBA"))
            if difference.getbbox() is not None:
                raise ValueError(f"ownership recomposition differs: {job['view_id']}")
    finally:
        for layer in layers:
            layer.close()


def source_render_result(lineage: dict[str, object]) -> Path:
    semantic_path = Path(lineage["inputs"]["semantic_rgba"]["path"])
    result_path = semantic_path.parent / "render-result.json"
    if not result_path.is_file():
        raise FileNotFoundError(result_path)
    return result_path


def materialize_view(
    job: dict[str, object], staging_root: Path, final_root: Path
) -> dict[str, object]:
    identity = str(job["view_id"])
    verify_domain_recomposition(job)
    lineage_path = Path(job["lineage"]["path"])
    require_hash(lineage_path, job["lineage"]["sha256"])
    lineage = json.loads(lineage_path.read_text(encoding="utf-8"))
    render_result_path = source_render_result(lineage)
    render_result = json.loads(render_result_path.read_text(encoding="utf-8"))
    if render_result.get("view_id") != identity:
        raise ValueError(f"3D render view mismatch: {render_result_path}")
    if render_result.get("mirror") is not False:
        raise ValueError(f"mirrored 3D source is forbidden: {render_result_path}")
    visibility = render_result.get("visibility", {})
    if visibility.get("backface_culling") is not True:
        raise ValueError(f"backface culling missing: {render_result_path}")
    if visibility.get("per_pixel_z_buffer") is not True:
        raise ValueError(f"z-buffer missing: {render_result_path}")

    destination = staging_root / identity
    recorded_destination = final_root / identity
    destination.mkdir(parents=True)
    controls: dict[str, dict[str, str]] = {}
    for domain in DOMAINS:
        source_record = job["ownership_controls"][domain]
        source = Path(source_record["path"])
        target = destination / f"{identity}_{domain}-control-rgba.png"
        controls[domain] = {
            "path": str((recorded_destination / target.name).resolve()),
            "sha256": copy_verified(source, target, source_record["sha256"]),
        }
        require_image(target, mode="RGBA")

    combined_record = job["combined_control"]
    combined_source = Path(combined_record["path"])
    combined_target = destination / f"{identity}_combined-control-rgba.png"
    copy_verified(combined_source, combined_target, combined_record["sha256"])
    require_image(combined_target, mode="RGBA")

    geometry: dict[str, dict[str, str]] = {}
    for key, output_key, suffix in (
        ("depth", "depth", "depth.png"),
        ("normal", "normal", "normal.png"),
        ("part_id", "part-id", "part-id.png"),
    ):
        source_record = render_result["outputs"][output_key]
        source = Path(source_record["path"])
        target = destination / f"{identity}_{suffix}"
        geometry[key] = {
            "path": str((recorded_destination / target.name).resolve()),
            "sha256": copy_verified(source, target, source_record["sha256"]),
        }
        require_image(target)

    jaw_record = render_result["sources"]["jaw13_candidates"]
    jaw_source = Path(jaw_record["path"])
    jaw_target = destination / f"{identity}_jaw13-mesh-candidates.json"
    geometry["jaw13"] = {
        "path": str((recorded_destination / jaw_target.name).resolve()),
        "sha256": copy_verified(jaw_source, jaw_target, jaw_record["sha256"]),
    }

    softedge_target = destination / f"{identity}_softedge.png"
    geometry["softedge"] = {
        "path": str((recorded_destination / softedge_target.name).resolve()),
        "sha256": build_softedge(combined_target, softedge_target),
    }
    return {
        "view_id": identity,
        "formal": False,
        "accepted": False,
        "combined_control": {
            "path": str((recorded_destination / combined_target.name).resolve()),
            "sha256": combined_record["sha256"].upper(),
        },
        "ownership_controls": controls,
        "geometry_controls": geometry,
        "inference_args": [
            "--view-id",
            identity,
            "--control-rgba",
            str(combined_target.resolve()),
            "--depth",
            geometry["depth"]["path"],
            "--normal",
            geometry["normal"]["path"],
            "--softedge",
            geometry["softedge"]["path"],
            "--part-id",
            geometry["part_id"]["path"],
            "--jaw13",
            geometry["jaw13"]["path"],
        ],
    }


def atomic_write_json(path: Path, payload: dict[str, object]) -> None:
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
    parser.add_argument("--queue", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    arguments = parser.parse_args()

    queue_path = arguments.queue.resolve()
    queue = json.loads(queue_path.read_text(encoding="utf-8"))
    jobs = queue.get("jobs", [])
    if queue.get("job_count") != 24 or len(jobs) != 24:
        raise ValueError("input queue must contain exactly 24 jobs")

    final_root = arguments.output_root.resolve()
    if final_root.exists():
        raise FileExistsError(f"refusing to overwrite existing pack: {final_root}")
    staging_root = final_root.parent / f".{final_root.name}.staging-{uuid.uuid4().hex}"
    staging_root.mkdir(parents=True)
    try:
        output_jobs = [
            materialize_view(job, staging_root, final_root) for job in jobs
        ]
        output_queue = {
            "schema": "mohan.stage-a-control-pack/v1",
            "formal": False,
            "accepted": False,
            "canvas": [*CANVAS],
            "job_count": len(output_jobs),
            "source_queue": {
                "path": str(queue_path),
                "sha256": sha256(queue_path),
            },
            "jobs": output_jobs,
        }
        atomic_write_json(staging_root / "stage-a-inference-queue.json", output_queue)
        os.replace(staging_root, final_root)
    except BaseException:
        shutil.rmtree(staging_root, ignore_errors=True)
        raise

    print(
        json.dumps(
            {
                "output_root": str(final_root),
                "queue": str(final_root / "stage-a-inference-queue.json"),
                "job_count": 24,
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
