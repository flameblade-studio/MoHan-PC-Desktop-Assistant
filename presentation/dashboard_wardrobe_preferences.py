from __future__ import annotations

"""Wardrobe autonomy preferences and manual-override ownership."""

lazy from datetime import UTC, datetime, timedelta

lazy from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QFrame,
    QLabel,
    QSpinBox,
    QVBoxLayout,
)

lazy from domain.autonomous_wardrobe import DEFAULT_MANUAL_LOCK
lazy from presentation.flagship_theme import mark_flagship_card

__all__ = ("DashboardWardrobePreferencesMixin",)


class DashboardWardrobePreferencesMixin:
    """Keep source-neutral wardrobe controls outside the Dashboard shell."""

    def _wardrobe_preferences_card(self) -> QFrame:
        preferences_card = QFrame()
        mark_flagship_card(preferences_card)
        preferences = QVBoxLayout(preferences_card)
        preferences_title = QLabel(
            self._t("wardrobe_autonomous_enabled", "允許墨寒自主選裝")
        )
        preferences_title.setProperty("mohanRole", "cardTitle")
        preferences.addWidget(preferences_title)
        self.autonomous_wardrobe_enabled = QCheckBox(
            self._t("wardrobe_autonomous_enabled", "允許墨寒自主選裝")
        )
        self.autonomous_wardrobe_enabled.setChecked(
            bool(self.db.setting("autonomous_wardrobe_enabled", True))
        )
        self.self_outfit_generation_enabled = QCheckBox(
            self._t(
                "wardrobe_self_generation_enabled",
                "允許墨寒雲端自創新衣（可能產生費用）",
            )
        )
        self.self_outfit_generation_enabled.setChecked(
            bool(self.db.setting("self_outfit_generation_enabled", False))
        )
        self.fashion_trend_search_enabled = QCheckBox(
            self._t(
                "wardrobe_trend_search_enabled",
                "允許以五類情境搜尋流行趨勢作為原創靈感（可能產生費用）",
            )
        )
        self.fashion_trend_search_enabled.setChecked(
            bool(self.db.setting("fashion_trend_search_enabled", False))
        )
        self.generated_outfit_limit = QSpinBox()
        self.generated_outfit_limit.setRange(1, 64)
        self.generated_outfit_limit.setValue(
            int(self.db.setting("generated_outfit_limit", 16))
        )
        (
            generated_limit_control,
            self.generated_outfit_limit_up,
            self.generated_outfit_limit_down,
        ) = self._step_control(
            self.generated_outfit_limit,
            "generatedOutfitLimit",
        )
        self.generated_outfit_storage_gb = QSpinBox()
        self.generated_outfit_storage_gb.setRange(1, 64)
        self.generated_outfit_storage_gb.setSuffix(" GB")
        self.generated_outfit_storage_gb.setValue(
            int(self.db.setting("generated_outfit_storage_gb", 6))
        )
        (
            generated_storage_control,
            self.generated_outfit_storage_gb_up,
            self.generated_outfit_storage_gb_down,
        ) = self._step_control(
            self.generated_outfit_storage_gb,
            "generatedOutfitStorageGb",
        )
        self.manual_wardrobe_lock_hours = QSpinBox()
        self.manual_wardrobe_lock_hours.setRange(0, 720)
        self.manual_wardrobe_lock_hours.setWrapping(True)
        self.manual_wardrobe_lock_hours.setSuffix(" h")
        self.manual_wardrobe_lock_hours.setSpecialValueText(
            self._t("wardrobe_manual_lock_off", "不鎖定")
        )
        self.manual_wardrobe_lock_hours.setValue(
            int(self.db.setting("manual_wardrobe_lock_hours", 6))
        )
        self.manual_wardrobe_lock_hours.valueChanged.connect(
            self._manual_wardrobe_lock_changed
        )
        (
            manual_lock_control,
            self.manual_wardrobe_lock_hours_up,
            self.manual_wardrobe_lock_hours_down,
        ) = self._step_control(
            self.manual_wardrobe_lock_hours,
            "manualWardrobeLockHours",
        )
        self.outfit_image_quality = QComboBox()
        for value, key, fallback in (
            ("low", "wardrobe_quality_low", "快速（畫質較低，最省時省費）"),
            ("medium", "wardrobe_quality_medium", "標準（建議）"),
            ("high", "wardrobe_quality_high", "精緻（最耗時，費用最高）"),
        ):
            self.outfit_image_quality.addItem(self._t(key, fallback), value)
        stored_quality = str(
            self.db.setting("outfit_image_quality", "medium")
        )
        quality_index = self.outfit_image_quality.findData(stored_quality)
        self.outfit_image_quality.setCurrentIndex(
            quality_index if quality_index >= 0 else 1
        )
        preferences.addWidget(self.autonomous_wardrobe_enabled)
        preferences.addWidget(self.self_outfit_generation_enabled)
        preferences.addWidget(self.fashion_trend_search_enabled)
        limits = QFormLayout()
        limits.addRow(
            self._t("wardrobe_image_quality", "雲端製衣畫質"),
            self.outfit_image_quality,
        )
        limits.addRow(
            self._t("wardrobe_generated_limit", "自創服裝保留上限"),
            generated_limit_control,
        )
        limits.addRow(
            self._t("wardrobe_storage_limit", "自創服裝容量上限"),
            generated_storage_control,
        )
        limits.addRow(
            self._t("wardrobe_manual_lock_hours", "手動換裝鎖定時數"),
            manual_lock_control,
        )
        preferences.addLayout(limits)
        preferences.addStretch(1)
        return preferences_card

    def _save_wardrobe_preferences(self) -> None:
        if not hasattr(self, "autonomous_wardrobe_enabled"):
            return
        settings = {
            "autonomous_wardrobe_enabled": self.autonomous_wardrobe_enabled.isChecked(),
            "self_outfit_generation_enabled": self.self_outfit_generation_enabled.isChecked(),
            "fashion_trend_search_enabled": self.fashion_trend_search_enabled.isChecked(),
            "generated_outfit_limit": self.generated_outfit_limit.value(),
            "generated_outfit_storage_gb": self.generated_outfit_storage_gb.value(),
            "manual_wardrobe_lock_hours": self.manual_wardrobe_lock_hours.value(),
            "outfit_image_quality": str(
                self.outfit_image_quality.currentData() or "medium"
            ),
        }
        for key, value in settings.items():
            self.db.set_setting(key, value)

    def _manual_wardrobe_lock_changed(self, hours: int) -> None:
        """Persist the preference and revise an active manual lock immediately."""

        self.db.set_setting("manual_wardrobe_lock_hours", int(hours))
        changed_raw = str(self.db.setting("wardrobe_last_changed_at", "") or "")
        if not changed_raw:
            return
        try:
            changed_at = datetime.fromisoformat(changed_raw)
        except ValueError:
            return
        if changed_at.tzinfo is None or changed_at.utcoffset() is None:
            return
        self.db.set_setting(
            "wardrobe_manual_lock_until",
            "" if hours <= 0 else (changed_at + timedelta(hours=hours)).isoformat(),
        )

    def _record_manual_outfit_selection(self, outfit_id: str) -> None:
        """Give an explicit Dashboard choice temporary priority over autonomy."""

        selected_at = datetime.now(UTC)
        self.db.set_setting("active_outfit_id", outfit_id)
        self.db.set_setting("wardrobe_last_changed_at", selected_at.isoformat())
        default_hours = int(DEFAULT_MANUAL_LOCK.total_seconds() // 3600)
        hours = max(
            0,
            min(
                720,
                int(self.db.setting("manual_wardrobe_lock_hours", default_hours)),
            ),
        )
        self.db.set_setting(
            "wardrobe_manual_lock_until",
            "" if hours == 0 else (selected_at + timedelta(hours=hours)).isoformat(),
        )
