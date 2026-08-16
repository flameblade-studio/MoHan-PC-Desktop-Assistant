from __future__ import annotations

lazy import sys
lazy from pathlib import Path
lazy from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from PySide6.QtGui import QColor, QImage

lazy from tools.compose_body_profile_candidate import compose_candidate


def _image(path: Path, color: str) -> None:
    image = QImage(200, 200, QImage.Format_RGBA8888)
    image.fill(QColor(color))
    assert image.save(str(path), "PNG")


def test_composition_changes_only_the_approved_torso() -> None:
    with TemporaryDirectory() as temporary:
        root = Path(temporary)
        base = root / "base.png"
        donor = root / "donor.png"
        output = root / "output.png"
        _image(base, "#102030")
        _image(donor, "#D0A080")

        audit = compose_candidate(base, donor, output)
        result = QImage(str(output)).convertToFormat(QImage.Format_RGBA8888)

        assert audit["changed_inside_mask"] > 0
        assert audit["changed_outside_mask"] == 0
        assert result.pixelColor(2, 2) == QColor("#102030")
        assert result.pixelColor(100, 130) == QColor("#D0A080")
        assert result.pixelColor(100, 190) == QColor("#102030")
        assert result.pixelColor(2, 2).alpha() == 255


def test_protected_overlay_is_also_clipped_to_the_torso() -> None:
    with TemporaryDirectory() as temporary:
        root = Path(temporary)
        base = root / "base.png"
        donor = root / "donor.png"
        overlay = root / "overlay.png"
        output = root / "output.png"
        _image(base, "#102030")
        _image(donor, "#D0A080")
        _image(overlay, "#224466")

        audit = compose_candidate(base, donor, output, (overlay,))
        result = QImage(str(output)).convertToFormat(QImage.Format_RGBA8888)

        assert audit["changed_outside_mask"] == 0
        assert result.pixelColor(2, 2) == QColor("#102030")
        assert result.pixelColor(100, 130) == QColor("#224466")


if __name__ == "__main__":
    test_composition_changes_only_the_approved_torso()
    test_protected_overlay_is_also_clipped_to_the_torso()
    print("BODY_PROFILE_CANDIDATE_OK")
