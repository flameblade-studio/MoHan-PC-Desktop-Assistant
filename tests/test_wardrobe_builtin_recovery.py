from __future__ import annotations

lazy import json
lazy import os
lazy import sys
lazy from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

lazy from PySide6.QtWidgets import QApplication
lazy from application.wardrobe_service import (
    BUILTIN_OUTFIT_FALLBACK_NAME,
    BUILTIN_OUTFIT_ID,
    WardrobeService,
)
lazy from domain.outfit_pack import SELECTION_CATEGORIES
lazy from test_global_settings_actions import build_dashboard, close_dashboard
lazy from test_outfit_pack import _manifest, _pack, _png, pending_official_root


def _install_valid_pack(root: Path, store: Path) -> WardrobeService:
    manifest, assets = _manifest(_png())
    archive = _pack(root / "modern.mohan-outfit", manifest, assets)
    service = WardrobeService(store)
    service.install(archive)
    return service


def _write_corrupt_archive(store: Path) -> tuple[Path, bytes]:
    archive = store / "packages" / "broken.mohan-outfit"
    contents = b"broken archive"
    archive.write_bytes(contents)
    return archive, contents


def _assert_builtin_state(store: Path) -> None:
    state = json.loads((store / "active.json").read_text(encoding="utf-8"))
    assert all(
        state[category]
        == {"pack_id": "builtin", "item_id": "builtin", "variant_id": "builtin"}
        for category in SELECTION_CATEGORIES
    )


def test_builtin_recovery_returns_fallback_after_corrupt_archive(tmp_path: Path) -> None:
    with pending_official_root(tmp_path):
        store = tmp_path / "store"
        service = _install_valid_pack(tmp_path, store)
        selected = next(item for item in service.outfits() if not item.built_in)
        assert service.apply(selected.outfit_id).outfit_id == selected.outfit_id
        corrupt, contents = _write_corrupt_archive(store)

        restored = service.apply(BUILTIN_OUTFIT_ID)

        assert (restored.outfit_id, restored.display_name, restored.built_in) == (
            BUILTIN_OUTFIT_ID,
            BUILTIN_OUTFIT_FALLBACK_NAME,
            True,
        )
        assert restored.ensemble is None
        _assert_builtin_state(store)
        assert corrupt.read_bytes() == contents


def test_dashboard_builtin_recovery_syncs_db_and_reports_read_error(
    tmp_path: Path,
) -> None:
    QApplication.instance() or QApplication([])
    with pending_official_root(tmp_path):
        db, dashboard = build_dashboard(tmp_path)
        try:
            store = tmp_path / "outfits"
            service = _install_valid_pack(tmp_path, store)
            dashboard.wardrobe_service = service
            selected = next(item for item in service.outfits() if not item.built_in)
            service.apply(selected.outfit_id)
            db.set_setting("active_outfit_id", selected.outfit_id)
            corrupt, contents = _write_corrupt_archive(store)

            dashboard._restore_builtin_outfit()

            assert db.setting("active_outfit_id", "") == BUILTIN_OUTFIT_ID
            assert db.setting("wardrobe_reveal_pending_outfit_id", "") == ""
            _assert_builtin_state(store)
            assert "讀取髮型或頭飾需要處理" in dashboard.wardrobe_status.text()
            assert corrupt.read_bytes() == contents
        finally:
            close_dashboard(dashboard, db)
