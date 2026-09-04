"""凌霄殼層：導覽軌（四組＋組名）、狀態緞帶、草稿動作列、大廳動效。

dashboard_shell.py 只保留行為與訊號接線；這裡負責「長什麼樣、排在哪裡」。
八個功能頁不動，導覽軌分四組，每組上方一個小小的組名：

    陪伴：對話、聲音        事務：今日待辦、工作平台、長期記憶
    裝扮：雲裳閣            系統：電腦權限、設定

組名用白話（不用「機關」這種要猜的詞），字級小、色淡、不可點；
按鈕有底、有框、字大且亮——一眼就分得出哪個能按（擁有者 09-02 實測回饋）。
組名不與按鈕文字重複（「雲裳閣／雲裳閣」那種疊字擁有者已兩次退件）。

`game_navigation_buttons` 的順序仍與分頁索引一致（第 i 顆按鈕開第 i 頁），
版面順序與清單順序分開——測試與鍵盤走訪靠清單，眼睛靠版面。
"""
from __future__ import annotations

lazy import html
lazy from functools import partial

lazy from PySide6.QtCore import Qt
lazy from PySide6.QtGui import QPixmap
lazy from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
)

lazy from presentation.flagship_theme import create_flagship_ornament
lazy from presentation.lingxiao_themes import palette_for_theme
lazy from presentation.lingxiao_widgets import (
    MotesLayer,
    PageTransition,
    PulseDot,
    StateChip,
)
lazy from presentation.presentation_resources import resource_path
lazy from domain.app_profile import profile_window_title

__all__ = (
    "REALMS",
    "build_draft_bar",
    "build_navigation",
    "build_ribbon",
    "install_lobby_motion",
    "refresh_runtime_palette",
    "realm_layout_order",
    "DRAFT_BAR_READ_ERROR",
    "update_draft_bar",
)

DRAFT_BAR_READ_ERROR = "error"


def _shell_palette(shell):
    theme_id = getattr(shell, "_runtime_lingxiao_theme_id", None)
    if theme_id is None:
        theme_id = shell.db.setting("flagship_theme", "ink-gold")
    high_contrast = getattr(shell, "_runtime_lingxiao_high_contrast", None)
    if high_contrast is None:
        high_contrast = shell.db.setting("flagship_high_contrast", False)
    return palette_for_theme(
        theme_id,
        high_contrast=bool(high_contrast),
    )

# (領域鍵, 繁中預設組名, 這一組收哪些功能 id)。功能 id 對應 DashboardFeatureRegistry。
REALMS = (
    ("companion", "陪伴", ("chat", "voice")),
    ("today", "事務", ("today", "platforms", "memory")),
    ("wardrobe", "裝扮", ("wardrobe",)),
    ("machine", "系統", ("permissions", "settings")),
)
NAVIGATION_WIDTH = 124
_LOBBY_BACKDROP = resource_path("assets/ui/mohan-strategist-lobby-v1.png")


def realm_layout_order(feature_ids: tuple[str, ...]) -> tuple[tuple[str, tuple[int, ...]], ...]:
    """把功能索引依領域分組，回傳 ((領域鍵, (索引…)), …)。

    不在任何領域裡的功能（未來新增的分頁）落到最後一個「其他」群，不會消失。
    """

    grouped: list[tuple[str, tuple[int, ...]]] = []
    seen: set[int] = set()
    for realm_key, _label, members in REALMS:
        indexes = tuple(
            index for index, feature_id in enumerate(feature_ids) if feature_id in members
        )
        if indexes:
            grouped.append((realm_key, indexes))
            seen.update(indexes)
    leftovers = tuple(index for index in range(len(feature_ids)) if index not in seen)
    if leftovers:
        grouped.append(("other", leftovers))
    return tuple(grouped)


def _realm_caption(shell, realm_key: str) -> str:
    """組名一律用字面鍵呼叫 _t，讓本地化完整性測試看得到每一個鍵。"""

    if realm_key == "companion":
        return shell._t("nav_realm_companion", "陪伴")
    if realm_key == "today":
        return shell._t("nav_realm_today", "事務")
    if realm_key == "wardrobe":
        return shell._t("nav_realm_wardrobe", "裝扮")
    if realm_key == "machine":
        return shell._t("nav_realm_machine", "系統")
    return shell._t("nav_realm_other", "其他")


