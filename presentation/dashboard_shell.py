from __future__ import annotations

lazy import html
lazy from collections import deque
lazy from functools import partial
lazy from pathlib import Path

lazy from PySide6.QtCore import QEvent, Qt, QThreadPool, QTimer
lazy from PySide6.QtGui import QKeySequence, QMouseEvent, QShortcut
lazy from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QFileDialog, QFrame, QHBoxLayout, QLabel,
    QLineEdit, QListWidget, QListWidgetItem, QPushButton, QSizePolicy,
    QSplitter, QTabWidget, QVBoxLayout, QWidget,
)

lazy from application.presentation_ports import (
    PlatformServicePort, PresentationDatabasePort, format_duration,
)
lazy from application.wardrobe_service import BUILTIN_OUTFIT_ID, WardrobeService
lazy from domain.app_profile import (
    personalize_text, profile_setting, profile_window_title,
)
lazy from domain.feature_registry import DashboardFeatureRegistry
lazy from domain.language_support import (
    is_english, is_japanese, is_simplified_chinese,
)
lazy from domain.outfit_pack import IncompatibleBodyProfileError, OutfitPackError
lazy from presentation.companion_platform import reminder_line
lazy from presentation.dashboard_composition import DashboardDependencies
lazy from presentation.dashboard_control_style import enforce_readable_combo_popups
lazy from presentation.dashboard_wardrobe_status import wardrobe_generation_message
lazy from presentation.desktop_companion_status import (
    build_desktop_companion_stage,
    desktop_companion_initial_status,
    gesture_status_message,
    mode_status_label,
    update_desktop_companion_status,
    visual_status_message,
)
lazy from presentation.flagship_theme import (
    create_flagship_ornament,
    mark_flagship_card,
)
lazy from presentation.presentation_resources import STYLE, application_icon
lazy from presentation.settings_ui_localization import SettingsText, settings_text
lazy from presentation.ui_localization import (
    MODE_LABELS,
    SIMPLIFIED_MODE_LABELS,
    display_label,
    ui_text,
)
lazy from presentation.ui_localization_ja import JAPANESE_MODE_LABELS

__all__ = ("DashboardShellMixin",)

