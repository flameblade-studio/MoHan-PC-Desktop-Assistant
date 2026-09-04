from __future__ import annotations

"""Makeup category card of the Wardrobe Pavilion: item/variant menu plus the intensity slider."""

lazy from PySide6.QtCore import Qt
lazy from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QSlider,
    QVBoxLayout,
    QWidget,
)

lazy from domain.outfit_pack import IncompatibleBodyProfileError, OutfitPackError
lazy from presentation.flagship_theme import mark_flagship_card

__all__ = ("DashboardWardrobeMakeupMixin",)

INTENSITY_PERCENT = 100
INTENSITY_SINGLE_STEP = 5
INTENSITY_PAGE_STEP = 10
BARE_OPTION = "none"
CLASSIC_OPTION = "builtin/classic"
LIGHT_OPTION = "builtin/light"


class DashboardWardrobeMakeupMixin:
    """Makeup rides the same pack pipeline as garments; only its menu and slider are new UI."""

    def _wardrobe_makeup_card(self) -> QFrame:
        card = QFrame()
        mark_flagship_card(card)
        layout = QVBoxLayout(card)
        title = QLabel(self._t("wardrobe_makeup_title", "妝容"))
        title.setProperty("mohanRole", "cardTitle")
        layout.addWidget(title)
        self.wardrobe_makeup_selector = QComboBox()
        self.wardrobe_makeup_selector.setAccessibleName(
            self._t("wardrobe_makeup_item", "妝容選擇")
        )
        self.wardrobe_makeup_intensity = QSlider(Qt.Horizontal)
        self.wardrobe_makeup_intensity.setRange(0, INTENSITY_PERCENT)
        self.wardrobe_makeup_intensity.setSingleStep(INTENSITY_SINGLE_STEP)
        self.wardrobe_makeup_intensity.setPageStep(INTENSITY_PAGE_STEP)
        self.wardrobe_makeup_intensity.setAccessibleName(
            self._t("wardrobe_makeup_intensity", "妝感濃淡")
        )
        self.wardrobe_makeup_intensity_value = QLabel(f"{INTENSITY_PERCENT}%")
        self.wardrobe_makeup_intensity_value.setProperty("mohanRole", "muted")
        slider_row = QWidget()
        slider_layout = QHBoxLayout(slider_row)
        slider_layout.setContentsMargins(0, 0, 0, 0)
        slider_layout.addWidget(self.wardrobe_makeup_intensity, 1)
        slider_layout.addWidget(self.wardrobe_makeup_intensity_value)
        form = QFormLayout()
        form.addRow(
            self._t("wardrobe_makeup_item", "妝容選擇"),
            self.wardrobe_makeup_selector,
        )
        form.addRow(
            self._t("wardrobe_makeup_intensity", "妝感濃淡"),
            slider_row,
        )
        layout.addLayout(form)
        hint = QLabel(
            self._t(
                "wardrobe_makeup_hint",
                "素體為素顏；妝容與衣裝、髮型、頭飾一樣是可開關的圖層，新妝容請用「匯入服裝套件」加入。",
            )
        )
        hint.setWordWrap(True)
        hint.setProperty("mohanRole", "muted")
        layout.addWidget(hint)
        layout.addStretch(1)
        self._reload_wardrobe_makeup_options()
        self.wardrobe_makeup_selector.currentIndexChanged.connect(
            self._wardrobe_makeup_selected
        )
        self.wardrobe_makeup_intensity.valueChanged.connect(
            self._wardrobe_makeup_intensity_changed
        )
        return card

    def _makeup_option_label(self, option) -> str:
        if option.option_id == BARE_OPTION:
            return self._t("wardrobe_makeup_none", "素顏（不上妝）")
        if option.option_id == CLASSIC_OPTION:
            label = self._t("wardrobe_makeup_variant_classic", "原妝")
        elif option.option_id == LIGHT_OPTION:
            label = self._t("wardrobe_makeup_variant_light", "淡雅")
        else:
            return option.display_name
        if not option.available:
            label += "（" + self._t("wardrobe_makeup_assets_pending", "內建妝容素材待補") + "）"
        return label

    def _wardrobe_makeup_read_warning(self, message: str) -> None:
        self.wardrobe_status.setText(
            self._t("wardrobe_makeup_read_failed", message)
        )

    def _reload_wardrobe_makeup_options(self) -> None:
        selector = getattr(self, "wardrobe_makeup_selector", None)
        if selector is None:
            return
        try:
            state = self.wardrobe_service.active_makeup()
        except IncompatibleBodyProfileError:
            state = None
            self.wardrobe_status.setText(
                self._t(
                    "wardrobe_body_profile_outdated",
                    "這套服裝是為一代素體製作的，穿在二代素體上會對不準；請用一鍵製衣重新生成",
                )
            )
        except OutfitPackError:
            state = None
        selector.blockSignals(True)
        selector.clear()
        for option in self.wardrobe_service.makeup_options(self.ui_language):
            selector.addItem(self._makeup_option_label(option), option.option_id)
        active_id = state.option_id if state is not None else BARE_OPTION
        index = selector.findData(active_id)
        selector.setCurrentIndex(index if index >= 0 else 0)
        selector.blockSignals(False)
        if state is not None and state.fallback:
            # Same pattern as a stale pack: fall back to the built-in default, tell the user once.
            self.wardrobe_service.apply_makeup(state.option_id)
            self.wardrobe_status.setText(
                self._t(
                    "wardrobe_makeup_pack_missing",
                    "所選妝容的套件已不存在，已改回內建原妝。",
                )
            )
        slider = self.wardrobe_makeup_intensity
        slider.blockSignals(True)
        slider.setValue(
            round(
                self.wardrobe_service.makeup_intensity(
                    notify=self._wardrobe_makeup_read_warning
                )
                * INTENSITY_PERCENT
            )
        )
        slider.blockSignals(False)
        self.wardrobe_makeup_intensity_value.setText(f"{slider.value()}%")

    def _wardrobe_makeup_selected(self, index: int) -> None:
        option_id = str(self.wardrobe_makeup_selector.itemData(index) or BARE_OPTION)
        try:
            self.wardrobe_service.apply_makeup(option_id)
        except IncompatibleBodyProfileError:
            self.wardrobe_status.setText(
                self._t(
                    "wardrobe_body_profile_outdated",
                    "這套服裝是為一代素體製作的，穿在二代素體上會對不準；請用一鍵製衣重新生成",
                )
            )
            return
        except OutfitPackError:
            self.wardrobe_status.setText(
                self._t("wardrobe_makeup_unavailable", "這組妝容目前無法套用，已保留目前妝容。")
            )
            return
        self.wardrobe_status.setText(
            self._t("wardrobe_makeup_cleared", "已卸妝，回到素顏。")
            if option_id == BARE_OPTION
            else self._t("wardrobe_makeup_applied", "已套用所選妝容。")
        )
        self._refresh_wardrobe_preview()

    def _wardrobe_makeup_intensity_changed(self, value: int) -> None:
        self.wardrobe_makeup_intensity_value.setText(f"{int(value)}%")
        self.wardrobe_service.set_makeup_intensity(int(value) / INTENSITY_PERCENT)
        self._refresh_wardrobe_preview()