def build_navigation(shell, features) -> tuple[QFrame, list[QPushButton]]:
    """建導覽軌。回傳 (框, 依分頁索引排序的按鈕清單)。"""

    navigation = QFrame()
    navigation.setProperty("mohanRole", "gameNavigation")
    navigation.setFixedWidth(NAVIGATION_WIDTH)
    layout = QVBoxLayout(navigation)
    layout.setContentsMargins(8, 14, 8, 14)
    layout.setSpacing(6)
    title = QLabel(shell._t("navigation_brand", "墨寒"))
    title.setAlignment(Qt.AlignCenter)
    title.setProperty("mohanRole", "navigationTitle")
    layout.addWidget(title)
    layout.addWidget(create_flagship_ornament(navigation, size=52), 0, Qt.AlignCenter)

    buttons: list[QPushButton | None] = [None] * len(features)
    feature_ids = tuple(feature.feature_id for feature in features)
    for group_number, (realm_key, indexes) in enumerate(realm_layout_order(feature_ids)):
        caption = QLabel(_realm_caption(shell, realm_key))
        caption.setProperty("mohanRole", "navRealm")
        caption.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        caption.setFocusPolicy(Qt.NoFocus)
        layout.addSpacing(10 if group_number else 2)
        layout.addWidget(caption)
        for index in indexes:
            feature = features[index]
            button = QPushButton(feature.title)
            button.setCheckable(True)
            button.setAutoExclusive(True)
            button.setProperty("mohanAction", "navigation")
            button.setAccessibleName(feature.title)
            button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            button.clicked.connect(partial(shell._select_game_lobby_page, index))
            layout.addWidget(button)
            buttons[index] = button
    layout.addStretch(1)
    ordered = [button for button in buttons if button is not None]
    return navigation, ordered


def build_ribbon(shell, root: QVBoxLayout) -> tuple[QPushButton, QPushButton]:
    """頂部狀態緞帶：品牌、模式、狀態燈＋計時、開始／結束。"""

    deck = QFrame()
    deck.setProperty("mohanRole", "commandDeck")
    header = QHBoxLayout(deck)
    header.setContentsMargins(16, 8, 14, 8)
    header.setSpacing(12)
    shell.mode_combo = shell._build_mode_combo()
    shell.work_label = QLabel()
    shell.work_label.setProperty("mohanRole", "headerStatus")
    start_button = QPushButton(shell._t("start_work", "開始工作"))
    stop_button = QPushButton(shell._t("stop_work", "結束工作"))
    shell.restore_window_button = QPushButton(shell._t("restore_dashboard_window", "還原視窗"))
    shell.restore_window_button.setProperty("mohanAction", "secondary")
    shell.restore_window_button.setToolTip(
        shell._t("restore_dashboard_window_tooltip", "將控制中心還原為可移動、可調整大小的視窗")
    )
    shell.restore_window_button.clicked.connect(shell.showNormal)
    shell.restore_window_button.hide()
    start_button.setProperty("mohanAction", "primary")
    stop_button.setProperty("mohanAction", "secondary")

    brand = QVBoxLayout()
    brand.setSpacing(0)
    shell.header_title = QLabel(f"<b>{html.escape(profile_window_title(shell.db))}</b>")
    shell.header_title.setProperty("mohanRole", "brand")
    brand_line = QLabel(shell._t("dashboard_brand_line", "墨色為骨・寒光為心"))
    brand_line.setProperty("mohanRole", "muted")
    brand.addWidget(shell.header_title)
    brand.addWidget(brand_line)

    palette = _shell_palette(shell)
    shell.ribbon_pulse = PulseDot(palette.jade, deck)
    header.addWidget(create_flagship_ornament(shell, size=44))
    header.addLayout(brand)
    header.addStretch()
    header.addWidget(QLabel(shell._t("mode", "模式")))
    header.addWidget(shell.mode_combo)
    header.addWidget(shell.ribbon_pulse)
    header.addWidget(shell.work_label)
    header.addWidget(shell.restore_window_button)
    header.addWidget(start_button)
    header.addWidget(stop_button)
    root.addWidget(deck)
    return start_button, stop_button


