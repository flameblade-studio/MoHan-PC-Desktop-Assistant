"""Issue #140, option 3: the body profile moved to generation 2 in one step.

Three modules used to carry their own ``mohan-body-v1`` literal.  This suite
pins them to each other and to ``POSE_ATLAS_GENERATION`` so a future bump is
one edit that either lands everywhere or fails here, and it proves that a
generation-1 outfit pack is rejected at install, at apply and at runtime with
the dedicated, localized message instead of a silent fallback.
"""

from __future__ import annotations

lazy import copy
lazy import json
lazy import os
lazy import shutil
lazy import sys
lazy from pathlib import Path
lazy from tempfile import TemporaryDirectory
lazy from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parents[1]
TESTS = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(TESTS))

lazy import pytest
lazy from PySide6.QtCore import Qt
lazy from PySide6.QtWidgets import QApplication, QFileDialog

lazy from application.wardrobe_service import BUILTIN_OUTFIT_ID, WardrobeService
lazy from domain import outfit_pack, pose_pack
lazy from domain.character_body_profile import MOHAN_BODY_PROFILE, body_profile_reference
lazy from domain.constants import POSE_ATLAS_GENERATION
lazy from domain.outfit_pack import (
    OFFICIAL_BODY_SPEC,
    IncompatibleBodyProfileError,
    OutfitPackError,
    inspect_outfit_pack,
    install_outfit_pack,
    list_installed_outfits,
    list_stale_body_profile_packs,
    official_pose_template,
    remove_outfit_pack,
    resolve_active_selection,
)
lazy from domain.pose_atlas_manifest_builder import PoseAtlasBuildConfig
lazy from presentation.dashboard_wardrobe_status import wardrobe_generation_message
lazy from presentation.ui_localization import ui_text
lazy from test_global_settings_actions import build_dashboard, close_dashboard
lazy from test_outfit_pack import _manifest, _pack, _png

GENERATION_ONE = {"id": "mohan-body-v1", "version": 1}
NOTICE_KEY = "wardrobe_body_profile_outdated"
NOTICE_ZH_TW = "這套服裝是為一代素體製作的，穿在二代素體上會對不準；請用一鍵製衣重新生成"


@pytest.fixture(autouse=True)
def _pending_official_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """These contracts describe a store on its own; the shipped official packs are covered elsewhere."""
    monkeypatch.setattr(outfit_pack, "OFFICIAL_PACK_ROOT", tmp_path / "official")


def _generation_one_pack(root: Path) -> Path:
    manifest, assets = _manifest(_png())
    stale = copy.deepcopy(manifest)
    stale["compatible_body_profile"] = GENERATION_ONE
    return _pack(root / "stale-v1.mohan-outfit", stale, assets)


def _current_pack(root: Path) -> Path:
    manifest, assets = _manifest(_png())
    return _pack(root / "current.mohan-outfit", manifest, assets)


def test_body_profile_generation_is_declared_once() -> None:
    expected_id = f"mohan-body-v{POSE_ATLAS_GENERATION}"
    assert MOHAN_BODY_PROFILE.profile_id == expected_id
    assert MOHAN_BODY_PROFILE.version == POSE_ATLAS_GENERATION
    assert outfit_pack.BODY_PROFILE_ID == MOHAN_BODY_PROFILE.profile_id == pose_pack.BODY_PROFILE["id"]
    assert outfit_pack.BODY_PROFILE_VERSION == MOHAN_BODY_PROFILE.version == pose_pack.BODY_PROFILE["version"]
    assert body_profile_reference() == {"id": expected_id, "version": POSE_ATLAS_GENERATION}
    template = official_pose_template()
    assert (template["body_profile_id"], template["body_profile_version"]) == (expected_id, POSE_ATLAS_GENERATION)
    config = PoseAtlasBuildConfig("pack", "source-proof", "identity-proof")
    assert config.body_profile_id == expected_id
    assert config.body_profile_version_range == (POSE_ATLAS_GENERATION, POSE_ATLAS_GENERATION + 1)
    measurements = MOHAN_BODY_PROFILE.measurements
    assert dict(OFFICIAL_BODY_SPEC) == {
        "adult": True,
        "height_cm": measurements.height_cm,
        "weight_kg": measurements.weight_kg,
        "bust_cm": measurements.bust_cm,
        "underbust_cm": measurements.underbust_cm,
        "waist_cm": measurements.waist_cm,
        "hips_cm": measurements.hips_cm,
    }


