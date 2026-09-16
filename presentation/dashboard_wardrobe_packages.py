"""Reload the wardrobe package controls while preserving the saved selection."""

from __future__ import annotations

lazy from typing import Protocol
lazy from PySide6.QtCore import Qt
lazy from PySide6.QtWidgets import QLabel, QListWidget, QListWidgetItem
lazy from application.presentation_ports import PresentationDatabasePort
lazy from application.wardrobe_service import BUILTIN_OUTFIT_ID, WardrobeService
lazy from domain.outfit_pack import OutfitPackError


class WardrobePackagesView(Protocol):
    wardrobe_packages: QListWidget
    wardrobe_status: QLabel
    wardrobe_service: WardrobeService
    db: PresentationDatabasePort
    ui_language: str

    def _t(self, key: str, chinese: str, **values: object) -> str: ...

    def _reload_wardrobe_makeup_options(self) -> None: ...


def reload_wardrobe_packages(view: WardrobePackagesView) -> None:
    if not hasattr(view, "wardrobe_packages"):
        return
    view.wardrobe_packages.clear()
    selected_id = WardrobeService.selected_outfit(
        view.db.setting("active_outfit_id", BUILTIN_OUTFIT_ID)
    )
    try:
        outfits = view.wardrobe_service.outfits(view.ui_language)
    except OutfitPackError:
        view.wardrobe_status.setText(view._t(
            "wardrobe_packages_read_failed",
            '讀取外觀套件需要處理，請檢查或重新匯入；目前選擇持續使用。',
        ))
        view._reload_wardrobe_makeup_options()
        return
    for outfit in outfits:
        label = (
            view._t("wardrobe_default_outfit", "內建預設服裝")
            if outfit.built_in else outfit.display_name
        )
        item = QListWidgetItem(label)
        item.setData(Qt.UserRole, outfit.outfit_id)
        item.setToolTip(
            view._t("wardrobe_compatibility_status", "相容狀態") + "："
            + (
                view._t("wardrobe_compatible", "相容") if outfit.compatible
                else view._t("wardrobe_incompatible", '相容性待更新')
            )
        )
        view.wardrobe_packages.addItem(item)
        if outfit.outfit_id == selected_id:
            view.wardrobe_packages.setCurrentItem(item)
    view._reload_wardrobe_makeup_options()