def build_draft_bar(shell, root: QVBoxLayout) -> None:
    """草稿動作列：取代漂浮在右下角的「取消／保存」。

    左邊是狀態晶片與一句話，右邊是還原與套用。按鈕的 objectName、訊號與
    文字鍵都與以前相同，行為層零改動。
    """

    bar = QFrame()
    bar.setProperty("mohanRole", "commandFooter")
    row = QHBoxLayout(bar)
    row.setContentsMargins(14, 8, 12, 8)
    row.setSpacing(12)
    shell.draft_chip = StateChip(shell._t("draft_bar_clean", "已套用"), "ok")
    shell.draft_message = QLabel(shell._t("draft_bar_clean_message", "設定與目前執行中的狀態一致"))
    shell.draft_message.setProperty("mohanRole", "muted")
    shell.cancel_settings_button = QPushButton(shell._t("cancel_without_saving", "取消（不要保存）"))
    shell.cancel_settings_button.setObjectName("globalCancelSettingsButton")
    shell.cancel_settings_button.setProperty("mohanAction", "secondary")
    shell.save_settings_button = QPushButton(shell._t("save_settings", "保存設定"))
    shell.save_settings_button.setObjectName("globalSaveSettingsButton")
    shell.save_settings_button.setProperty("mohanPrimaryAction", True)
    shell.save_settings_button.setProperty("mohanAction", "primary")
    palette = _shell_palette(shell)
    _style_save_settings_button(shell.save_settings_button, palette)

    row.addWidget(shell.draft_chip)
    row.addWidget(shell.draft_message, 1)
    row.addWidget(shell.cancel_settings_button)
    row.addWidget(shell.save_settings_button)
    root.addWidget(bar)
    shell.cancel_settings_button.clicked.connect(shell.cancel_settings_changes)
    shell.save_settings_button.clicked.connect(shell.save_all_settings)


def _style_save_settings_button(button: QPushButton, palette) -> None:
    button.setStyleSheet(
        "QPushButton#globalSaveSettingsButton{"
        f"background:{palette.gold};color:{palette.on_gold};border:1px solid {palette.gold_2};"
        "border-radius:10px;font-weight:700;padding:10px 24px;}"
        "QPushButton#globalSaveSettingsButton:hover{"
        f"background:{palette.gold_2};color:{palette.on_gold};}}"
    )


def refresh_runtime_palette(shell, *, active: bool) -> None:
    """Refresh custom shell widgets from the dashboard's cached palette."""

    palette = _shell_palette(shell)
    pulse = getattr(shell, "ribbon_pulse", None)
    if pulse is not None:
        pulse.set_color(palette.jade if active else palette.dim)
    save_button = getattr(shell, "save_settings_button", None)
    if save_button is not None:
        _style_save_settings_button(save_button, palette)
    motes = getattr(shell, "lobby_motes", None)
    if motes is not None:
        motes.set_palette(palette)


def update_draft_bar(shell) -> int | str:
    """比對設定快照，回傳未套用的變更數並更新晶片與訊息。"""

    chip = getattr(shell, "draft_chip", None)
    if chip is None:
        return 0
    try:
        baseline = shell._settings_draft_snapshot
        current = shell.db.settings_snapshot()
    except Exception:  # 資料庫暫時讀不到：讓晶片明確顯示錯誤
        chip.setText(shell._t("draft_bar_error", "讀取失敗"))
        chip.set_state("bad")
        shell.draft_message.setText(
            shell._t(
                "draft_bar_error_message",
                "設定無法讀取，請稍後再試",
            )
        )
        return DRAFT_BAR_READ_ERROR
    changed = 0
    keys = set(baseline) | set(current)
    for key in keys:
        if baseline.get(key) != current.get(key):
            changed += 1
    if changed:
        chip.setText(shell._t("draft_bar_dirty", "草稿"))
        chip.set_state("gold")
        shell.draft_message.setText(
            shell._t("draft_bar_dirty_message", "你有 {count} 項未套用的變更", count=changed)
        )
    else:
        chip.setText(shell._t("draft_bar_clean", "已套用"))
        chip.set_state("ok")
        shell.draft_message.setText(
            shell._t("draft_bar_clean_message", "設定與目前執行中的狀態一致")
        )
    return changed


def set_ribbon_state(shell, *, active: bool) -> None:
    """狀態燈：計時中玉青、未計時薄霧。顏色是狀態，呼吸是活著。"""

    pulse = getattr(shell, "ribbon_pulse", None)
    if pulse is None:
        return
    palette = _shell_palette(shell)
    pulse.set_color(palette.jade if active else palette.dim)


def install_lobby_motion(shell, lobby: QFrame, tabs) -> None:
    """大廳底層金塵與切頁過場。重複呼叫是安全的。"""

    if getattr(shell, "lobby_motes", None) is None:
        palette = _shell_palette(shell)
        shell.lobby_motes = MotesLayer(lobby, QPixmap(str(_LOBBY_BACKDROP)), palette)
        shell.lobby_motes.show()
    if getattr(shell, "page_transition", None) is None:
        shell.page_transition = PageTransition(tabs)
