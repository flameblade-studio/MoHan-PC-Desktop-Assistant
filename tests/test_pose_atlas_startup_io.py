"""The existing half-body window stays usable while metadata requires attention."""

from __future__ import annotations

lazy import logging
lazy from pathlib import Path

lazy import pytest
lazy from PySide6.QtWidgets import QApplication

lazy from domain.safe_error import SafeDiagnostic, SafeError, SafeErrorType
lazy from presentation.companion_window import CompanionWindow
lazy from presentation.pose_atlas_assets import PoseAtlasAssets


@pytest.mark.parametrize(
    ("denied", "expected"),
    [
        (False, SafeError(SafeErrorType.NOT_FOUND_ERROR, SafeDiagnostic.RESOURCE_NOT_FOUND)),
        (True, SafeError(SafeErrorType.AUTHORIZATION_ERROR, SafeDiagnostic.ACCESS_DENIED)),
    ],
    ids=["missing-metadata", "unreadable-metadata"],
)
def test_metadata_io_failure_preserves_halfbody_and_sanitizes_diagnostic(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    denied: bool,
    expected: SafeError,
) -> None:
    monkeypatch.setenv("MOHAN_DATA_DIR", str(tmp_path / "mohan-data"))
    private_metadata = tmp_path / "private-atlas" / "BUILD-METADATA.json"

    def unavailable_metadata(_self: PoseAtlasAssets) -> dict:
        if denied:
            raise PermissionError(13, "access denied", str(private_metadata))
        # Exercise a dedicated absent-file fixture while preserving the formal asset pack.
        private_metadata.read_text(encoding="utf-8")
        raise AssertionError('metadata loading must report the absent source')

    monkeypatch.setattr(PoseAtlasAssets, "_load_metadata", unavailable_metadata)
    application = QApplication.instance() or QApplication([])
    window = None
    with caplog.at_level(logging.WARNING, logger="presentation.companion_core"):
        try:
            window = CompanionWindow(
                startup_speech=False,
                defer_visual_startup=True,
                adaptive_character_enabled=True,
            )
            assert window._adaptive_character_enabled is False
            assert window._adaptive_character_composition is None
            assert window._performance_app_bridge is None
            assert window._adaptive_character_startup_error == expected
            pixmap = window.character.pixmap()
            assert pixmap is not None and not pixmap.isNull()
        finally:
            if window is not None:
                window.close()
            application.processEvents()

    records = [
        record for record in caplog.records
        if record.name == "presentation.companion_core"
        and "adaptive_character_startup_failed" in record.getMessage()
    ]
    assert len(records) == 1
    assert records[0].getMessage() == f"adaptive_character_startup_failed {expected}"
    assert records[0].exc_info is None
    assert str(tmp_path) not in records[0].getMessage()
