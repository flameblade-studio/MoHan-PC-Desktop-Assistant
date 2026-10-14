"""Render three base-body previews through the shared presentation renderer."""
from __future__ import annotations

lazy import argparse
lazy import hashlib
lazy import json
lazy import os
lazy import sys
lazy from pathlib import Path
lazy from PySide6.QtCore import Qt
lazy from PySide6.QtGui import QPixmap
lazy from PySide6.QtWidgets import QApplication
lazy from application.character_runtime_bootstrap import _activate, activate_product_character_runtime, official_character_pack_limits
lazy from application.service_container import _create_presentation_ports
lazy from application.wardrobe_service import BODY_OUTFIT_ID, WardrobeService
lazy from domain.engine_capabilities import current_engine_capabilities
lazy from infrastructure.character_source_pack import CharacterPackReader
lazy from domain.face_rig import FaceMotionFrame, FacePose, Viseme, MouthShape, ExpressionShape

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
PREVIEW_SCALE = 3


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--character-root", type=Path, required=True)
    parser.add_argument("--body-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--character-id", default="lin-keyun")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    os.environ["MOHAN_DATA_DIR"] = str((args.output / "profile").resolve())
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance() or QApplication([])
    activate_product_character_runtime(ROOT, character_id="mohan")
    engine = current_engine_capabilities()
    source = CharacterPackReader(
        args.character_root, engine_version=engine.version,
        engine_api_version=engine.api_version, engine_features=engine.features,
        body_pack_roots=(args.body_root,), limits=official_character_pack_limits(),
    )
    if source.character_id != args.character_id:
        raise ValueError("Preview source must match the requested character.")
    _activate(source)
    wardrobe = WardrobeService(
        args.output / "profile" / "outfits", official_pack_root=source.official_pack_roots,
    )
    wardrobe.apply(BODY_OUTFIT_ID)
    ports = _create_presentation_ports(source)
    renderer = ports.full_body_renderer_factory()
    motion = FaceMotionFrame(
        FacePose.FRONT, "idle", Viseme.CLOSED, MouthShape(), ExpressionShape(), breath=0.5,
    )
    cases = (("full-front", "yaw+000-pitch+00", False),
             ("full-side", "yaw+090-pitch+00", False),
             ("half-front", "front-crossed", True))
    records = []
    for label, view, halfbody in cases:
        frame = (renderer.render(QPixmap(), motion, None) if halfbody
                 else renderer.render_view(view, motion))
        path = args.output / f"{label}-3x.png"
        scaled = frame.scaled(
            frame.width() * PREVIEW_SCALE, frame.height() * PREVIEW_SCALE,
            Qt.IgnoreAspectRatio, Qt.FastTransformation,
        )
        if frame.isNull() or not scaled.save(str(path), "PNG"):
            raise ValueError(f"Preview output failed: {path}")
        plan = source.appearance.character_layer_views[view].without_clothing()
        records.append({"path": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                        "size": [scaled.width(), scaled.height()],
                        "retained_kinds": sorted({layer.kind for layer in plan.layers})})
    (args.output / "preview.json").write_text(
        json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n",
    )
    print(json.dumps(records, ensure_ascii=False, indent=2))
    app.quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
