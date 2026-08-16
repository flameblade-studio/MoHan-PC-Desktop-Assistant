from __future__ import annotations

lazy import html
lazy from collections import deque
lazy from functools import partial
lazy from pathlib import Path

lazy from PySide6.QtCore import QEvent, Qt, QThreadPool, QTimer
lazy from PySide6.QtGui import QKeySequence, QMouseEvent, QPixmap, QShortcut
lazy from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QSplitter,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

lazy from application.presentation_ports import (
    PlatformServicePort,
    PresentationDatabasePort,
    format_duration,
)
lazy from application.wardrobe_service import BUILTIN_OUTFIT_ID, WardrobeService
lazy from domain.outfit_pack import OutfitPackError
lazy from domain.app_profile import (
    personalize_text,
    profile_setting,
    profile_window_title,
)
lazy from domain.feature_registry import DashboardFeatureRegistry
lazy from domain.language_support import (
    is_english,
    is_japanese,
    is_simplified_chinese,
)
lazy from presentation.companion_platform import reminder_line
lazy from presentation.dashboard_composition import DashboardDependencies
lazy from presentation.flagship_theme import (
    create_flagship_ornament,
    mark_flagship_card,
)
lazy from presentation.presentation_resources import (
    STYLE,
    application_icon,
    resource_path,
)
lazy from presentation.settings_ui_localization import SettingsText, settings_text
lazy from presentation.ui_localization import (
    MODE_LABELS,
    SIMPLIFIED_MODE_LABELS,
    display_label,
    ui_text,
)
lazy from presentation.ui_localization_ja import JAPANESE_MODE_LABELS

__all__ = ("DashboardShellMixin",)


