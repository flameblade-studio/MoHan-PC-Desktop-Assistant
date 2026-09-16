"""Wardrobe controls retain state and responsiveness when an installed archive is damaged."""

from __future__ import annotations

lazy import sys
lazy from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

lazy from PySide6.QtWidgets import QApplication
lazy from application.wardrobe_service import BUILTIN_OUTFIT_ID, WardrobeService
lazy from domain import outfit_pack
lazy from test_global_settings_actions import build_dashboard, close_dashboard
lazy from test_outfit_pack import _manifest, _pack, _png


def test_corrupt_package_notice_preserves_selection_and_recovers(tmp_path, monkeypatch):
    QApplication.instance() or QApplication([])
    monkeypatch.setattr(outfit_pack, "OFFICIAL_PACK_ROOT", tmp_path / "official")
    db, dashboard = build_dashboard(tmp_path)
    try:
        store = tmp_path / "outfits"
        manifest, assets = _manifest(_png())
        archive = _pack(tmp_path / "valid.mohan-outfit", manifest, assets)
        outfit_pack.install_outfit_pack(archive, store)
        service = WardrobeService(store)
        dashboard.wardrobe_service = service
        chosen = next(item for item in service.outfits() if not item.built_in)
        service.apply(chosen.outfit_id)
        db.set_setting("active_outfit_id", chosen.outfit_id)
        dashboard._reload_wardrobe_packages()
        count_before = dashboard.wardrobe_packages.count()
        active_before = (store / "active.json").read_bytes()
        corrupt = store / "packages" / "broken.mohan-outfit"
        corrupt.write_bytes(b"broken archive")

        dashboard._reload_wardrobe_packages()
        assert "讀取髮型或頭飾需要處理" in dashboard.wardrobe_status.text()
        assert dashboard.wardrobe_packages.count() == 0
        assert dashboard.wardrobe_makeup_selector.count() == 0
        assert not dashboard.wardrobe_makeup_selector.signalsBlocked()
        dashboard._preview_selected_outfit()
        dashboard._reload_wardrobe_makeup_options()
        assert db.setting("active_outfit_id", BUILTIN_OUTFIT_ID) == chosen.outfit_id
        assert (store / "active.json").read_bytes() == active_before
        assert corrupt.read_bytes() == b"broken archive"

        corrupt.unlink()
        dashboard._reload_wardrobe_packages()
        assert dashboard.wardrobe_packages.count() == count_before
        assert dashboard.wardrobe_makeup_selector.count() > 0
        assert not dashboard.wardrobe_makeup_selector.signalsBlocked()
        assert (store / "active.json").read_bytes() == active_before
    finally:
        close_dashboard(dashboard, db)
