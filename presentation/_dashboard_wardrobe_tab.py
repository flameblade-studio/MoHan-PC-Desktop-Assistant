from __future__ import annotations

lazy from pathlib import Path
lazy from typing import Protocol

lazy from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QPushButton, QScrollArea,
    QTabWidget, QVBoxLayout, QWidget,
)

lazy from application.wardrobe_service import WardrobeService
lazy from presentation.dashboard_artwork import CelestialFrame
lazy from presentation.dashboard_wardrobe_categories import (
    build_appearance_card, reload_appearance_controls,
)
lazy from presentation.flagship_theme import mark_flagship_card
lazy from presentation.wardrobe_layout import WardrobeScrollArea


class _WardrobeDatabase(Protocol):
    path: Path


class _DashboardWardrobeHost(Protocol):
    db: _WardrobeDatabase
    wardrobe_service: WardrobeService
    wardrobe_packages: QListWidget
    wardrobe_status: QLabel
    wardrobe_import_button: QPushButton
    wardrobe_apply_button: QPushButton
    wardrobe_restore_button: QPushButton
    wardrobe_generate_button: QPushButton
    wardrobe_category_tabs: QTabWidget
    wardrobe_appearance_selectors: dict[str, object]
    wardrobe_appearance_buttons: dict[str, object]

    def _t(self, key: str, fallback: str) -> str: ...
    def _reload_wardrobe_packages(self) -> None: ...
    def _wardrobe_preview_card(self) -> QWidget: ...
    def _wardrobe_preferences_card(self) -> QWidget: ...
    def _wardrobe_hero(self) -> QFrame: ...
    def _wardrobe_makeup_card(self) -> QWidget: ...
    def _update_wardrobe_preview_name(
        self,
        current: QListWidgetItem | None,
        previous: QListWidgetItem | None,
    ) -> None: ...
    def _import_outfit_package(self) -> None: ...
    def _preview_selected_outfit(self) -> None: ...
    def _restore_builtin_outfit(self) -> None: ...
    def _request_outfit_generation(self) -> None: ...


def _build_package_library(shell: _DashboardWardrobeHost) -> QFrame:
    library_card = QFrame()
    mark_flagship_card(library_card)
    library = QVBoxLayout(library_card)
    library_title = QLabel(shell._t("wardrobe_package_list", "套件清單"))
    library_title.setProperty("mohanRole", "cardTitle")
    library.addWidget(library_title)
    shell.wardrobe_service = WardrobeService(shell.db.path.parent / "outfits")
    shell.wardrobe_packages = QListWidget()
    shell.wardrobe_packages.setMinimumHeight(130)
    shell.wardrobe_status = QLabel(
        shell._t("wardrobe_status_ready", "雲裳系統已就緒")
    )
    shell.wardrobe_status.setWordWrap(True)
    shell.wardrobe_status.setProperty("mohanRole", "statusPill")
    shell._reload_wardrobe_packages()
    compatibility = QLabel(
        shell._t("wardrobe_compatibility_status", "相容狀態")
        + "："
        + shell._t("wardrobe_compatible", "相容")
    )
    compatibility.setProperty("mohanRole", "muted")
    source_policy = QLabel(
        shell._t(
            "wardrobe_source_policy",
            "來源分流：炎劍官方・使用者匯入・墨寒自創",
        )
    )
    source_policy.setWordWrap(True)
    source_policy.setProperty("mohanRole", "muted")
    library.addWidget(shell.wardrobe_packages, 1)
    library.addWidget(compatibility)
    library.addWidget(source_policy)
    library.addWidget(_build_package_actions(shell))
    return library_card


def _build_package_actions(shell: _DashboardWardrobeHost) -> QWidget:
    actions = QWidget()
    row = QVBoxLayout(actions)
    row.setContentsMargins(0, 0, 0, 0)
    shell.wardrobe_import_button = QPushButton(
        shell._t("wardrobe_import", "匯入服裝套件")
    )
    shell.wardrobe_apply_button = QPushButton(
        shell._t("wardrobe_apply", "套用選取服裝")
    )
    shell.wardrobe_restore_button = QPushButton(
        shell._t("wardrobe_restore_builtin", "還原內建服裝")
    )
    shell.wardrobe_generate_button = QPushButton(
        shell._t("wardrobe_generate_now", "立即生成新衣（將使用圖片 API）")
    )
    row.addWidget(shell.wardrobe_import_button)
    row.addWidget(shell.wardrobe_apply_button)
    row.addWidget(shell.wardrobe_restore_button)
    row.addWidget(shell.wardrobe_generate_button)
    return actions


def _build_category_panel(
    shell: _DashboardWardrobeHost,
    library_card: QFrame,
    preferences_card: QWidget,
) -> CelestialFrame:
    panel = CelestialFrame()
    panel.setProperty("mohanRole", "wardrobeControls")
    controls = QVBoxLayout(panel)
    controls.setContentsMargins(28, 54, 28, 30)
    shell.wardrobe_category_tabs = QTabWidget()
    shell.wardrobe_category_tabs.setObjectName("wardrobeCategoryTabs")
    shell.wardrobe_appearance_selectors = {}
    shell.wardrobe_appearance_buttons = {}
    hairstyle_title = shell._t("wardrobe_hairstyle_tab", "髮型")
    headwear_title = shell._t("wardrobe_headwear_tab", "髮飾")
    categories = (
        (library_card, shell._t("wardrobe_clothing_tab", "衣裝")),
        (build_appearance_card(shell, "hairstyle", hairstyle_title), hairstyle_title),
        (build_appearance_card(shell, "headwear", headwear_title), headwear_title),
        (shell._wardrobe_makeup_card(), shell._t("wardrobe_makeup_title", "妝容")),
        (preferences_card, shell._t("wardrobe_preferences_tab", "自主選裝")),
    )
    for widget, title in categories:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setWidget(widget)
        shell.wardrobe_category_tabs.addTab(scroll, title)
    controls.addWidget(shell.wardrobe_category_tabs)
    controls.addWidget(shell.wardrobe_status)
    reload_appearance_controls(shell)
    return panel


def _connect_wardrobe_actions(shell: _DashboardWardrobeHost) -> None:
    shell.wardrobe_packages.currentItemChanged.connect(
        shell._update_wardrobe_preview_name
    )
    shell.wardrobe_import_button.clicked.connect(shell._import_outfit_package)
    shell.wardrobe_apply_button.clicked.connect(shell._preview_selected_outfit)
    shell.wardrobe_restore_button.clicked.connect(shell._restore_builtin_outfit)
    shell.wardrobe_generate_button.clicked.connect(shell._request_outfit_generation)


def build_wardrobe_tab(shell: _DashboardWardrobeHost) -> QWidget:
    tab = QWidget()
    root = QVBoxLayout(tab)
    root.setContentsMargins(10, 8, 10, 8)
    root.setSpacing(10)
    columns = QHBoxLayout()
    columns.setSpacing(14)
    library_card = _build_package_library(shell)
    preview_card = shell._wardrobe_preview_card()
    preferences_card = shell._wardrobe_preferences_card()
    stage = QWidget()
    stage_layout = QVBoxLayout(stage)
    stage_layout.setContentsMargins(0, 0, 0, 0)
    stage_layout.addWidget(shell._wardrobe_hero())
    stage_layout.addWidget(preview_card, 1)
    panel = _build_category_panel(shell, library_card, preferences_card)
    columns.addWidget(stage, 5)
    columns.addWidget(panel, 6)
    root.addLayout(columns, 1)
    _connect_wardrobe_actions(shell)
    return WardrobeScrollArea(tab, columns, stage, panel)
