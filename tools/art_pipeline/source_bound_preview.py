"""Render a pinned staging manifest through MoHan's production compositor.

Usage: python -m tools.art_pipeline.source_bound_preview --manifest FILE --output DIR
Outputs remain scratch candidates requiring the owner's visual decision.
"""

from __future__ import annotations

lazy import argparse
lazy import json
lazy import os
lazy from pathlib import Path
lazy from threading import Lock
lazy from time import perf_counter

lazy from tools.art_pipeline.source_bound_stage import digest, pinned_file, read_pinned, stage_preview
lazy from tools.art_pipeline.source_bound_reference import normalize_makeup_slot_intensities

STATES = (("rest", 0.0), ("half", 0.5), ("closed", 1.0), ("reopened", 0.0))
_RENDER_LOCK = Lock()


def _makeup_state_payload(manifest: dict) -> dict:
    values = normalize_makeup_slot_intensities(manifest)
    overrides = {slot: value for slot, value in values.items() if value != 1.0}
    payload = {"enabled": True, "intensity": 1.0}
    if overrides:
        payload["slot_intensities"] = overrides
    return payload


def _render_frames(manifest: dict, output: Path) -> tuple[dict, dict]:
    """Use the same pack, overlay, body authority and eye states as the app."""
    from PySide6.QtWidgets import QApplication

    from domain import outfit_pack
    from domain.outfit_pack_makeup import select_builtin_makeup
    from infrastructure.active_outfit_overlay import ActiveOutfitOverlay
    from infrastructure.layered_full_body_assets import (
        LayeredFullBodyManifest, load_layered_full_body_assets,
    )
    from infrastructure.layered_full_body_renderer import LayeredFullBodyRenderer
    from tools.art_pipeline.source_bound_pack_scope import resolve_runtime_members
    application = QApplication.instance() or QApplication([])
    previous_pack_root = outfit_pack.OFFICIAL_PACK_ROOT
    outfit_pack.OFFICIAL_PACK_ROOT = output / "assets/official-packs"
    try:
        store = output / "store"
        outfit_pack.apply_ensemble(store, manifest["pack_id"], manifest["ensemble_id"])
        if manifest.get("makeup"):
            select_builtin_makeup(store, manifest["makeup"])
            (store / "makeup.json").write_text(
                json.dumps(_makeup_state_payload(manifest)) + "\n", encoding="utf-8",
            )
        overlay = ActiveOutfitOverlay(store, output)
        loaded = load_layered_full_body_assets(output / "assets/pose-atlas/v5-base-layered")
        renderer = LayeredFullBodyRenderer(
            LayeredFullBodyManifest({manifest["view_id"]: loaded.view(manifest["view_id"])}),
            overlay, authority_root=output / "assets/pose-atlas/v5-base",
        )
        frames = _save_frames(renderer, overlay, manifest["view_id"], output)
        members = resolve_runtime_members(store, manifest, output)
        if manifest.get("makeup_updates"):
            from tools.art_pipeline.source_bound_makeup import resolve_runtime_makeup_members

            members.update(resolve_runtime_makeup_members(store, manifest, output))
        application.processEvents()
        return frames, members
    finally:
        outfit_pack.OFFICIAL_PACK_ROOT = previous_pack_root


def _save_frames(renderer, overlay, view: str, output: Path) -> dict:
    from tools.audit_yaw000_layer_runtime import _frame

    frames: dict[str, dict] = {}
    for state, blink in STATES:
        target = output / f"{state}.png"
        rendered = renderer.render_view(view, _frame(blink=blink))
        if rendered.isNull() or not rendered.save(str(target)):
            raise RuntimeError(f"Runtime preview failed: {state}")
        count = overlay.layer_count(
            view, eye_state="rest" if state == "reopened" else state,
            suppress_makeup_slots={"eyes"} if blink else (),
        )
        if count <= 0:
            raise RuntimeError(f"Preview lost its appearance layers: {state}")
        frames[state] = {"sha256": digest(target.read_bytes()), "layer_count": count}
    if frames["rest"]["sha256"] != frames["reopened"]["sha256"]:
        raise RuntimeError("Reopened preview differs from rest.")
    return frames


def run_preview(root: Path, manifest: dict, output: Path) -> dict:
    from tools.art_pipeline.source_bound_identity import verify_reference_faces

    started = perf_counter()
    root = root.resolve()
    output = output.resolve()
    stage = stage_preview(root, manifest, output)
    with _RENDER_LOCK:
        frames, members = _render_frames(manifest, output)
    for relative, expected in stage["files"].items():
        if digest((output / relative).read_bytes()) != expected:
            raise RuntimeError(f"Staged input changed during rendering: {relative}")
    for declaration in manifest["files"]:
        read_pinned(root, pinned_file(declaration))
    faces = verify_reference_faces(root, manifest, output)
    report = {
        **stage, "status": "scratch-runtime-preview-awaiting-visual-review",
        "owner_visual_approval": "pending", "frames": frames,
        "composed_face_identity": faces,
        "runtime_selected_members": members,
        "elapsed_seconds": round(perf_counter() - started, 3),
    }
    (output / "receipt.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    args = parser.parse_args()
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    print(json.dumps(run_preview(args.root, manifest, args.output), indent=2))


if __name__ == "__main__":
    main()