class DashboardShellMixin:
    """Dashboard window shell and cross-tab coordination behavior."""

    def _mount_global_settings_actions(self, root: QVBoxLayout) -> None:
        actions = QHBoxLayout()
        actions.setContentsMargins(0, 8, 14, 4)
        actions.setSpacing(10)
        self.cancel_settings_button = QPushButton(
            self._t("cancel_without_saving", "取消（不要保存）")
        )
        self.cancel_settings_button.setObjectName("globalCancelSettingsButton")
        self.cancel_settings_button.setProperty("mohanAction", "secondary")
        self.save_settings_button = QPushButton(
            self._t("save_settings", "保存設定")
        )
        self.save_settings_button.setObjectName("globalSaveSettingsButton")
        self.save_settings_button.setProperty("mohanPrimaryAction", True)
        self.save_settings_button.setProperty("mohanAction", "primary")
        self.save_settings_button.setStyleSheet(
            "/* background is supplied by the active contrast-safe theme; "
            "font-weight:700; padding:10px 24px */"
        )
        actions.addStretch(1)
        actions.addWidget(self.cancel_settings_button)
        actions.addWidget(self.save_settings_button)
        root.addLayout(actions)
        self.cancel_settings_button.clicked.connect(
            self.cancel_settings_changes
        )
        self.save_settings_button.clicked.connect(self.save_all_settings)

    def cancel_settings_changes(self) -> None:
        center = getattr(self, "flagship_center", None)
        if center is not None:
            center.cancel_draft_settings()
        theme_session = getattr(self, "theme_session", None)
        if theme_session is not None:
            theme_session.cancel()
        self.db.restore_settings_snapshot(self._settings_draft_snapshot)
        if center is not None:
            center.reload_draft_settings()
        self.settings_saved.emit()
        self.refresh_all()
        self.reject()

    def save_all_settings(self) -> bool:
        center = getattr(self, "flagship_center", None)
        center_values = (
            center.validate_draft_settings() if center is not None else None
        )
        if center is not None and center_values is None:
            return False
        before = self.db.settings_snapshot()
        try:
            if not self.save_settings(
                silent=True,
                persist_external=False,
                finish=False,
            ):
                return False
            self.save_permissions()
            if center is not None and not center.save_draft_settings(center_values):
                raise RuntimeError("Control-center settings were not saved.")
            theme_session = getattr(self, "theme_session", None)
            if theme_session is not None:
                theme_session.save()
            self._save_wardrobe_preferences()
        except Exception:  # noqa: BLE001 -- global settings rollback boundary
            self.db.restore_settings_snapshot(before)
            if center is not None:
                center.reload_draft_settings()
            self.refresh_all()
            return False
        self._persist_external_settings()
        self._settings_draft_snapshot = self.db.settings_snapshot()
        if center is not None:
            center.save_home_settings()
        self.settings_saved.emit()
        self.speak_requested.emit(
            self._t("settings_saved", "設定已保存。"),
            "happy",
        )
        return True

    def _initialize_dashboard_state(
        self,
        db: PresentationDatabasePort,
        dependencies: DashboardDependencies,
    ) -> None:
        self.db = db
        self.listener = dependencies.listener
        self.secret_store = dependencies.secret_store
        self.azure_secret_store = dependencies.azure_secret_store
        self.azure_hd_secret_store = dependencies.azure_hd_secret_store
        self.azure_tts = dependencies.azure_speech
        self.azure_hd_tts = dependencies.azure_hd_speech
        self.secret_store_factory = (
            dependencies.secret_store_factory
        )
        self.cloud_vision_service_factory = (
            dependencies.cloud_vision_service_factory
        )
        self.dense_face_provider_factory = dependencies.dense_face_provider_factory
        if dependencies.platform_services is None:
            raise ValueError("Dashboard requires an injected platform service.")
        if dependencies.presentation_ports is None:
            raise ValueError("Dashboard requires injected presentation ports.")
        self.platform_services: PlatformServicePort = dependencies.platform_services
        self.presentation_ports = dependencies.presentation_ports
        self.ai_worker_factory = self.presentation_ports.ai_worker_factory
        self.voice_catalog = self.presentation_ports.voice_catalog
        self.profile_manager_factory = self.presentation_ports.profile_manager_factory
        self.update_manager_factory = self.presentation_ports.update_manager_factory
        self.autostart_configurator = self.presentation_ports.autostart_configurator
        self.thread_pool = QThreadPool.globalInstance()
        self.ai_queue: deque[tuple[str, str]] = deque()
        self.ai_busy = False
        self.ai_wait_generation = 0
        self.active_ai_wait_generation = 0
        self.next_expression_metadata: tuple[str, float, str] | None = None
        self.chat_loaded_limit = 50
        self.chat_zoom_percent = int(
            self.db.setting("chat_zoom_percent", 100)
        )
        self.mode = str(db.setting("mode", "工作"))
        self.ui_language = profile_setting(db, "ui_language")
        self.assistant_name = profile_setting(db, "assistant_name")
        self.user_title = profile_setting(db, "user_title")
        self.organization_name = profile_setting(
            db, "organization_name"
        )

    def _configure_dashboard_window(self) -> None:
        db = self.db
        self.setWindowTitle(profile_window_title(db))
        self.resize(900, 660)
        self.setMinimumSize(720, 480)
        self.setStyleSheet(STYLE)
        self.setWindowFlags(
            Qt.Window
            | Qt.WindowTitleHint
            | Qt.WindowSystemMenuHint
            | Qt.WindowMinimizeButtonHint
            | Qt.WindowMaximizeButtonHint
            | Qt.WindowCloseButtonHint
        )
        # Apply the icon after the native window flags are final. On Windows,
        # changing flags can recreate the native handle used by the taskbar.
        self.setWindowIcon(application_icon())
        self.front_raise_timer = QTimer(self)
        self.front_raise_timer.setSingleShot(True)
        self.front_raise_timer.timeout.connect(self._bring_to_front)
        self.emergency_shortcut = QShortcut(QKeySequence("Esc"), self)
        self.emergency_shortcut.setContext(Qt.ApplicationShortcut)
        self.emergency_shortcut.activated.connect(self._emergency_stop)

    def _build_mode_combo(self) -> QComboBox:
        combo = QComboBox()
        for value in ("工作", "陪伴", "勿擾", "會議", "離席", "休眠"):
            combo.addItem(
                display_label(
                    self.ui_language,
                    value,
                    MODE_LABELS,
                    SIMPLIFIED_MODE_LABELS,
                    JAPANESE_MODE_LABELS,
                ),
                value,
            )
        combo.setCurrentIndex(max(0, combo.findData(self.mode)))
        return combo

    def _build_dashboard_header(
        self,
        root: QVBoxLayout,
    ) -> tuple[QPushButton, QPushButton]:
        command_deck = QFrame()
        command_deck.setProperty("mohanRole", "commandDeck")
        header = QHBoxLayout(command_deck)
        header.setContentsMargins(16, 10, 16, 10)
        header.setSpacing(10)
        self.mode_combo = self._build_mode_combo()
        self.work_label = QLabel()
        self.work_label.setProperty("mohanRole", "headerStatus")
        start_btn = QPushButton(self._t("start_work", "開始工作"))
        stop_btn = QPushButton(self._t("stop_work", "結束工作"))
        start_btn.setProperty("mohanAction", "primary")
        stop_btn.setProperty("mohanAction", "secondary")
        brand = QVBoxLayout()
        self.header_title = QLabel(
            f"<b>{html.escape(profile_window_title(self.db))}</b>"
        )
        self.header_title.setProperty("mohanRole", "brand")
        brand_line = QLabel(
            self._t("dashboard_brand_line", "墨色為骨・寒光為心")
        )
        brand_line.setProperty("mohanRole", "muted")
        brand.addWidget(self.header_title)
        brand.addWidget(brand_line)
        header.addWidget(create_flagship_ornament(self, size=72))
        header.addLayout(brand)
        header.addStretch()
        header.addWidget(QLabel(self._t("mode", "模式")))
        header.addWidget(self.mode_combo)
        header.addWidget(self.work_label)
        header.addWidget(start_btn)
        header.addWidget(stop_btn)
        root.addWidget(command_deck)
        return start_btn, stop_btn

    def _mount_dashboard_tabs(self, root: QVBoxLayout) -> None:
        self.tabs = QTabWidget()
        self.tabs.setProperty("mohanRole", "gameStage")
        self.feature_registry = DashboardFeatureRegistry()
        chat_title = self._t("tab_chat", "對話")
        self.feature_registry.register(
            "chat",
            chat_title,
            partial(self._themed_feature_page, self._chat_tab, chat_title),
        )
        today_title = self._t("tab_today", "今日待辦")
        self.feature_registry.register(
            "today",
            today_title,
            partial(self._themed_feature_page, self._today_tab, today_title),
        )
        platforms_title = self._t("tab_platforms", "工作平台")
        self.feature_registry.register(
            "platforms",
            platforms_title,
            partial(
                self._themed_feature_page,
                self._platform_tab,
                platforms_title,
            ),
        )
        memory_title = self._t("tab_memory", "長期記憶")
        self.feature_registry.register(
            "memory",
            memory_title,
            partial(self._themed_feature_page, self._memory_tab, memory_title),
        )
        voice_title = self._t("tab_voice", "聲音")
        self.feature_registry.register(
            "voice",
            voice_title,
            partial(self._themed_feature_page, self._voice_tab, voice_title),
        )
        permissions_title = self._t("tab_permissions", "電腦權限")
        self.feature_registry.register(
            "permissions",
            permissions_title,
            partial(
                self._themed_feature_page,
                self._permissions_tab,
                permissions_title,
            ),
        )
        self.feature_registry.register(
            "wardrobe",
            self._t("tab_wardrobe", "雲裳閣"),
            self._wardrobe_tab,
        )
        settings_title = self._t("tab_settings", "設定")
        self.feature_registry.register(
            "settings",
            settings_title,
            partial(
                self._themed_feature_page,
                self._settings_tab,
                settings_title,
            ),
        )
        self.feature_registry.mount(self.tabs)
        self.tabs.tabBar().hide()

        lobby = QFrame()
        lobby.setProperty("mohanRole", "gameLobby")
        lobby_layout = QHBoxLayout(lobby)
        lobby_layout.setContentsMargins(0, 0, 0, 0)
        lobby_layout.setSpacing(12)

        navigation = QFrame()
        navigation.setProperty("mohanRole", "gameNavigation")
        navigation.setFixedWidth(148)
        navigation_layout = QVBoxLayout(navigation)
        navigation_layout.setContentsMargins(10, 14, 10, 14)
        navigation_layout.setSpacing(8)
        navigation_title = QLabel("✦ MoHan ✦")
        navigation_title.setAlignment(Qt.AlignCenter)
        navigation_title.setProperty("mohanRole", "navigationTitle")
        navigation_layout.addWidget(navigation_title)
        navigation_layout.addWidget(
            create_flagship_ornament(navigation, size=66),
            0,
            Qt.AlignCenter,
        )

        self.game_navigation_buttons: list[QPushButton] = []
        for index, feature in enumerate(self.feature_registry.features):
            button = QPushButton(feature.title)
            button.setFixedHeight(54)
            button.setCheckable(True)
            button.setAutoExclusive(True)
            button.setProperty("mohanAction", "navigation")
            button.setAccessibleName(feature.title)
            button.clicked.connect(
                partial(self._select_game_lobby_page, index)
            )
            navigation_layout.addWidget(button)
            self.game_navigation_buttons.append(button)
        navigation_layout.addStretch(1)

        lobby_layout.addWidget(navigation)
        lobby_layout.addWidget(self.tabs, 1)
        root.addWidget(lobby, 1)
        self.tabs.currentChanged.connect(self._sync_game_lobby_navigation)
        self._sync_game_lobby_navigation(self.tabs.currentIndex())

    def _select_game_lobby_page(self, index: int) -> None:
        """Open one real feature page from the game-style navigation."""

        self.tabs.setCurrentIndex(index)

    def _sync_game_lobby_navigation(self, index: int) -> None:
        """Keep keyboard, tests and the visible lobby selection in sync."""

        for button_index, button in enumerate(self.game_navigation_buttons):
            button.setChecked(button_index == index)

    def _themed_feature_page(self, factory, title: str) -> QWidget:
        """Place one real feature panel beside the persistent character stage."""

        content = factory()
        content.setProperty("mohanRole", "featureContent")
        page = QWidget()
        page.setProperty("mohanRole", "featurePage")
        page_layout = QHBoxLayout(page)
        page_layout.setContentsMargins(14, 14, 14, 14)
        page_layout.setSpacing(14)

        stage = QFrame()
        stage.setProperty("mohanRole", "characterStage")
        stage.setMinimumWidth(400)
        stage_layout = QVBoxLayout(stage)
        stage_layout.setContentsMargins(18, 18, 18, 18)
        stage_portrait = QLabel()
        stage_portrait.setObjectName("dashboardCharacterStagePortrait")
        stage_portrait.setAlignment(Qt.AlignCenter | Qt.AlignBottom)
        stage_portrait.setAccessibleName(profile_window_title(self.db))
        stage_source = QPixmap(
            str(
                resource_path(
                    "assets/pose-atlas/v4-working/yaw+000-pitch+00.png"
                )
            )
        )
        if not stage_source.isNull():
            stage_portrait.setPixmap(
                stage_source.scaled(
                    370,
                    580,
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation,
                )
            )
        stage_layout.addWidget(stage_portrait, 1)
        stage_caption = QFrame()
        stage_caption.setProperty("mohanRole", "stageCaption")
        stage_caption_layout = QVBoxLayout(stage_caption)
        stage_caption_layout.setContentsMargins(14, 9, 14, 9)
        stage_title = QLabel(title)
        stage_title.setAlignment(Qt.AlignCenter)
        stage_title.setProperty("mohanRole", "stageTitle")
        stage_caption_layout.addWidget(stage_title)
        stage_layout.addWidget(stage_caption)

        dock = QFrame()
        dock.setProperty("mohanRole", "featureDock")
        dock.setMinimumWidth(500)
        dock_layout = QVBoxLayout(dock)
        dock_layout.setContentsMargins(12, 12, 12, 12)
        dock_layout.setSpacing(10)
        banner = QFrame()
        banner.setProperty("mohanRole", "pageBanner")
        banner_layout = QHBoxLayout(banner)
        banner_layout.setContentsMargins(16, 8, 16, 8)
        heading = QLabel(title)
        heading.setProperty("mohanRole", "pageTitle")
        title_stack = QVBoxLayout()
        title_stack.addWidget(heading)
        banner_layout.addLayout(title_stack, 1)
        banner_layout.addWidget(create_flagship_ornament(banner, size=58))
        dock_layout.addWidget(banner)
        dock_layout.addWidget(content, 1)
        feature_splitter = QSplitter(Qt.Horizontal)
        feature_splitter.setObjectName("featurePageSplitter")
        feature_splitter.setChildrenCollapsible(False)
        feature_splitter.addWidget(stage)
        feature_splitter.addWidget(dock)
        feature_splitter.setStretchFactor(0, 6)
        feature_splitter.setStretchFactor(1, 7)
        feature_splitter.setSizes((540, 630))
        page_layout.addWidget(feature_splitter, 1)
        return page

    def _wardrobe_tab(self) -> QWidget:
        tab = QWidget()
        root = QVBoxLayout(tab)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(14)

        hero = QFrame()
        hero.setProperty("mohanRole", "hero")
        hero_row = QHBoxLayout(hero)
        hero_text = QVBoxLayout()
        hero_title = QLabel("✦ " + self._t("tab_wardrobe", "雲裳閣") + " ✦")
        hero_title.setProperty("mohanRole", "sectionTitle")
        hero_subtitle = QLabel(
            self._t(
                "wardrobe_pavilion_subtitle",
                "讓墨寒依天候、心情與場合挑選完整造型，也保留您的決定。",
            )
        )
        hero_subtitle.setWordWrap(True)
        hero_subtitle.setProperty("mohanRole", "muted")
        hero_text.addWidget(hero_title)
        hero_text.addWidget(hero_subtitle)
        hero_row.addLayout(hero_text, 1)
        hero_row.addWidget(create_flagship_ornament(hero, size=110))
        root.addWidget(hero)

        columns = QHBoxLayout()
        columns.setSpacing(14)
        library_card = QFrame()
        mark_flagship_card(library_card)
        library = QVBoxLayout(library_card)
        library_title = QLabel(
            self._t("wardrobe_package_list", "套件清單")
        )
        library_title.setProperty("mohanRole", "cardTitle")
        library.addWidget(library_title)
        self.wardrobe_service = WardrobeService(
            self.db.path.parent / "outfits"
        )
        self.wardrobe_packages = QListWidget()
        self.wardrobe_packages.setMinimumHeight(260)
        selected_id = WardrobeService.selected_outfit(
            self.db.setting("active_outfit_id", BUILTIN_OUTFIT_ID)
        )
        for outfit in self.wardrobe_service.outfits(self.ui_language):
            label = outfit.display_name
            if outfit.built_in:
                label = self._t("wardrobe_default_outfit", "內建預設服裝")
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, outfit.outfit_id)
            item.setToolTip(
                self._t(
                    "wardrobe_compatibility_status",
                    "相容狀態",
                )
                + "："
                + (
                    self._t("wardrobe_compatible", "相容")
                    if outfit.compatible
                    else self._t("wardrobe_incompatible", "不相容")
                )
            )
            self.wardrobe_packages.addItem(item)
            if outfit.outfit_id == selected_id:
                self.wardrobe_packages.setCurrentItem(item)
        self.wardrobe_status = QLabel(
            self._t("wardrobe_status_ready", "雲裳系統已就緒")
        )
        self.wardrobe_status.setWordWrap(True)
        self.wardrobe_status.setProperty("mohanRole", "statusPill")
        wardrobe_compatibility = QLabel(
            self._t("wardrobe_compatibility_status", "相容狀態")
            + "："
            + self._t("wardrobe_compatible", "相容")
        )
        wardrobe_compatibility.setProperty("mohanRole", "muted")
        source_policy = QLabel(
            self._t(
                "wardrobe_source_policy",
                "來源分流：炎劍官方・使用者匯入・墨寒自創",
            )
        )
        source_policy.setWordWrap(True)
        source_policy.setProperty("mohanRole", "muted")

        preview_card = QFrame()
        preview_card.setProperty("mohanRole", "portraitCard")
        preview = QVBoxLayout(preview_card)
        preview.setContentsMargins(14, 14, 14, 14)
        preview.setSpacing(8)
        preview_title = QLabel(
            self._t("wardrobe_character_preview", "墨寒造型預覽")
        )
        preview_title.setAlignment(Qt.AlignCenter)
        preview_title.setProperty("mohanRole", "cardTitle")
        self.wardrobe_character_preview = QLabel()
        self.wardrobe_character_preview.setObjectName("wardrobeCharacterPreview")
        self.wardrobe_character_preview.setAlignment(Qt.AlignCenter | Qt.AlignBottom)
        self.wardrobe_character_preview.setMinimumSize(300, 410)
        self.wardrobe_character_preview.setAccessibleName(
            self._t("wardrobe_character_preview", "墨寒造型預覽")
        )
        pose_root = resource_path("assets/pose-atlas/v4-source")
        pose_choices = (
            ("wardrobe_view_front", "正面", pose_root / "yaw+000-pitch+00.png"),
            ("wardrobe_view_left", "左側", pose_root / "yaw-090-pitch+00.png"),
            ("wardrobe_view_right", "右側", pose_root / "yaw+090-pitch+00.png"),
            ("wardrobe_view_back", "背面", pose_root / "yaw-180-pitch+00.png"),
        )
        self._wardrobe_pose_source = QPixmap()
        self.wardrobe_pose_buttons: list[QPushButton] = []
        pose_actions = QHBoxLayout()
        pose_actions.setSpacing(5)
        for key, fallback, path in pose_choices:
            button = QPushButton(self._t(key, fallback))
            button.setCheckable(True)
            button.setProperty("mohanAction", "pose")
            button.clicked.connect(
                partial(self._show_wardrobe_pose, path, button)
            )
            self.wardrobe_pose_buttons.append(button)
            pose_actions.addWidget(button)
        self._show_wardrobe_pose(
            pose_choices[0][2],
            self.wardrobe_pose_buttons[0],
        )
        self.wardrobe_preview_name = QLabel(
            self._t("wardrobe_default_outfit", "內建預設服裝")
        )
        self.wardrobe_preview_name.setAlignment(Qt.AlignCenter)
        self.wardrobe_preview_name.setWordWrap(True)
        self.wardrobe_preview_name.setProperty("mohanRole", "statusPill")
        preview.addWidget(preview_title)
        preview.addWidget(self.wardrobe_character_preview, 1)
        preview.addLayout(pose_actions)
        preview.addWidget(self.wardrobe_preview_name)

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
            self._t("wardrobe_self_generation_enabled", "允許墨寒雲端自創新衣（可能產生費用）")
        )
        self.self_outfit_generation_enabled.setChecked(
            bool(self.db.setting("self_outfit_generation_enabled", False))
        )
        self.fashion_trend_search_enabled = QCheckBox(
            self._t("wardrobe_trend_search_enabled", "允許搜尋流行趨勢作為原創靈感")
        )
        self.fashion_trend_search_enabled.setChecked(
            bool(self.db.setting("fashion_trend_search_enabled", False))
        )
        self.generated_outfit_limit = QSpinBox()
        self.generated_outfit_limit.setRange(1, 64)
        self.generated_outfit_limit.setValue(
            int(self.db.setting("generated_outfit_limit", 16))
        )
        self.generated_outfit_storage_gb = QSpinBox()
        self.generated_outfit_storage_gb.setRange(1, 64)
        self.generated_outfit_storage_gb.setSuffix(" GB")
        self.generated_outfit_storage_gb.setValue(
            int(self.db.setting("generated_outfit_storage_gb", 6))
        )
        actions = QWidget()
        row = QHBoxLayout(actions)
        row.setContentsMargins(0, 0, 0, 0)
        self.wardrobe_import_button = QPushButton(
            self._t("wardrobe_import", "匯入服裝套件")
        )
        self.wardrobe_apply_button = QPushButton(
            self._t("wardrobe_apply", "套用選取服裝")
        )
        self.wardrobe_restore_button = QPushButton(
            self._t("wardrobe_restore_builtin", "還原內建服裝")
        )
        row.addWidget(self.wardrobe_import_button)
        row.addWidget(self.wardrobe_apply_button)
        row.addWidget(self.wardrobe_restore_button)
        library.addWidget(self.wardrobe_packages, 1)
        library.addWidget(self.wardrobe_status)
        library.addWidget(wardrobe_compatibility)
        library.addWidget(source_policy)
        library.addWidget(actions)
        preferences.addWidget(self.autonomous_wardrobe_enabled)
        preferences.addWidget(self.self_outfit_generation_enabled)
        preferences.addWidget(self.fashion_trend_search_enabled)
        limits = QFormLayout()
        limits.addRow(
            self._t("wardrobe_generated_limit", "自創服裝保留上限"),
            self.generated_outfit_limit,
        )
        limits.addRow(
            self._t("wardrobe_storage_limit", "自創服裝容量上限"),
            self.generated_outfit_storage_gb,
        )
        preferences.addLayout(limits)
        preferences.addStretch(1)
        controls = QVBoxLayout()
        controls.setSpacing(12)
        controls.addWidget(library_card, 5)
        controls.addWidget(preferences_card, 4)
        columns.addWidget(preview_card, 6)
        columns.addLayout(controls, 4)
        root.addLayout(columns, 1)
        self.wardrobe_packages.currentItemChanged.connect(
            self._update_wardrobe_preview_name
        )
        self.wardrobe_import_button.clicked.connect(
            self._import_outfit_package
        )
        self.wardrobe_apply_button.clicked.connect(
            self._preview_selected_outfit
        )
        self.wardrobe_restore_button.clicked.connect(
            self._restore_builtin_outfit
        )
        return tab

    def _update_wardrobe_preview_name(
        self,
        current: QListWidgetItem | None,
        _previous: QListWidgetItem | None,
    ) -> None:
        if current is None:
            return
        self.wardrobe_preview_name.setText(current.text())

    def _show_wardrobe_pose(self, path: Path, active: QPushButton) -> None:
        pose = QPixmap(str(path))
        if pose.isNull():
            return
        self._wardrobe_pose_source = pose
        self.wardrobe_character_preview.setPixmap(
            pose.scaled(
                300,
                400,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
        )
        for button in self.wardrobe_pose_buttons:
            button.setChecked(button is active)

    def _save_wardrobe_preferences(self) -> None:
        if not hasattr(self, "autonomous_wardrobe_enabled"):
            return
        self.db.set_setting(
            "autonomous_wardrobe_enabled",
            self.autonomous_wardrobe_enabled.isChecked(),
        )
        self.db.set_setting(
            "self_outfit_generation_enabled",
            self.self_outfit_generation_enabled.isChecked(),
        )
        self.db.set_setting(
            "fashion_trend_search_enabled",
            self.fashion_trend_search_enabled.isChecked(),
        )
        self.db.set_setting(
            "generated_outfit_limit",
            self.generated_outfit_limit.value(),
        )
        self.db.set_setting(
            "generated_outfit_storage_gb",
            self.generated_outfit_storage_gb.value(),
        )

    def _import_outfit_package(self) -> None:
        source, _filter = QFileDialog.getOpenFileName(
            self,
            self._t("wardrobe_import", "匯入服裝套件"),
            str(Path.home() / "Downloads"),
            "MoHan outfit package (*.mohan-outfit *.zip)",
        )
        if not source:
            return
        try:
            self.wardrobe_service.install(Path(source))
        except OutfitPackError:
            self.wardrobe_status.setText(
                self._t(
                    "wardrobe_validator_pending",
                    "套件未通過完整全視角與安全驗證，因此未安裝。",
                )
            )
            return
        self.wardrobe_status.setText(
            self._t("wardrobe_installed_inactive", "已安裝，尚未套用")
        )
        self.wardrobe_packages.clear()
        selected_id = WardrobeService.selected_outfit(
            self.db.setting("active_outfit_id", BUILTIN_OUTFIT_ID)
        )
        for outfit in self.wardrobe_service.outfits(self.ui_language):
            item = QListWidgetItem(outfit.display_name)
            item.setData(Qt.UserRole, outfit.outfit_id)
            self.wardrobe_packages.addItem(item)
            if outfit.outfit_id == selected_id:
                self.wardrobe_packages.setCurrentItem(item)

    def _preview_selected_outfit(self) -> None:
        selected = self.wardrobe_packages.currentItem()
        if selected is None:
            return
        outfit_id = str(selected.data(Qt.UserRole))
        try:
            self.wardrobe_service.apply(outfit_id)
        except OutfitPackError:
            self.wardrobe_status.setText(
                self._t(
                    "wardrobe_assets_pending",
                    "這套服裝未具備完整全視角素材，不能套用。",
                )
            )
            return
        self.db.set_setting("active_outfit_id", outfit_id)
        if outfit_id != BUILTIN_OUTFIT_ID:
            self.db.set_setting(
                "wardrobe_reveal_pending_outfit_id",
                outfit_id,
            )
        self.wardrobe_status.setText(
            self._t("wardrobe_outfit_applied", "已套用所選完整服裝。")
        )

    def _restore_builtin_outfit(self) -> None:
        self.wardrobe_service.apply(BUILTIN_OUTFIT_ID)
        self.db.set_setting("active_outfit_id", BUILTIN_OUTFIT_ID)
        self.db.set_setting("wardrobe_reveal_pending_outfit_id", "")
        for index in range(self.wardrobe_packages.count()):
            item = self.wardrobe_packages.item(index)
            if item.data(Qt.UserRole) == BUILTIN_OUTFIT_ID:
                self.wardrobe_packages.setCurrentItem(item)
                break
        self.wardrobe_status.setText(
            self._t("wardrobe_builtin_applied", "已套用內建預設服裝。")
        )

    def _connect_dashboard_signals(
        self,
        start_button: QPushButton,
        stop_button: QPushButton,
    ) -> None:
        self.mode_combo.currentIndexChanged.connect(
            self._mode_index_changed
        )
        self.tabs.currentChanged.connect(self._tab_changed)
        start_button.clicked.connect(self.start_work)
        stop_button.clicked.connect(self.stop_work)
        self.listener.recognized.connect(self._voice_text)
        self.listener.failed.connect(self._voice_error)
        self.listener.listening_changed.connect(
            self._listening_changed
        )
        self.listener.recording_changed.connect(
            self._recording_changed
        )
        self.listener.status_changed.connect(self.set_voice_phase)
        self.listener.diagnostic_changed.connect(
            self._transcription_diagnostic
        )
        for engine in (self.azure_tts, self.azure_hd_tts):
            catalog_signal = getattr(engine, "voice_catalog_ready", None)
            if catalog_signal is not None:
                catalog_signal.connect(self._apply_azure_voice_catalog)
        self._request_azure_voice_catalog(hd_only=False)
        self._request_azure_voice_catalog(hd_only=True)

    def _start_dashboard_timer(self) -> None:
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh_work_time)
        self.timer.start(1000)

    def _disable_implicit_default_buttons(self) -> None:
        # QDialog otherwise makes the first push button ("開始工作") the
        # implicit Enter key target. Chat submission must never click an
        # unrelated action button.
        for button in self.findChildren(QPushButton):
            button.setAutoDefault(False)
            button.setDefault(False)

    def _t(self, key: str, chinese: str, **values: object) -> str:
        return ui_text(self.ui_language, key, chinese, **values)

    def _settings_text(
        self,
        key: SettingsText,
        **values: object,
    ) -> str:
        return settings_text(self.ui_language, key, **values)

    def _tab_changed(self, index: int) -> None:
        if getattr(self, "_today_split_initialized", False):
            return
        current = self.tabs.widget(index)
        if (
            current is None
            or current.findChild(QSplitter, "todaySplitter")
            is not self.today_splitter
        ):
            return
        QTimer.singleShot(0, self._initialize_today_equal_split)

    def _initialize_today_equal_split(self) -> None:
        if getattr(self, "_today_split_initialized", False):
            return
        available = (
            self.today_splitter.height()
            - self.today_splitter.handleWidth()
        )
        if available <= 20:
            QTimer.singleShot(20, self._initialize_today_equal_split)
            return
        first = available // 2
        self.today_splitter.setSizes([first, available - first])
        self._today_split_initialized = True

    def _apply_profile_texts(self) -> None:
        for widget in self.findChildren(QWidget):
            if isinstance(widget, (QLabel, QPushButton, QCheckBox)):
                template = widget.property("profileTextTemplate")
                if template is None:
                    template = widget.text()
                    widget.setProperty("profileTextTemplate", template)
                widget.setText(personalize_text(self.db, str(template)))
            tooltip = widget.property("profileTooltipTemplate")
            if tooltip is None and widget.toolTip():
                tooltip = widget.toolTip()
                widget.setProperty("profileTooltipTemplate", tooltip)
            if tooltip is not None:
                widget.setToolTip(
                    personalize_text(self.db, str(tooltip))
                )
            if isinstance(widget, QLineEdit):
                placeholder = widget.property(
                    "profilePlaceholderTemplate"
                )
                if placeholder is None and widget.placeholderText():
                    placeholder = widget.placeholderText()
                    widget.setProperty(
                        "profilePlaceholderTemplate", placeholder
                    )
                if placeholder is not None:
                    widget.setPlaceholderText(
                        personalize_text(self.db, str(placeholder))
                    )

    def _bring_to_front(self) -> None:
        if not self.isVisible() or self.isMinimized():
            return
        self.raise_()
        self.activateWindow()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self.visibility_changed.emit(not self.isMinimized())
        self.front_raise_timer.start(0)

    def hideEvent(self, event) -> None:
        self.visibility_changed.emit(False)
        super().hideEvent(event)

    def changeEvent(self, event) -> None:
        super().changeEvent(event)
        if event.type() == QEvent.WindowStateChange:
            self.visibility_changed.emit(
                self.isVisible() and not self.isMinimized()
            )

    def mousePressEvent(self, event: QMouseEvent) -> None:
        self._bring_to_front()
        super().mousePressEvent(event)

    def moveEvent(self, event) -> None:
        super().moveEvent(event)
        # Windows 移動視窗後可能不會觸發 Qt 的 mousePressEvent，再補一次置頂。
        self.front_raise_timer.start(0)

    def refresh_all(self) -> None:
        self.refresh_chat()
        self.refresh_todos()
        self.refresh_ideas()
        self.refresh_memories()
        rows = self.db.platform_rows()
        if {
            row["platform"] for row in rows
        } != set(self.platform_controls):
            self._reload_platform_cards()
            rows = []
        self._platform_loading = True
        try:
            for row in rows:
                self._load_platform_row(row)
        finally:
            self._platform_loading = False
        self._refresh_platform_summary()
        self._filter_platform_cards()
        self.refresh_work_time()

    def apply_profile_from_database(self) -> None:
        """Refresh identity state through one public dashboard boundary."""
        self.assistant_name = profile_setting(
            self.db,
            "assistant_name",
        )
        self.user_title = profile_setting(self.db, "user_title")
        self.organization_name = profile_setting(
            self.db,
            "organization_name",
        )
        title = profile_window_title(self.db)
        self.setWindowTitle(title)
        self._apply_profile_texts()
        self.header_title.setText(f"<b>{html.escape(title)}</b>")

    def consume_expression_metadata(
        self,
        expected_state: str,
    ) -> tuple[str, float, str] | None:
        pending = self.next_expression_metadata
        if pending is None or pending[0] != expected_state:
            return None
        self.next_expression_metadata = None
        return pending

    def capture_explicit_memory(self, text: str) -> None:
        self._capture_explicit_memory(text)

    def reply_expression(self, text: str) -> str:
        return self._reply_expression(text)

    def bring_to_front(self) -> None:
        self._bring_to_front()

    def set_api_status(self, text: str) -> None:
        self.api_status.setText(text)

    def refresh_work_time(self) -> None:
        seconds = self.db.today_work_seconds()
        active = self.db.active_session() is not None
        if active:
            hours, remainder = divmod(seconds, 3600)
            minutes, seconds_part = divmod(remainder, 60)
            total = f"{hours:02d}:{minutes:02d}:{seconds_part:02d}"
        else:
            total = format_duration(seconds, self.ui_language)
        state = self._t(
            "timing_active" if active else "timing_inactive",
            "計時中" if active else "未計時",
        )
        self.work_label.setText(
            self._t(
                "today_time",
                "今日 {total}｜{state}",
                total=total,
                state=state,
            )
        )

    def start_work(self) -> None:
        if self.db.start_work():
            self.speak_requested.emit(
                reminder_line(self.ui_language, "work"),
                "speaking",
            )
            self.work_changed.emit()
            if hasattr(self, "flagship_center"):
                self.flagship_center.work_started()
        else:
            self.speak_requested.emit(
                self._t(
                    "work_timer_already_running",
                    "計時仍在進行，主上不必重複開局。",
                ),
                "idle",
            )
        self.refresh_work_time()

    def stop_work(self) -> None:
        if self.db.stop_work():
            self.speak_requested.emit(
                reminder_line(self.ui_language, "offwork"),
                "happy",
            )
            self.work_changed.emit()
        else:
            self.speak_requested.emit(
                self._t(
                    "work_timer_not_started",
                    "今日尚未開始計時。",
                ),
                "worried",
            )
        self.refresh_work_time()

    def _mode_index_changed(self, index: int) -> None:
        mode = str(self.mode_combo.itemData(index) or "工作")
        self._mode_changed(mode)

    def _mode_changed(self, mode: str) -> None:
        self.mode = mode
        self.db.set_setting("mode", mode)
        if is_english(self.ui_language):
            lines = {
                "工作": "Work mode enabled. I will interrupt only when necessary.",
                "陪伴": "Companion mode enabled. We need not speak of victory tonight.",
                "勿擾": "Do not disturb enabled. I will stay quiet unless it is urgent.",
                "會議": "Meeting mode enabled. I will record only what is necessary.",
                "離席": "Away mode enabled. I will brief you when you return.",
                "休眠": "Sleep mode enabled. Reminders and urgent alerts remain active.",
            }
            self.speak_requested.emit(
                lines.get(
                    mode,
                    f"{display_label(self.ui_language, mode, MODE_LABELS)} "
                    "mode enabled.",
                ),
                "speaking",
            )
            return
        if is_simplified_chinese(self.ui_language):
            lines = {
                "工作": "工作模式已启动。妾只在必要时打断主上。",
                "陪伴": "陪伴模式已启动。今夜不谈胜负，也无妨。",
                "勿擾": "勿扰模式已启动。除紧急事项外，妾不会打断主上。",
                "會議": "会议模式已启动。妾会保持安静，只记录必要事项。",
                "離席": "离席模式已启动。主上回来时，妾再呈上期间摘要。",
                "休眠": "休眠模式已启动。提醒与紧急警报仍会按规则处理。",
            }
            self.speak_requested.emit(
                lines.get(
                    mode,
                    f"{display_label(self.ui_language, mode, MODE_LABELS, SIMPLIFIED_MODE_LABELS)}"
                    "模式已启动。",
                ),
                "speaking",
            )
            return
        if is_japanese(self.ui_language):
            lines = {
                "工作": "仕事モードを開始しました。必要な時だけ主様にお声がけします。",
                "陪伴": "お供モードを開始しました。今宵は勝ち負けを語らずともよいでしょう。",
                "勿擾": "集中モードを開始しました。緊急時以外、妾は静かにしております。",
                "會議": "会議モードを開始しました。静かに、必要なことだけを記録します。",
                "離席": "離席モードを開始しました。お戻りの際に要点をお伝えします。",
                "休眠": "休眠モードを開始しました。リマインダーと緊急通知は規則どおり動きます。",
            }
            self.speak_requested.emit(
                lines.get(
                    mode,
                    f"{display_label(self.ui_language, mode, MODE_LABELS, SIMPLIFIED_MODE_LABELS, JAPANESE_MODE_LABELS)}モードを開始しました。",
                ),
                "speaking",
            )
            return
        lines = {
            "工作": "工作模式已啟。妾只在必要時打斷主上。",
            "陪伴": "陪伴模式已啟。今夜不談勝負，也無妨。",
            "勿擾": "勿擾模式已啟。除緊急事項外，妾不打斷主上。",
            "會議": "會議模式已啟。妾會保持安靜，只記錄必要事項。",
            "離席": "離席模式已啟。主上回來時，妾再呈上期間摘要。",
            "休眠": "休眠模式已啟。妾暫歸劍中，提醒與緊急警報仍照規則處理。",
        }
        line = lines.get(mode, f"{mode}模式已啟。")
        self.speak_requested.emit(line, "speaking")
