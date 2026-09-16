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

lazy from domain.outfit_pack import (
    FOUNDATION_SLOT,
    IncompatibleBodyProfileError,
    MAKEUP_SLOTS,
    MAKEUP_SLOTS_V2,
    OutfitPackError,
)
lazy from domain.character_pose import canonical_view_id
lazy from presentation.flagship_theme import mark_flagship_card

__all__ = ("DashboardWardrobeMakeupMixin",)

INTENSITY_PERCENT = 100
INTENSITY_SINGLE_STEP = 5
INTENSITY_PAGE_STEP = 10
BARE_OPTION = "none"
CLASSIC_OPTION = "builtin/classic"
LIGHT_OPTION = "builtin/light"
GLAMOROUS_OPTION = "builtin/glamorous"
FRONT_SILHOUETTE = canonical_view_id(0)


class DashboardWardrobeMakeupMixin:
    """Makeup rides the same pack pipeline as garments; only its menu and slider are new UI."""

    def _wardrobe_makeup_card(self) -> QFrame:
        card = QFrame()
        mark_flagship_card(card)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(22, 22, 22, 22)
        layout.setSpacing(20)
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
        slider_row.setMinimumHeight(30)
        slider_layout = QHBoxLayout(slider_row)
        slider_layout.setContentsMargins(0, 0, 0, 0)
        slider_layout.addWidget(self.wardrobe_makeup_intensity, 1)
        slider_layout.addWidget(self.wardrobe_makeup_intensity_value)
        form = QFormLayout()
        form.setRowWrapPolicy(QFormLayout.WrapAllRows)
        form.setVerticalSpacing(16)
        form.addRow(
            self._t("wardrobe_makeup_item", "妝容選擇"),
            self.wardrobe_makeup_selector,
        )
        form.addRow(
            self._t("wardrobe_makeup_intensity", "妝感濃淡"),
            slider_row,
        )
        self._add_makeup_detail_controls(form)
        self.wardrobe_makeup_form = form
        self._add_makeup_foundation_control(form)
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
        preview = getattr(self, "wardrobe_character_preview", None)
        view_changed = getattr(preview, "view_changed", None)
        if view_changed is not None:
            view_changed.connect(self._wardrobe_makeup_view_changed)
        self._reload_wardrobe_makeup_options()
        self.wardrobe_makeup_selector.currentIndexChanged.connect(
            self._wardrobe_makeup_selected
        )
        self.wardrobe_makeup_intensity.valueChanged.connect(
            self._wardrobe_makeup_intensity_changed
        )
        self.wardrobe_makeup_foundation.valueChanged.connect(
            self._wardrobe_makeup_foundation_changed
        )
        return card

    def _add_makeup_foundation_control(self, form: QFormLayout) -> None:
        label = self._t("wardrobe_makeup_foundation_intensity", "粉底濃淡")
        self.wardrobe_makeup_foundation_label = QLabel(label)
        self.wardrobe_makeup_foundation = QSlider(Qt.Horizontal)
        self.wardrobe_makeup_foundation.setRange(0, INTENSITY_PERCENT)
        self.wardrobe_makeup_foundation.setSingleStep(INTENSITY_SINGLE_STEP)
        self.wardrobe_makeup_foundation.setPageStep(INTENSITY_PAGE_STEP)
        self.wardrobe_makeup_foundation.setAccessibleName(label)
        self.wardrobe_makeup_foundation.setProperty("makeupSlot", FOUNDATION_SLOT)
        self.wardrobe_makeup_foundation_value = QLabel(f"{INTENSITY_PERCENT}%")
        self.wardrobe_makeup_foundation_value.setProperty("mohanRole", "muted")
        self.wardrobe_makeup_foundation_row = QWidget()
        self.wardrobe_makeup_foundation_row.setMinimumHeight(30)
        foundation_layout = QHBoxLayout(self.wardrobe_makeup_foundation_row)
        foundation_layout.setContentsMargins(0, 0, 0, 0)
        foundation_layout.addWidget(self.wardrobe_makeup_foundation, 1)
        foundation_layout.addWidget(self.wardrobe_makeup_foundation_value)
        form.addRow(self.wardrobe_makeup_foundation_label, self.wardrobe_makeup_foundation_row)
        self.wardrobe_makeup_foundation_label.hide()
        self.wardrobe_makeup_foundation_row.hide()

    def _active_makeup_slots(
        self,
        silhouette: str | None = None,
    ) -> frozenset[str]:
        """Read makeup capability for the preview's current canonical view."""

        capability = getattr(self.wardrobe_service, "active_makeup_slots", None)
        if not callable(capability):
            # Older services only know the three-slot makeup contract.
            return frozenset()
        if silhouette is None:
            preview = getattr(self, "wardrobe_character_preview", None)
            silhouette = getattr(preview, "view_id", None)
            if not isinstance(silhouette, str) or not silhouette.strip():
                silhouette = getattr(self, "_wardrobe_pose_view", FRONT_SILHOUETTE)
        if not isinstance(silhouette, str) or not silhouette.strip():
            silhouette = FRONT_SILHOUETTE
        try:
            slots = capability(
                silhouette,
                notify=self._wardrobe_makeup_read_warning,
            )
        except (IncompatibleBodyProfileError, OutfitPackError, OSError, ValueError):
            return frozenset()
        if not isinstance(slots, frozenset):
            return frozenset()
        return slots

    def _wardrobe_makeup_view_changed(self, view_id: str) -> None:
        """Refresh view-specific controls when the turntable changes angle."""

        self._refresh_foundation_control(view_id=view_id)

    def _refresh_foundation_control(
        self,
        details: object | None = None,
        *,
        view_id: str | None = None,
    ) -> None:
        """Show and synchronise foundation only for a v2-capable view."""

        slots = self._active_makeup_slots(view_id)
        supported = FOUNDATION_SLOT in slots
        self.wardrobe_makeup_foundation_label.setVisible(supported)
        self.wardrobe_makeup_foundation_row.setVisible(supported)
        if supported:
            values = details
            if values is None:
                read_slots = (
                    MAKEUP_SLOTS_V2
                    if FOUNDATION_SLOT in slots
                    else slots or MAKEUP_SLOTS
                )
                values = self.wardrobe_service.makeup_slot_intensities(
                    notify=self._wardrobe_makeup_read_warning,
                    slots=read_slots,
                )
            intensity = (
                values.get(FOUNDATION_SLOT, 1.0)
                if hasattr(values, "get")
                else 1.0
            )
            slider = self.wardrobe_makeup_foundation
            slider.blockSignals(True)
            slider.setValue(round(float(intensity) * INTENSITY_PERCENT))
            slider.blockSignals(False)
            self.wardrobe_makeup_foundation_value.setText(f"{slider.value()}%")
        self.wardrobe_makeup_foundation_row.updateGeometry()
        self.wardrobe_makeup_foundation_label.updateGeometry()
        self.wardrobe_makeup_form.invalidate()
        self.wardrobe_makeup_form.activate()

    def _add_makeup_detail_controls(self, form: QFormLayout) -> None:
        self.wardrobe_makeup_details = {}
        self.wardrobe_makeup_detail_values = {}
        for slot, label in (
            ("eyes", self._t("wardrobe_makeup_eyes_intensity", "眼妝濃淡")),
            ("cheeks", self._t("wardrobe_makeup_cheeks_intensity", "腮紅濃淡")),
            ("lips", self._t("wardrobe_makeup_lips_intensity", "唇妝濃淡")),
        ):
            slider = QSlider(Qt.Horizontal)
            slider.setRange(0, INTENSITY_PERCENT)
            slider.setSingleStep(INTENSITY_SINGLE_STEP)
            slider.setPageStep(INTENSITY_PAGE_STEP)
            slider.setAccessibleName(label)
            slider.setProperty("makeupSlot", slot)
            value = QLabel(f"{INTENSITY_PERCENT}%")
            value.setProperty("mohanRole", "muted")
            row = QWidget()
            row.setMinimumHeight(30)
            layout = QHBoxLayout(row)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.addWidget(slider, 1)
            layout.addWidget(value)
            self.wardrobe_makeup_details[slot] = slider
            self.wardrobe_makeup_detail_values[slot] = value
            form.addRow(label, row)
            slider.valueChanged.connect(self._wardrobe_makeup_detail_changed)

    def _makeup_option_label(self, option) -> str:
        if option.option_id == BARE_OPTION:
            return self._t("wardrobe_makeup_none", "素顏（不上妝）")
        if option.option_id == CLASSIC_OPTION:
            label = self._t("wardrobe_makeup_variant_classic", "標準妝")
        elif option.option_id == LIGHT_OPTION:
            label = self._t("wardrobe_makeup_variant_light", "淡妝")
        elif option.option_id == GLAMOROUS_OPTION:
            label = self._t("wardrobe_makeup_variant_glamorous", "華麗妝")
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
            options = self.wardrobe_service.makeup_options(self.ui_language)
        except OutfitPackError:
            self.wardrobe_status.setText(self._t("wardrobe_packages_read_failed", '讀取外觀套件需要處理，請檢查或重新匯入；目前選擇持續使用。'))
            previous = selector.blockSignals(True)
            selector.clear()
            selector.blockSignals(previous)
            return
        try:
            state = self.wardrobe_service.active_makeup()
        except IncompatibleBodyProfileError:
            state = None
            self.wardrobe_status.setText(
                self._t(
                    "wardrobe_body_profile_outdated",
                    "這套服裝需要二代素體素材；請用一鍵製衣重新生成",
                )
            )
        except OutfitPackError:
            state = None
        selector.blockSignals(True)
        selector.clear()
        for option in options:
            selector.addItem(self._makeup_option_label(option), option.option_id)
        active_id = state.option_id if state is not None else BARE_OPTION
        index = selector.findData(active_id)
        selector.setCurrentIndex(index if index >= 0 else 0)
        selector.blockSignals(False)
        if state is not None and state.fallback:
            # The recovery path for an older pack: fall back to the built-in default, tell the user once.
            self.wardrobe_service.apply_makeup(state.option_id)
            self.wardrobe_status.setText(
                self._t(
                    "wardrobe_makeup_pack_missing",
                    "所選妝容的套件已不存在，已改回內建標準妝。",
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
        active_slots = self._active_makeup_slots()
        read_slots = (
            MAKEUP_SLOTS_V2
            if FOUNDATION_SLOT in active_slots
            else active_slots or MAKEUP_SLOTS
        )
        details = self.wardrobe_service.makeup_slot_intensities(
            notify=self._wardrobe_makeup_read_warning,
            slots=read_slots,
        )
        for slot, detail_slider in self.wardrobe_makeup_details.items():
            detail_slider.blockSignals(True)
            detail_slider.setValue(round(details[slot] * INTENSITY_PERCENT))
            detail_slider.blockSignals(False)
            self.wardrobe_makeup_detail_values[slot].setText(f"{detail_slider.value()}%")
        self._refresh_foundation_control(details)

    def _wardrobe_makeup_selected(self, index: int) -> None:
        option_id = str(self.wardrobe_makeup_selector.itemData(index) or BARE_OPTION)
        try:
            self.wardrobe_service.apply_makeup(option_id)
        except IncompatibleBodyProfileError:
            self.wardrobe_status.setText(
                self._t(
                    "wardrobe_body_profile_outdated",
                    "這套服裝需要二代素體素材；請用一鍵製衣重新生成",
                )
            )
            return
        except OutfitPackError:
            self.wardrobe_status.setText(
                self._t("wardrobe_makeup_unavailable", '套用這組妝容需要處理；目前妝容持續使用。')
            )
            return
        self.wardrobe_status.setText(
            self._t("wardrobe_makeup_cleared", "已卸妝，回到素顏。")
            if option_id == BARE_OPTION
            else self._t("wardrobe_makeup_applied", "已套用所選妝容。")
        )
        self._refresh_foundation_control()
        self._refresh_wardrobe_preview()

    def _wardrobe_makeup_intensity_changed(self, value: int) -> None:
        self.wardrobe_makeup_intensity_value.setText(f"{int(value)}%")
        self.wardrobe_service.set_makeup_intensity(int(value) / INTENSITY_PERCENT)
        self._refresh_wardrobe_preview()

    def _wardrobe_makeup_detail_changed(self, value: int) -> None:
        slider = self.sender()
        if not isinstance(slider, QSlider):
            raise RuntimeError("Makeup detail changes require their slider sender.")
        slot = str(slider.property("makeupSlot"))
        self.wardrobe_service.set_makeup_slot_intensity(slot, int(value) / INTENSITY_PERCENT)
        self.wardrobe_makeup_detail_values[slot].setText(f"{int(value)}%")
        self._refresh_wardrobe_preview()

    def _wardrobe_makeup_foundation_changed(self, value: int) -> None:
        """Persist foundation independently from global and legacy makeup slots."""

        self.wardrobe_service.set_makeup_slot_intensity(
            FOUNDATION_SLOT,
            int(value) / INTENSITY_PERCENT,
        )
        self.wardrobe_makeup_foundation_value.setText(f"{int(value)}%")
        self._refresh_wardrobe_preview()