def test_generation_one_pack_is_rejected_with_the_dedicated_error() -> None:
    with TemporaryDirectory(ignore_cleanup_errors=True) as temporary:
        root = Path(temporary)
        stale = _generation_one_pack(root)
        with pytest.raises(IncompatibleBodyProfileError) as rejected:
            inspect_outfit_pack(stale)
        assert "mohan-body-v1" in str(rejected.value)
        assert outfit_pack.BODY_PROFILE_ID in str(rejected.value)
        assert issubclass(IncompatibleBodyProfileError, OutfitPackError)
        store = root / "store"
        with pytest.raises(IncompatibleBodyProfileError):
            install_outfit_pack(stale, store)
        assert not (store / "packages").exists()
        # The generic authoring-template branch is no longer merged with the body-profile branch.
        manifest, assets = _manifest(_png())
        manifest["authoring"] = {"template": "mohan-official-poses", "version": 1}
        with pytest.raises(OutfitPackError) as generic:
            inspect_outfit_pack(_pack(root / "authoring.mohan-outfit", manifest, assets))
        assert not isinstance(generic.value, IncompatibleBodyProfileError)


def test_previously_installed_generation_one_pack_is_listed_incompatible_and_never_applied() -> None:
    with TemporaryDirectory(ignore_cleanup_errors=True) as temporary:
        root = Path(temporary)
        store = root / "store"
        install_outfit_pack(_current_pack(root), store)
        packages = store / "packages"
        shutil.copyfile(_generation_one_pack(root), packages / "stale-v1.mohan-outfit")
        assert [pack.pack_id for pack in list_installed_outfits(store)] == ["modern-collection"]
        assert list_stale_body_profile_packs(store) == ("stale-v1",)
        service = WardrobeService(store)
        by_id = {outfit.outfit_id: outfit for outfit in service.outfits()}
        assert by_id["stale-v1"].compatible is False
        assert all(outfit.compatible for key, outfit in by_id.items() if key != "stale-v1")
        with pytest.raises(IncompatibleBodyProfileError):
            service.apply("stale-v1")
        # A pre-bump active.json still pointing at the stale pack is the runtime case.
        (store / "active.json").write_text(
            json.dumps({"garment": {"pack_id": "stale-v1", "item_id": "city-dress", "variant_id": "navy"}}),
            encoding="utf-8",
        )
        with pytest.raises(IncompatibleBodyProfileError):
            resolve_active_selection(store, "garment")
        assert resolve_active_selection(store, "hairstyle").status == "builtin"
        service.apply(BUILTIN_OUTFIT_ID)
        assert resolve_active_selection(store, "garment").status == "builtin"
        assert remove_outfit_pack(store, "stale-v1").pack_id == "stale-v1"
        assert list_stale_body_profile_packs(store) == ()


def test_runtime_notice_uses_the_localized_key() -> None:
    seen: list[tuple[str, str]] = []

    def translate(key: str, fallback: str) -> str:
        seen.append((key, fallback))
        return f"<{key}>"

    assert wardrobe_generation_message("body-profile-outdated", translate) == f"<{NOTICE_KEY}>"
    assert (NOTICE_KEY, NOTICE_ZH_TW) in seen
    for language in ("zh-TW", "zh-CN", "en", "ja-JP"):
        text = ui_text(language, NOTICE_KEY, NOTICE_ZH_TW)
        assert text.strip(), language
    assert ui_text("en", NOTICE_KEY, NOTICE_ZH_TW) != NOTICE_ZH_TW


def test_dashboard_import_and_apply_show_the_body_profile_notice() -> None:
    QApplication.instance() or QApplication([])
    with TemporaryDirectory(ignore_cleanup_errors=True) as temporary:
        root = Path(temporary)
        db, dashboard = build_dashboard(root)
        try:
            store = root / "outfits"
            dashboard.wardrobe_service = WardrobeService(store)
            stale = _generation_one_pack(root)
            with patch.object(QFileDialog, "getOpenFileName", return_value=(str(stale), "")):
                dashboard._import_outfit_package()
            assert dashboard.wardrobe_status.text() == NOTICE_ZH_TW
            assert not (store / "packages").exists()

            (store / "packages").mkdir(parents=True)
            shutil.copyfile(stale, store / "packages" / "stale-v1.mohan-outfit")
            dashboard._reload_wardrobe_packages()
            items = [
                dashboard.wardrobe_packages.item(index)
                for index in range(dashboard.wardrobe_packages.count())
            ]
            stale_item = next(item for item in items if item.data(Qt.UserRole) == "stale-v1")
            assert "不相容" in stale_item.toolTip()
            dashboard.wardrobe_packages.setCurrentItem(stale_item)
            dashboard.wardrobe_status.setText("")
            dashboard._preview_selected_outfit()
            assert dashboard.wardrobe_status.text() == NOTICE_ZH_TW
            assert db.setting("active_outfit_id", BUILTIN_OUTFIT_ID) == BUILTIN_OUTFIT_ID

            dashboard.db.set_setting("active_outfit_id", "stale-v1")
            dashboard.set_outfit_generation_status("body-profile-outdated")
            assert dashboard.wardrobe_status.text() == NOTICE_ZH_TW
            assert db.setting("active_outfit_id", "") == BUILTIN_OUTFIT_ID
        finally:
            close_dashboard(dashboard, db)
