from __future__ import annotations

lazy from PySide6.QtCore import Qt
lazy from PySide6.QtGui import QPixmap
lazy from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

lazy from application.presentation_ports import (
    PlatformServicePort,
    PresentationDatabasePort,
    fallback_platform_services,
)
lazy from domain.app_profile import default_persona_for_language, profile_setting
lazy from domain.language_support import (
    is_english,
    is_japanese,
    localized_transcription_prompt,
    localized_voice_instructions,
    transcription_language_for_ui,
)
lazy from domain.speech_configuration import (
    VOICE_ENGINE_OPENAI,
    VOICE_ENGINE_SYSTEM,
    VOICE_GENERATION_PROMPT,
    combo_data_or_custom_text,
)
lazy from presentation.presentation_resources import (
    STYLE,
    application_icon,
    application_ui_font,
    resource_path,
)
lazy from presentation.ui_localization import (
    SIMPLIFIED_WORK_TYPE_LABELS,
    WORK_TYPE_LABELS,
    display_label,
    ui_text,
)
lazy from presentation.ui_localization_ja import JAPANESE_WORK_TYPE_LABELS

__all__ = ("FirstRunWizard",)

class FirstRunWizard(QDialog):
    """Collect identity and workflow choices without assuming one profession."""

    WORK_TYPES = (
        "一般辦公／行政",
        "專案管理",
        "自由工作者／接案",
        "創作／內容工作",
        "軟體開發／技術",
        "教育／研究",
        "銷售／客戶服務",
        "其他（可自行輸入）",
    )

    def __init__(
        self,
        db: PresentationDatabasePort,
        parent=None,
        *,
        platform_services: PlatformServicePort | None = None,
        appearance_pixmap: QPixmap | None = None,
    ):
        super().__init__(parent)
        self.db = db
        self.appearance_pixmap = appearance_pixmap
        self.platform_services = (
            platform_services or fallback_platform_services()
        )
        self.language = profile_setting(db, "ui_language")
        self._configure_window()
        root = QHBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(18)
        root.addWidget(self._build_hero_panel())
        root.addWidget(self._build_content_panel(), 1)
        self.save_button.clicked.connect(self._save)
        self.ui_language.currentIndexChanged.connect(
            self._apply_language
        )
        self._apply_language()

    def _configure_window(self) -> None:
        self.setWindowIcon(application_icon())
        self.setMinimumSize(1100, 720)
        self.setFont(application_ui_font())
        self.setStyleSheet(STYLE)

    def _build_hero_panel(self) -> QFrame:
        hero_panel = QFrame()
        hero_panel.setObjectName("onboardingHero")
        hero_panel.setFixedWidth(360)
        hero_background = resource_path(
            "assets/onboarding/first-run-ink-tech.png"
        ).as_posix()
        hero_panel.setStyleSheet(
            f"""
            QFrame#onboardingHero {{
                border-image: url(\"{hero_background}\") 0 0 0 0 stretch stretch;
                border: 1px solid #aebfcd;
                border-radius: 20px;
            }}
            """
        )
        hero_layout = QVBoxLayout(hero_panel)
        hero_layout.setContentsMargins(16, 24, 16, 14)
        hero_layout.setSpacing(10)
        self.hero_brand = QLabel("墨寒  MoHan")
        self.hero_brand.setObjectName("onboardingBrand")
        self.hero_tagline = QLabel()
        self.hero_tagline.setObjectName("onboardingTagline")
        self.hero_tagline.setWordWrap(True)
        self.hero_image = QLabel()
        self.hero_image.setAlignment(Qt.AlignHCenter | Qt.AlignBottom)
        hero_pixmap = self.appearance_pixmap or QPixmap(
            str(resource_path("assets/expressions/idle_front.png"))
        )
        portrait_width = round(hero_pixmap.width() * 0.62)
        hero_portrait = hero_pixmap.copy(
            (hero_pixmap.width() - portrait_width) // 2,
            0,
            portrait_width,
            hero_pixmap.height(),
        )
        self.hero_image.setPixmap(
            hero_portrait.scaled(
                330,
                520,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
        )
        hero_layout.addWidget(self.hero_brand)
        hero_layout.addWidget(self.hero_tagline)
        hero_layout.addStretch()
        hero_layout.addWidget(self.hero_image)
        return hero_panel

    def _initialize_profile_editors(self) -> None:
        db = self.db
        self.assistant_name = QLineEdit(
            profile_setting(db, "assistant_name")
        )
        self.assistant_name.setPlaceholderText(
            "例如：墨寒、Ava、Office Mate"
        )
        self.user_title = QLineEdit(profile_setting(db, "user_title"))
        self.user_title.setPlaceholderText(
            "助理如何稱呼你，例如：主上、Alex、主管"
        )
        self.organization_name = QLineEdit(
            profile_setting(db, "organization_name")
        )
        self.organization_name.setPlaceholderText(
            "公司、工作室或團隊名稱；個人使用可留空"
        )
        self.window_title = QLineEdit(
            profile_setting(db, "window_title")
        )
        self.window_title.setPlaceholderText(
            "留空時自動顯示「助理名稱．組織名稱」"
        )
        self._initialize_work_type()
        self._initialize_language()
        self.wake_word = QLineEdit(profile_setting(db, "wake_word"))
        self.wake_word.setPlaceholderText(
            "語音喚醒詞，例如：墨寒"
        )

    def _initialize_work_type(self) -> None:
        self.work_type = QComboBox()
        self.work_type.setEditable(True)
        for value in self.WORK_TYPES:
            self.work_type.addItem(
                display_label(
                    self.language,
                    value,
                    WORK_TYPE_LABELS,
                    SIMPLIFIED_WORK_TYPE_LABELS,
                    JAPANESE_WORK_TYPE_LABELS,
                ),
                value,
            )
        saved = profile_setting(self.db, "work_type")
        index = self.work_type.findData(saved)
        if index >= 0:
            self.work_type.setCurrentIndex(index)
        else:
            self.work_type.setCurrentText(saved)

    def _initialize_language(self) -> None:
        self.ui_language = QComboBox()
        self.ui_language.addItem("繁體中文（台灣）", "zh-TW")
        self.ui_language.addItem("简体中文（中国大陆）", "zh-CN")
        self.ui_language.addItem("English", "en")
        self.ui_language.addItem("日本語", "ja-JP")
        current = profile_setting(self.db, "ui_language")
        self.ui_language.setCurrentIndex(
            max(0, self.ui_language.findData(current))
        )

    def _build_profile_form(self) -> QFormLayout:
        self._initialize_profile_editors()
        form = QFormLayout()
        form.setHorizontalSpacing(18)
        form.setVerticalSpacing(12)
        form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.form_labels: dict[str, QLabel] = {}
        fields = (
            ("assistant_name", self.assistant_name),
            ("user_title", self.user_title),
            ("organization_name", self.organization_name),
            ("window_title", self.window_title),
            ("work_type", self.work_type),
            ("ui_language", self.ui_language),
            ("wake_word", self.wake_word),
        )
        for key, editor in fields:
            label = QLabel()
            label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            # Matching label and editor heights prevents mixed-font baseline
            # drift in the commercial onboarding dialog.
            editor.setFixedHeight(50)
            label.setFixedHeight(50)
            self.form_labels[key] = label
            form.addRow(label, editor)
        return form

    def _build_content_panel(self) -> QFrame:
        content_panel = QFrame()
        content_panel.setObjectName("onboardingContent")
        layout = QVBoxLayout(content_panel)
        layout.setContentsMargins(32, 30, 32, 26)
        layout.setSpacing(16)
        self.title_label = QLabel()
        self.title_label.setObjectName("onboardingTitle")
        self.intro_label = QLabel()
        self.intro_label.setWordWrap(True)
        layout.addWidget(self.title_label)
        layout.addWidget(self.intro_label)
        layout.addLayout(self._build_profile_form())
        self.note_label = QLabel()
        self.note_label.setWordWrap(True)
        self.note_label.setObjectName("onboardingNote")
        layout.addWidget(self.note_label)
        layout.addStretch()
        buttons = QHBoxLayout()
        self.save_button = QPushButton()
        buttons.addStretch()
        buttons.addWidget(self.save_button)
        layout.addLayout(buttons)
        return content_panel

    def _t(self, key: str, chinese: str) -> str:
        return ui_text(self.language, key, chinese)

    def _apply_localized_identity_defaults(self) -> None:
        if is_english(self.language):
            replacements = (
                (self.assistant_name, {"墨寒"}, "MoHan"),
                (self.user_title, {"主上", "主様"}, "Commander"),
                (self.wake_word, {"墨寒"}, "MoHan"),
            )
        elif is_japanese(self.language):
            replacements = (
                (self.assistant_name, {"MoHan"}, "墨寒"),
                (self.user_title, {"主上", "Commander"}, "主様"),
                (self.wake_word, {"MoHan"}, "墨寒"),
            )
        else:
            replacements = (
                (self.assistant_name, {"MoHan"}, "墨寒"),
                (self.user_title, {"Commander", "主様"}, "主上"),
                (self.wake_word, {"MoHan"}, "墨寒"),
            )
        for editor, defaults, replacement in replacements:
            if editor.text().strip() in defaults:
                editor.setText(replacement)

    def _apply_language(self, _index: int | None = None) -> None:
        previous = self.language
        self.language = str(self.ui_language.currentData() or "zh-TW")
        if previous != self.language:
            self._apply_localized_identity_defaults()
        self._update_wizard_headings()
        self._update_wizard_form()
        self._update_work_type_labels()
        self.note_label.setText(
            self._t(
                "first_run_note",
                "工作平台頁一開始保持空白，由你自行新增公司系統、"
                "協作工具、客戶後台或網站。程式不會替你建立特定商業平台。",
            )
        )
        self.save_button.setText(
            self._t("finish_setup", "完成設定並開始使用")
        )

    def _update_wizard_headings(self) -> None:
        self.setWindowTitle(self._t("first_run_title", "首次啟動設定"))
        self.hero_brand.setText(self._t("first_run_brand", "墨寒  MoHan"))
        self.hero_tagline.setText(
            self._t(
                "first_run_hero_tagline",
                "北宋千年女劍魂，陪你說話、記憶，也陪你把工作做好。",
            )
        )
        self.title_label.setText(
            self._t(
                "first_run_heading",
                "<b>歡迎使用墨寒桌面陪伴工作助理</b>",
            )
        )
        self.intro_label.setText(
            self._t(
                "first_run_intro",
                "先建立你的使用者設定。以下內容日後都能在「設定」頁修改，"
                "不會綁定特定公司、職業或工作平台。",
            )
        )

    def _update_wizard_form(self) -> None:
        labels = {
            "assistant_name": "助理名稱",
            "user_title": "助理對你的稱呼",
            "organization_name": "公司／團隊名稱",
            "window_title": "完整視窗標題",
            "work_type": "工作類型",
            "ui_language": "介面語言",
            "wake_word": "語音喚醒詞",
        }
        for key, chinese in labels.items():
            self.form_labels[key].setText(self._t(key, chinese))
        self.assistant_name.setPlaceholderText(
            self._t("assistant_name_placeholder", "例如：墨寒、Ava、Office Mate")
        )
        self.user_title.setPlaceholderText(
            self._t(
                "user_title_placeholder",
                "助理如何稱呼你，例如：主上、Alex、主管",
            )
        )
        self.organization_name.setPlaceholderText(
            self._t(
                "organization_placeholder",
                "公司、工作室或團隊名稱；個人使用可留空",
            )
        )
        self.window_title.setPlaceholderText(
            self._t(
                "window_title_placeholder",
                "留空時自動顯示「助理名稱．組織名稱」",
            )
        )
        self.wake_word.setPlaceholderText(
            self._t("wake_word_placeholder", "語音喚醒詞，例如：墨寒")
        )

    def _update_work_type_labels(self) -> None:
        for index, value in enumerate(self.WORK_TYPES):
            self.work_type.setItemText(
                index,
                display_label(
                    self.language,
                    value,
                    WORK_TYPE_LABELS,
                    SIMPLIFIED_WORK_TYPE_LABELS,
                    JAPANESE_WORK_TYPE_LABELS,
                ),
                # Internal data remains Taiwan Traditional Chinese so saved
                # profiles and command rules are language-independent.
            )

    def _save(self) -> None:
        assistant = self.assistant_name.text().strip()
        user_title = self.user_title.text().strip()
        if not assistant or not user_title:
            QMessageBox.information(
                self,
                self._t("required_title", "尚缺必要資料"),
                self._t(
                    "required_identity",
                    "請填寫助理名稱，以及助理對你的稱呼。",
                ),
            )
            return
        values = {
            "assistant_name": assistant,
            "user_title": user_title,
            "organization_name": self.organization_name.text().strip(),
            "window_title": self.window_title.text().strip(),
            "work_type": combo_data_or_custom_text(self.work_type, "其他"),
            "ui_language": str(self.ui_language.currentData() or "zh-TW"),
            "wake_word": self.wake_word.text().strip() or assistant,
            "voice_engine": (
                VOICE_ENGINE_SYSTEM
                if self.platform_services.capabilities.system_local_speech
                else VOICE_ENGINE_OPENAI
            ),
            "onboarding_complete": True,
        }
        for key, value in values.items():
            self.db.set_setting(key, value)
        self.db.set_setting(
            "transcription_language",
            transcription_language_for_ui(values["ui_language"]),
        )
        self.db.set_setting(
            "transcription_prompt",
            localized_transcription_prompt(
                values["ui_language"],
                assistant_name=values["assistant_name"],
                user_title=values["user_title"],
                organization_name=values["organization_name"],
                wake_word=values["wake_word"],
            ),
        )
        self.db.set_setting(
            "voice_instructions",
            localized_voice_instructions(
                values["ui_language"],
                VOICE_GENERATION_PROMPT,
            ),
        )
        self.db.set_setting(
            "persona_prompt",
            default_persona_for_language(values["ui_language"]),
        )
        self.accept()
