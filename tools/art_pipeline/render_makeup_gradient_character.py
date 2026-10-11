"""Render the makeup-gradient review through a character ZIP cold start."""

from __future__ import annotations

lazy import argparse
lazy import hashlib
lazy import json
lazy import os
lazy import shutil
lazy import sys
lazy import time
lazy import zipfile
lazy from pathlib import Path


MAKEUPS = ("none", "light", "classic", "glamorous")
HALF_EXPRESSIONS = (
    ("idle_front", "front"),
    ("gentle_smile_front", "front"),
    ("surprised_front", "front"),
    ("idle", "cheek"),
)
FULL_VIEW = "yaw+000-pitch+00"
OFFICIAL_PACK = "mohan.makeup.builtin.mohan-outfit"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _activate_environment(repository: Path, archive: Path, runtime: Path) -> None:
    sys.path.insert(0, str(repository))
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    os.environ["LOCALAPPDATA"] = str(runtime / "localappdata")
    os.environ["MOHAN_ACTIVE_CHARACTER"] = "lin-keyun"
    os.environ["MOHAN_DEV_CHARACTER_PACK_ARCHIVE"] = str(archive)


def render_character(  # ruff: ignore[too-many-locals]
    repository: Path,
    archive: Path,
    output: Path,
    candidate: Path | None,
) -> dict[str, object]:
    repository = repository.resolve()
    archive = archive.resolve()
    output = output.resolve()
    candidate = candidate.resolve() if candidate is not None else None
    if output.exists():
        raise ValueError("Refusing to overwrite an existing cold-start render directory.")
    output.mkdir(parents=True)
    frame_root = output / "frames"
    frame_root.mkdir()
    runtime = output / "runtime"
    (runtime / "localappdata").mkdir(parents=True)
    _activate_environment(repository, archive, runtime)

    from PySide6.QtCore import Qt
    from PySide6.QtGui import QPixmap, QPixmapCache
    from PySide6.QtWidgets import QApplication

    from application import presentation_ports as presentation_contracts
    from application import service_container
    from application.character_runtime_bootstrap import activate_product_character_runtime
    from tools import golden_render as golden

    started = time.perf_counter()
    QApplication.instance() or QApplication([])
    QPixmapCache.clear()
    source = activate_product_character_runtime(repository)
    if source.character_id != "lin-keyun":
        raise RuntimeError(f"Unexpected cold-start character: {source.character_id}")

    official = source.assets.asset_root / "assets" / "official-packs" / OFFICIAL_PACK
    embedded_sha256 = _sha256(official)
    if candidate is not None:
        shutil.copyfile(candidate, official)
    active_sha256 = _sha256(official)
    ports = service_container.create_presentation_ports()
    overlay = ports.outfit_overlay_factory()
    if overlay._native_halfbody_hair_is_baked:
        raise RuntimeError("Lin Keyun half-body source ownership was not applied.")

    store = presentation_contracts.default_data_dir() / "outfits"
    entries: list[dict[str, object]] = []
    with golden._network_disabled():
        for makeup in MAKEUPS:
            golden._prepare_store(store, makeup)
            face_renderer = ports.face_renderer_factory()
            for expression, pose in HALF_EXPRESSIONS:
                base = QPixmap(*golden.HALF_SIZE)
                base.fill(Qt.transparent)
                image = face_renderer.render(base, golden._motion(expression, pose), None)
                if image.isNull() or image.size().toTuple() != golden.HALF_SIZE:
                    raise RuntimeError(f"Invalid half-body frame: {expression}/{makeup}")
                name = f"half__{expression}__{makeup}__rest.png"
                measurement = golden._save_pixmap(image, frame_root / name)
                entries.append({"file": f"frames/{name}", **measurement})
            full_renderer = ports.full_body_renderer_factory(overlay)
            image = full_renderer.render_view(
                FULL_VIEW,
                golden._motion("idle_front", "front"),
            )
            if image.isNull() or image.size().toTuple() != golden.FULL_SIZE:
                raise RuntimeError(f"Invalid full-body frame: {makeup}")
            name = f"full__{FULL_VIEW}__{makeup}__rest.png"
            measurement = golden._save_pixmap(image, frame_root / name)
            entries.append({"file": f"frames/{name}", **measurement})

    with zipfile.ZipFile(archive) as package:
        package_manifest = json.loads(package.read("manifest.json"))
    report: dict[str, object] = {
        "schema": "mohan.makeup-gradient-character-render.v1",
        "render_path": "application.service_container.create_presentation_ports",
        "activation": "cold-start development character archive",
        "character_id": source.character_id,
        "archive": {
            "path": archive.as_posix(),
            "sha256": _sha256(archive),
            "package_hash": package_manifest["package_hash"],
        },
        "makeup_pack": {
            "embedded_sha256": embedded_sha256,
            "injected_candidate": candidate.as_posix() if candidate is not None else None,
            "active_sha256": active_sha256,
        },
        "matrix": {
            "makeups": len(MAKEUPS),
            "half_body_cells": len(MAKEUPS) * len(HALF_EXPRESSIONS),
            "full_body_cells": len(MAKEUPS),
            "total_cells": len(entries),
        },
        "elapsed_seconds": round(time.perf_counter() - started, 3),
        "cells": entries,
    }
    manifest_path = output / "render-manifest.json"
    manifest_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repository", type=Path)
    parser.add_argument("archive", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--candidate", type=Path)
    arguments = parser.parse_args(argv)
    report = render_character(
        arguments.repository,
        arguments.archive,
        arguments.output,
        arguments.candidate,
    )
    print(json.dumps({
        "character_id": report["character_id"],
        "makeup_pack": report["makeup_pack"],
        "matrix": report["matrix"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
