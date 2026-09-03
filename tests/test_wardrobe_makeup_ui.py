"""Wardrobe makeup category: shared import button, menu, slider persistence, removal fallback."""

from __future__ import annotations

lazy import json
lazy import os
lazy import sys
lazy from pathlib import Path
lazy from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parents[1]
TESTS = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(TESTS))

lazy import pytest
lazy from PySide6.QtWidgets import QApplication, QFileDialog

lazy from domain.outfit_pack import BUILTIN_MAKEUP_ITEM_ID, BUILTIN_MAKEUP_PACK_ID
lazy from test_global_settings_actions import close_dashboard
lazy from test_outfit_pack_makeup import makeup_pack, official_builtin_pack
lazy from test_wardrobe_ui import build_language_dashboard

FESTIVAL_OPTION = "festival-makeup/festival/classic"
HALF_PERCENT = 50
HALF = 0.5


def _menu_ids(dashboard) -> list[str]:
    selector = dashboard.wardrobe_makeup_selector
    return [str(selector.itemData(index)) for index in range(selector.count())]


def test_makeup_pack_imports_through_the_shared_button_persists_and_falls_back(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    application = QApplication.instance() or QApplication([])
    official_builtin_pack(tmp_path, monkeypatch)
    source = makeup_pack(tmp_path / "festival-makeup.mohan-outfit")
    profile = tmp_path / "profile"
    profile.mkdir()
    store = profile / "outfits"

    db, dashboard = build_language_dashboard(profile, "zh-TW")
    try:
        selector = dashboard.wardrobe_makeup_selector
        assert selector.currentData() == "builtin/classic"
        assert _menu_ids(dashboard) == ["none", "builtin/classic", "builtin/light"]
        with patch.object(QFileDialog, "getOpenFileName", return_value=(str(source), "")):
            dashboard._import_outfit_package()
        application.processEvents()
        assert (store / "packages" / "festival-makeup.mohan-outfit").is_file(), dashboard.wardrobe_status.text()
        assert FESTIVAL_OPTION in _menu_ids(dashboard)
        selector.setCurrentIndex(_menu_ids(dashboard).index(FESTIVAL_OPTION))
        application.processEvents()
        active = json.loads((store / "active.json").read_text(encoding="utf-8"))
        assert active["makeup"] == {"pack_id": "festival-makeup", "item_id": "festival", "variant_id": "classic"}
        assert dashboard.wardrobe_status.text() == "已套用所選妝容。"
        dashboard.wardrobe_makeup_intensity.setValue(HALF_PERCENT)
        application.processEvents()
        assert json.loads((store / "makeup.json").read_text(encoding="utf-8")) == {"intensity": HALF}
        assert dashboard.wardrobe_makeup_intensity_value.text() == f"{HALF_PERCENT}%"
    finally:
        close_dashboard(dashboard, db)

    # Restart: both the selection and the intensity come back from the store.
    db, dashboard = build_language_dashboard(profile, "zh-TW")
    try:
        assert dashboard.wardrobe_makeup_selector.currentData() == FESTIVAL_OPTION
        assert dashboard.wardrobe_makeup_intensity.value() == HALF_PERCENT
        selector = dashboard.wardrobe_makeup_selector
        selector.setCurrentIndex(_menu_ids(dashboard).index("none"))
        application.processEvents()
        assert dashboard.wardrobe_status.text() == "已卸妝，回到素顏。"
        selector.setCurrentIndex(_menu_ids(dashboard).index(FESTIVAL_OPTION))
        application.processEvents()
    finally:
        close_dashboard(dashboard, db)

    # The pack vanishes from disk: the wardrobe falls back to built-in classic and says so once.
    (store / "packages" / "festival-makeup.mohan-outfit").unlink()
    db, dashboard = build_language_dashboard(profile, "zh-TW")
    try:
        assert dashboard.wardrobe_makeup_selector.currentData() == "builtin/classic"
        assert dashboard.wardrobe_status.text() == "所選妝容的套件已不存在，已改回內建原妝。"
        active = json.loads((store / "active.json").read_text(encoding="utf-8"))
        assert active["makeup"] == {"pack_id": "builtin", "item_id": "builtin", "variant_id": "classic"}
        assert FESTIVAL_OPTION not in _menu_ids(dashboard)
        assert BUILTIN_MAKEUP_PACK_ID not in _menu_ids(dashboard)
        assert dashboard.wardrobe_service.makeup_options()[1].selection.item_id == BUILTIN_MAKEUP_ITEM_ID
    finally:
        close_dashboard(dashboard, db)