MIN_SPLITTER_HEIGHT = 20


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
            # The global transaction emits one final confirmation below.  The
            # nested tool-permission save therefore stays quiet, avoiding two
            # consecutive confirmations for one button press.
            self._saving_all_settings = True
            try:
                self.save_permissions()
            finally:
                self._saving_all_settings = False
            if center is not None and not center.save_draft_settings(center_values):
                raise RuntimeError("Control-center settings were not saved.")
            theme_session = getattr(self, "theme_session", None)
            if theme_session is not None:
                theme_session.save()
            self._save_wardrobe_preferences()
        except Exception:
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
        self._closed = False
        self._ai_generation = 0
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
        self._desktop_companion_status_values = desktop_companion_initial_status(self)
        self._desktop_companion_status_labels: list[dict[str, QLabel]] = []

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
        self.emergency_shortcut.activated.connect(self._emergency_shortcut_activated)

    def _enforce_readable_combo_popups(self) -> None:
        enforce_readable_combo_popups(self)

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
        self.restore_window_button = QPushButton(
            self._t("restore_dashboard_window", "還原視窗")
        )
        self.restore_window_button.setProperty("mohanAction", "secondary")
        self.restore_window_button.setToolTip(
            self._t(
                "restore_dashboard_window_tooltip",
                "將控制中心還原為可移動、可調整大小的視窗",
            )
        )
        self.restore_window_button.clicked.connect(self.showNormal)
        self.restore_window_button.hide()
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
        header.addWidget(self.restore_window_button)
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
        """Place one feature panel beside a live status card for the desktop companion."""

        content = factory()
        content.setProperty("mohanRole", "featureContent")
        page = QWidget()
        page.setProperty("mohanRole", "featurePage")
        page_layout = QHBoxLayout(page)
        page_layout.setContentsMargins(14, 14, 14, 14)
        page_layout.setSpacing(14)

        stage, labels = build_desktop_companion_stage(
            self, self._desktop_companion_status_values
        )
        self._desktop_companion_status_labels.append(labels)

        dock = QFrame()
        dock.setObjectName("featureDock")
        dock.setProperty("mohanRole", "featureDock")
        dock.setMinimumWidth(360)
        dock.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
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
        feature_splitter.setHandleWidth(8)
        feature_splitter.addWidget(stage)
        feature_splitter.addWidget(dock)
        feature_splitter.setStretchFactor(0, 2)
        feature_splitter.setStretchFactor(1, 3)
        feature_splitter.setSizes((360, 640))
        page_layout.addWidget(feature_splitter, 1)
        return page

    def set_desktop_companion_status(self, key: str, value: str) -> None:
        """Reflect the one desktop companion without rendering a duplicate."""

        if key not in self._desktop_companion_status_values:
            return
        self._desktop_companion_status_labels = update_desktop_companion_status(
            self,
            self._desktop_companion_status_values,
            self._desktop_companion_status_labels,
            key,
            value,
        )

    def set_desktop_companion_visual_status(
        self, presence: str, *, active: bool = False
    ) -> None:
        """Present camera activity in the console's current interface language."""

        translation_key, fallback = visual_status_message(
            presence, active=active
        )
        self.set_desktop_companion_status("vision", self._t(translation_key, fallback))

    def set_desktop_companion_gesture_status(self, gesture: str) -> None:
        """Show recognized gestures without leaking untranslated internal labels."""

        translation_key, fallback = gesture_status_message(gesture)
        self.set_desktop_companion_status("gesture", self._t(translation_key, fallback))

    def _wardrobe_tab(self) -> QWidget:
        tab = QWidget()
        root = QVBoxLayout(tab)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(14)
        root.addWidget(self._wardrobe_hero())

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
        self._reload_wardrobe_packages()
        self.wardrobe_status = QLabel(
            self._t("wardrobe_status_ready", "雲裳系統已就緒")
        )
        self.wardrobe_status.setWordWrap(True)
        self.wardrobe_status.setProperty("mohanRole", "statusPill")
        wardrobe_compatibility = QLabel(self._t("wardrobe_compatibility_status", "相容狀態") + "：" + self._t("wardrobe_compatible", "相容"))
        wardrobe_compatibility.setProperty("mohanRole", "muted")
        source_policy = QLabel(
            self._t(
                "wardrobe_source_policy",
                "來源分流：炎劍官方・使用者匯入・墨寒自創",
            )
        )
        source_policy.setWordWrap(True)
        source_policy.setProperty("mohanRole", "muted")

        preview_card = self._wardrobe_preview_card()

        preferences_card = self._wardrobe_preferences_card()
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
        self.wardrobe_generate_button = QPushButton(
            self._t("wardrobe_generate_now", "立即生成新衣（將使用圖片 API）")
        )
        row.addWidget(self.wardrobe_import_button)
        row.addWidget(self.wardrobe_apply_button)
        row.addWidget(self.wardrobe_restore_button)
        row.addWidget(self.wardrobe_generate_button)
        library.addWidget(self.wardrobe_packages, 1)
        library.addWidget(self.wardrobe_status)
        library.addWidget(wardrobe_compatibility)
        library.addWidget(source_policy)
        library.addWidget(actions)
        controls = QVBoxLayout()
        controls.setSpacing(12)
        controls.addWidget(library_card, 5)
        controls.addWidget(self._wardrobe_makeup_card(), 3)
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
        self.wardrobe_generate_button.clicked.connect(
            self._request_outfit_generation
        )
        return tab

    def _request_outfit_generation(self) -> None:
        """Persist explicit consent immediately before the chargeable request."""

        self._save_wardrobe_preferences()
        if not self.self_outfit_generation_enabled.isChecked():
            self.wardrobe_status.setText(
                self._t("wardrobe_generation_not_enabled", "請先勾選允許雲端自創新衣。")
            )
            return
        self.wardrobe_generate_button.setEnabled(False)
        self.wardrobe_status.setText(
            self._t("wardrobe_generation_starting", "正在建立 31 視角新衣並執行安全稽核……")
        )
        self.outfit_generation_requested.emit()

    def set_outfit_generation_status(self, status: str) -> None:
        if not hasattr(self, "wardrobe_status"):
            return
        self.wardrobe_status.setText(wardrobe_generation_message(status, self._t))
        if hasattr(self, "wardrobe_generate_button"):
            self.wardrobe_generate_button.setEnabled(status not in {"generating", "generating-with-trend-search"})
        if status == "body-profile-outdated":
            # The runtime already restored the built-in outfit; keep the saved choice in step so nothing re-applies the stale pack.
            self.db.set_setting("active_outfit_id", BUILTIN_OUTFIT_ID)
        if status in {"installed", "installed-manual-lock", "outfit-selected", "body-profile-outdated"}:
            self._reload_wardrobe_packages()

    def _reload_wardrobe_packages(self) -> None:
        if not hasattr(self, "wardrobe_packages"):
            return
        self.wardrobe_packages.clear()
        selected_id = WardrobeService.selected_outfit(
            self.db.setting("active_outfit_id", BUILTIN_OUTFIT_ID)
        )
        for outfit in self.wardrobe_service.outfits(self.ui_language):
            label = (
                self._t("wardrobe_default_outfit", "內建預設服裝")
                if outfit.built_in
                else outfit.display_name
            )
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, outfit.outfit_id)
            item.setToolTip(
                self._t("wardrobe_compatibility_status", "相容狀態")
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
        self._reload_wardrobe_makeup_options()

    def _wardrobe_hero(self) -> QFrame:
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
        return hero

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
        except IncompatibleBodyProfileError:
            self.wardrobe_status.setText(self._t("wardrobe_body_profile_outdated", "這套服裝是為一代素體製作的，穿在二代素體上會對不準；請用一鍵製衣重新生成"))
            return
        except OutfitPackError:
            self.wardrobe_status.setText(self._t("wardrobe_validator_pending", "套件未通過完整全視角與安全驗證，因此未安裝。"))
            return
        self.wardrobe_status.setText(self._t("wardrobe_installed_inactive", "已安裝，尚未套用"))
        self._reload_wardrobe_packages()

    def _preview_selected_outfit(self) -> None:
        selected = self.wardrobe_packages.currentItem()
        if selected is None:
            return
        outfit_id = str(selected.data(Qt.UserRole))
        try:
            self.wardrobe_service.apply(outfit_id)
        except IncompatibleBodyProfileError:
            self.wardrobe_status.setText(self._t("wardrobe_body_profile_outdated", "這套服裝是為一代素體製作的，穿在二代素體上會對不準；請用一鍵製衣重新生成"))
            return
        except OutfitPackError:
            self.wardrobe_status.setText(self._t("wardrobe_assets_pending", "這套服裝未具備完整全視角素材，不能套用。"))
            return
        self._record_manual_outfit_selection(outfit_id)
        if outfit_id != BUILTIN_OUTFIT_ID:
            self.db.set_setting(
                "wardrobe_reveal_pending_outfit_id",
                outfit_id,
            )
        self.wardrobe_status.setText(
            self._t("wardrobe_outfit_applied", "已套用所選完整服裝。")
        )
        self._reload_wardrobe_makeup_options()
        self._refresh_wardrobe_preview()

    def _restore_builtin_outfit(self) -> None:
        self.wardrobe_service.apply(BUILTIN_OUTFIT_ID)
        self._record_manual_outfit_selection(BUILTIN_OUTFIT_ID)
        self.db.set_setting("wardrobe_reveal_pending_outfit_id", "")
        for index in range(self.wardrobe_packages.count()):
            item = self.wardrobe_packages.item(index)
            if item.data(Qt.UserRole) == BUILTIN_OUTFIT_ID:
                self.wardrobe_packages.setCurrentItem(item)
                break
        self.wardrobe_status.setText(
            self._t("wardrobe_builtin_applied", "已套用內建預設服裝。")
        )
        self._reload_wardrobe_makeup_options()
        self._refresh_wardrobe_preview()

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

    def _disable_implicit_default_buttons(self, root: QWidget | None = None) -> None:
        # QDialog otherwise makes the first push button ("開始工作") the
        # implicit Enter key target. Chat submission must never click an
        # unrelated action button; dynamically rebuilt widgets pass ``root``.
        for button in (self if root is None else root).findChildren(QPushButton):
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
        if available <= MIN_SPLITTER_HEIGHT:
            QTimer.singleShot(MIN_SPLITTER_HEIGHT, self._initialize_today_equal_split)
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
        # A reopened dashboard accepts fresh AI work again; only callbacks of
        # workers submitted before the previous close stay invalidated.
        self._closed = False
        self._sync_restore_window_action()
        self.visibility_changed.emit(not self.isMinimized())
        self.front_raise_timer.start(0)

    def hideEvent(self, event) -> None:
        self.visibility_changed.emit(False)
        super().hideEvent(event)

    def changeEvent(self, event) -> None:
        super().changeEvent(event)
        if event.type() == QEvent.WindowStateChange:
            self._sync_restore_window_action()
            if self.windowState() & Qt.WindowFullScreen:
                # The control centre has no fullscreen workflow.  Refuse an
                # accidental transition that removes the native Windows
                # caption buttons and strands mouse-only users.
                QTimer.singleShot(0, self.showNormal)
            self.visibility_changed.emit(
                self.isVisible() and not self.isMinimized()
            )

    def _sync_restore_window_action(self) -> None:
        button = getattr(self, "restore_window_button", None)
        if button is None:
            return
        state = self.windowState()
        button.setVisible(
            bool(state & (Qt.WindowMaximized | Qt.WindowFullScreen))
        )

    def mousePressEvent(self, event: QMouseEvent) -> None:
        self._bring_to_front()
        super().mousePressEvent(event)

    def moveEvent(self, event) -> None:
        super().moveEvent(event)
        # Windows 移動視窗後可能不會觸發 Qt 的 mousePressEvent，再補一次置頂。
        # 但狀態轉換（最大化／還原／最小化）也走 moveEvent：此時 raise 會與
        # 原生視框更新賽跑成假全螢幕死鎖（v4.5.1 實機回報）——僅一般狀態補。
        if self.windowState() & (
            Qt.WindowMaximized | Qt.WindowMinimized | Qt.WindowFullScreen
        ):
            return
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
        self.set_desktop_companion_status("mode", mode_status_label(self, mode))
        if mode == "休眠":
            # Sleep is an intentional quiet state.  Do not synthesize a
            # confirmation through a fallback provider, which can make the
            # selected companion voice appear to change unexpectedly.
            self.set_api_status(
                self._t(
                    "sleep_mode_status",
                    "休眠模式已啟；墨寒會保持安靜，提醒與緊急警報仍照規則處理。",
                )
            )
            return
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
