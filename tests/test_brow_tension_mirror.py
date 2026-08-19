from __future__ import annotations

lazy import sys
lazy from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from application.multimodal_fusion_hub import (
    FaceMeshFrame,
    FaceMeshPoint,
    MultimodalFusionHub,
)


def _face_frame(inner_brow_distance: float) -> FaceMeshFrame:
    """Build a 478-point frame whose inner brows sit at a controlled distance."""
    # A realistic face spans y from 0.1 (chin) to 0.9 (forehead), giving a
    # face_height of 0.8 so the brow-tension normalization is meaningful.
    points = [FaceMeshPoint(0.5, 0.5, 0.0) for _ in range(478)]
    points[152] = FaceMeshPoint(0.5, 0.1, 0.0)  # chin
    points[10] = FaceMeshPoint(0.5, 0.9, 0.0)   # forehead top
    # Landmarks 105 (left inner brow) and 334 (right inner brow).
    points[105] = FaceMeshPoint(0.5 - inner_brow_distance / 2.0, 0.4, 0.0)
    points[334] = FaceMeshPoint(0.5 + inner_brow_distance / 2.0, 0.4, 0.0)
    return FaceMeshFrame(tuple(points))


def test_brow_tension_rises_when_inner_brows_draw_together() -> None:
    hub = MultimodalFusionHub()
    relaxed = hub._analyze_face(_face_frame(0.20), ())
    furrowed = hub._analyze_face(_face_frame(0.04), ())
    assert furrowed.brow_tension > relaxed.brow_tension
    assert 0.0 <= relaxed.brow_tension <= 1.0
    assert 0.0 <= furrowed.brow_tension <= 1.0


def test_brow_tension_event_emitted_only_when_furrowed() -> None:
    hub = MultimodalFusionHub()
    relaxed = hub._analyze_face(_face_frame(0.20), ())
    furrowed = hub._analyze_face(_face_frame(0.04), ())
    assert "brow-tension-like" not in hub._events(relaxed, _voice(), None)
    assert "brow-tension-like" in hub._events(furrowed, _voice(), None)


def _voice():
    from application.multimodal_fusion_hub import VoiceActivityResult, VoiceActivityState
    return VoiceActivityResult(VoiceActivityState.SILENT, 0.0, 0.0)


def run() -> None:
    test_brow_tension_rises_when_inner_brows_draw_together()
    test_brow_tension_event_emitted_only_when_furrowed()
    print("BROW_TENSION_MIRROR_OK")


if __name__ == "__main__":
    run()
