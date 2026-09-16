"""Independent hairstyle and headwear controls for the Wardrobe Pavilion."""
from __future__ import annotations

lazy from functools import partial
lazy from typing import Protocol

lazy from PySide6.QtWidgets import QComboBox, QFrame, QLabel, QPushButton, QVBoxLayout

lazy from application.presentation_ports import PresentationDatabasePort
lazy from application.wardrobe_appearance_service import WardrobeAppearanceService
lazy from application.wardrobe_service import BUILTIN_OUTFIT_ID
lazy from domain.outfit_pack import OutfitPackError
lazy from presentation.flagship_theme import mark_flagship_card

__all__ = ("build_appearance_card", "reload_appearance_controls")


class AppearanceView(Protocol):
    db: PresentationDatabasePort
    ui_language: str
    wardrobe_appearance_selectors: dict[str, QComboBox]
    wardrobe_appearance_buttons: dict[str, QPushButton]
    wardrobe_status: QLabel

    def _t(self, key: str, chinese: str, **values: object) -> str: ...
    def _refresh_wardrobe_preview(self) -> None: ...
    def _record_manual_outfit_selection(self, outfit_id: str) -> None: ...


def _service(view: AppearanceView) -> WardrobeAppearanceService:
    return WardrobeAppearanceService(view.db.path.parent / "outfits")


def build_appearance_card(view: AppearanceView, category: str, title: str) -> QFrame:
    card = QFrame()
    mark_flagship_card(card)
    layout = QVBoxLayout(card)
    layout.setContentsMargins(22, 22, 22, 22)
    layout.setSpacing(20)
    heading = QLabel(title)
    heading.setProperty("mohanRole", "cardTitle")
    layout.addWidget(heading)
    hint = QLabel(view._t("wardrobe_independent_appearance", "髮型與髮飾可獨立搭配；套用後立即更新人物預覽。"))
    hint.setWordWrap(True)
    hint.setProperty("mohanRole", "muted")
    layout.addWidget(hint)
    selector = QComboBox()
    selector.setAccessibleName(title)
    selector.setObjectName(f"wardrobe-{category}-selector")
    layout.addWidget(selector)
    apply_button = QPushButton(view._t("wardrobe_apply_appearance", "套用選擇"))
    apply_button.setProperty("mohanAction", "primary")
    apply_button.setObjectName(f"wardrobe-{category}-apply")
    apply_button.clicked.connect(partial(_apply_selected, view, category))
    layout.addWidget(apply_button)
    layout.addStretch(1)
    view.wardrobe_appearance_selectors[category] = selector
    view.wardrobe_appearance_buttons[category] = apply_button
    return card


def reload_appearance_controls(view: AppearanceView) -> None:
    selectors = getattr(view, "wardrobe_appearance_selectors", {})
    service = _service(view)
    for category, selector in selectors.items():
        try:
            options = service.options(category, view.ui_language)
            active = service.active_id(category)
        except OutfitPackError:
            view.wardrobe_status.setText(view._t("wardrobe_appearance_read_failed", '讀取髮型或頭飾需要處理，請檢查外觀套件；目前選擇持續使用。'))
            view.wardrobe_appearance_buttons[category].setEnabled(False)
            continue
        previous = selector.blockSignals(True)
        selector.clear()
        for option in options:
            title = view._t("wardrobe_headwear_none", "頭飾關閉") if option.option_id == "none" else option.display_name
            selector.addItem(title, option.option_id)
        selector.setCurrentIndex(selector.findData(active))
        selector.blockSignals(previous)
        view.wardrobe_appearance_buttons[category].setEnabled(bool(options))


def _apply_selected(view: AppearanceView, category: str) -> None:
    selected = view.wardrobe_appearance_selectors[category].currentData()
    if selected is None:
        return
    try:
        _service(view).apply(category, str(selected))
    except OutfitPackError:
        view.wardrobe_status.setText(view._t("wardrobe_appearance_apply_failed", '套用髮型或頭飾需要處理；目前外觀持續使用。'))
        return
    view._record_manual_outfit_selection(str(view.db.setting("active_outfit_id", BUILTIN_OUTFIT_ID)))
    view.wardrobe_status.setText(view._t("wardrobe_appearance_applied", "已套用所選髮型或髮飾。"))
    view._refresh_wardrobe_preview()
