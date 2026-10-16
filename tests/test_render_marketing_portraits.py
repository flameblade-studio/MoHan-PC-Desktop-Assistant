"""Marketing portraits retain the approved product pixel contract."""
from __future__ import annotations

lazy import json
lazy from pathlib import Path

lazy import pytest
lazy from PySide6.QtWidgets import QApplication

lazy from application.character_runtime_bootstrap import activate_product_character_runtime
lazy from infrastructure.active_outfit_overlay import ActiveOutfitOverlay
lazy from tools.golden_render import pixel_sha256
lazy from tools.render_marketing_portraits import (
    portrait_motion,
    DEFAULT_EXPRESSIONS, ROOT, portrait_renderer, prepare_marketing_store, render_portrait,
)


SAVED_PORTRAIT_MEAN_DIFFERENCE_LIMIT = 0.002


@pytest.mark.parametrize("expression", DEFAULT_EXPRESSIONS)
def test_marketing_portrait_matches_approved_classic_rest(
    tmp_path: Path, expression: str,
) -> None:
    activate_product_character_runtime(ROOT)
    QApplication.instance() or QApplication([])
    store = tmp_path / "store"
    prepare_marketing_store(store)
    overlay = ActiveOutfitOverlay(store, ROOT)
    image = render_portrait(
        overlay, expression, renderer=portrait_renderer(overlay), size=(465, 465),
    )
    manifest = json.loads((ROOT / "tests/golden/golden-manifest.json").read_text(encoding="utf-8"))
    cell = next(
        cell for cell in manifest["cells"]
        if cell["id"] == f"half__{expression}__classic__rest"
    )
    assert image.size().toTuple() == (465, 465)
    assert pixel_sha256(image) == cell["pixel_sha256"]


@pytest.mark.parametrize("expression", DEFAULT_EXPRESSIONS)
def test_saved_portrait_resizes_to_product_golden(tmp_path: Path, expression: str) -> None:
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QImage
    import numpy as np
    from tools.golden_render import _rgba_bytes
    from tools.render_marketing_portraits import render_all

    render_all((expression,), tmp_path / "portraits")
    image = QImage(str(tmp_path / "portraits" / f"{expression}.png")).scaled(
        465, 465, Qt.IgnoreAspectRatio, Qt.SmoothTransformation,
    )
    store = tmp_path / "store"
    prepare_marketing_store(store)
    reference = render_portrait(
        ActiveOutfitOverlay(store, ROOT), expression, size=(465, 465),
    )
    actual = np.frombuffer(_rgba_bytes(image), dtype=np.uint8).astype(int)
    expected = np.frombuffer(_rgba_bytes(reference), dtype=np.uint8).astype(int)
    difference = np.abs(actual - expected)
    # PNG decoding and Qt premultiplied-alpha resizing round edge channels.
    assert difference.max() <= 1
    assert difference.mean() < SAVED_PORTRAIT_MEAN_DIFFERENCE_LIMIT


@pytest.mark.parametrize(
    ("expression", "expected"),
    (
        ("attentive_front", ("attentive_front", None, "rest")),
        ("attentive_front_speech_mid", ("attentive_front", "attentive_front_speech_mid", "rest")),
        ("attentive_front_speech_open", ("attentive_front", "attentive_front_speech_open", "rest")),
        ("attentive_front_speech_round", ("attentive_front", "attentive_front_speech_round", "rest")),
        ("blink_front", ("idle_front", None, "closed")),
    ),
)
def test_portrait_motion_keeps_speech_and_blink_frames(
    expression: str, expected: tuple[str, str | None, str],
) -> None:
    assert portrait_motion(expression) == expected


def test_portrait_motion_rejects_unknown_speech_frames() -> None:
    with pytest.raises(ValueError):
        portrait_motion("attentive_front_speech_whisper")
