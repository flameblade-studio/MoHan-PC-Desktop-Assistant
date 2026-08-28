from __future__ import annotations

lazy import os
lazy import sys
lazy from pathlib import Path

_SOURCE_ROOT = Path(__file__).resolve().parents[1]
if __name__ == "__main__" and not getattr(sys, "frozen", False):
    source_root = str(_SOURCE_ROOT)
    if source_root not in sys.path:
        sys.path.insert(0, source_root)

from application.preview_app import (
    PreviewRuntime,
    parse_preview_arguments,
    validate_preview_runtime,
)
lazy from application.runtime_bootstrap import ensure_default_jit, jit_is_enabled

ensure_default_jit(__name__, __file__)

lazy from PySide6.QtCore import QLocale, Qt
lazy from PySide6.QtGui import QFont, QIcon, QPixmap
lazy from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

lazy from domain.immutable_config import deep_freeze

SUPPORTED_LANGUAGES = ("zh-TW", "zh-CN", "en", "ja-JP")
LANGUAGE_NAMES = frozendict({
    "zh-TW": "繁體中文（台灣）",
    "zh-CN": "简体中文（中国大陆）",
    "en": "English",
    "ja-JP": "日本語",
})

_TEXT = deep_freeze({
    "zh-TW": {
        "window_title": "墨寒桌面陪伴工作助理 — macOS／Linux Preview",
        "badge": "功能受限預覽版",
        "heading": "墨寒已抵達此平台，但仍在整備中",
        "intro": (
            "這個安裝包用來驗證墨寒能在 macOS／Linux 啟動、顯示四語介面，"
            "以及遵守跨平台安全邊界；它不是 Windows 完整版的功能等同版本。"
        ),
        "language": "介面語言",
        "platform": "目前平台",
        "version": "候選版本",
        "verified_title": "此 Preview 已具備",
        "verified": (
            "✓ 原生格式封裝與啟動檢查\n"
            "✓ 繁中、簡中、英文、日文介面\n"
            "✓ 使用者資料路徑與平台能力邊界\n"
            "✓ 不支援能力一律安全停用"
        ),
        "limited_title": "尚未開放的完整能力",
        "limited": (
            "語音輸入與播放、透明桌面角色、完整聊天與工作介面、雲端連接器、"
            "自動啟動、系統工具，以及安全金鑰保存仍待各平台實機驗證。"
        ),
        "security_title": "安全承諾",
        "security": (
            "Preview 不提供 API 金鑰、OAuth 或 Home Assistant 權杖輸入。"
            "在原生安全保存完成前，墨寒不會退回明文保存，也不會假裝功能可用。"
        ),
        "close": "關閉 Preview",
    },
    "zh-CN": {
        "window_title": "墨寒桌面陪伴工作助手 — macOS／Linux Preview",
        "badge": "功能受限预览版",
        "heading": "墨寒已抵达此平台，但仍在整备中",
        "intro": (
            "此安装包用于验证墨寒能在 macOS／Linux 启动、显示四语界面，"
            "并遵守跨平台安全边界；它并不是与 Windows 完整版功能相同的版本。"
        ),
        "language": "界面语言",
        "platform": "当前平台",
        "version": "候选版本",
        "verified_title": "此 Preview 已具备",
        "verified": (
            "✓ 原生格式打包与启动检查\n"
            "✓ 繁中、简中、英文、日文界面\n"
            "✓ 用户数据路径与平台能力边界\n"
            "✓ 不支持的能力一律安全停用"
        ),
        "limited_title": "尚未开放的完整能力",
        "limited": (
            "语音输入与播放、透明桌面角色、完整聊天与工作界面、云端连接器、"
            "自动启动、系统工具及安全密钥保存，仍等待各平台真机验证。"
        ),
        "security_title": "安全承诺",
        "security": (
            "Preview 不提供 API 密钥、OAuth 或 Home Assistant 令牌输入。"
            "原生安全保存完成前，墨寒不会退回明文保存，也不会假装功能可用。"
        ),
        "close": "关闭 Preview",
    },
    "en": {
        "window_title": "MoHan Desktop Assistant — macOS/Linux Preview",
        "badge": "LIMITED PREVIEW",
        "heading": "MoHan has arrived on this platform—carefully",
        "intro": (
            "This package verifies native packaging, startup, four-language UI, "
            "and cross-platform safety boundaries on macOS/Linux. It is not a "
            "feature-parity replacement for the complete Windows application."
        ),
        "language": "Interface language",
        "platform": "Current platform",
        "version": "Candidate version",
        "verified_title": "Included in this Preview",
        "verified": (
            "✓ Native-format package and startup smoke test\n"
            "✓ Traditional Chinese, Simplified Chinese, English, and Japanese\n"
            "✓ Per-user paths and explicit platform capabilities\n"
            "✓ Unsupported capabilities remain safely disabled"
        ),
        "limited_title": "Full capabilities not yet enabled",
        "limited": (
            "Voice input/output, the transparent desktop character, complete "
            "chat and productivity UI, cloud connectors, autostart, system "
            "tools, and secure secret storage still require device validation."
        ),
        "security_title": "Safety promise",
        "security": (
            "This Preview exposes no API-key, OAuth, or Home Assistant token "
            "fields. Until native secure storage is verified, MoHan will not "
            "fall back to plaintext or pretend that protected features work."
        ),
        "close": "Close Preview",
    },
    "ja-JP": {
        "window_title": "墨寒デスクトップアシスタント — macOS／Linux Preview",
        "badge": "機能限定プレビュー",
        "heading": "墨寒はこの環境へ到着しました。現在は慎重に整備中です",
        "intro": (
            "このパッケージは、macOS／Linux での起動、四言語画面、ネイティブ"
            "形式の配布、安全なプラットフォーム境界を確認するものです。"
            "Windows 完全版と同等の機能を提供する版ではありません。"
        ),
        "language": "表示言語",
        "platform": "現在の環境",
        "version": "候補版",
        "verified_title": "この Preview で確認できること",
        "verified": (
            "✓ ネイティブ形式の配布物と起動確認\n"
            "✓ 繁体字中国語・簡体字中国語・英語・日本語\n"
            "✓ 利用者別の保存先と明示的な機能境界\n"
            "✓ 未対応機能を安全に無効化"
        ),
        "limited_title": "まだ有効にしない完全版機能",
        "limited": (
            "音声入出力、透明デスクトップキャラクター、完全な会話・作業画面、"
            "クラウド連携、自動起動、システム操作、安全な秘密情報保存は、"
            "各 OS の実機確認後に段階的に開放します。"
        ),
        "security_title": "安全上の約束",
        "security": (
            "Preview には API キー、OAuth、Home Assistant Token の入力欄を"
            "設けません。安全なネイティブ保存が確認されるまで、平文保存へ"
            "戻したり、保護機能が使えるように見せたりしません。"
        ),
        "close": "Preview を閉じる",
    },
})

_STYLE = """
QMainWindow, QWidget#root {
    background: #f6f1ee;
    color: #24354f;
}
QFrame#heroPanel {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
        stop:0 #dcebf2, stop:0.52 #f1e9ec, stop:1 #efe5d4);
    border: 1px solid #d7c9c3;
    border-radius: 26px;
}
QFrame#contentPanel {
    background: rgba(255, 255, 255, 235);
    border: 1px solid #d9dfe7;
    border-radius: 26px;
}
QLabel#badge {
    background: #294f70;
    color: white;
    border-radius: 12px;
    padding: 6px 12px;
    font-weight: 800;
}
QLabel#heading { color: #1e3a59; font-size: 28px; font-weight: 800; }
QLabel#intro { color: #526176; font-size: 16px; }
QLabel#sectionTitle { color: #7a4f61; font-size: 17px; font-weight: 800; }
QLabel#body { color: #3f4e62; font-size: 15px; }
QLabel#meta { color: #405b75; font-size: 14px; font-weight: 700; }
QComboBox {
    min-height: 42px;
    padding: 4px 12px;
    border: 2px solid #afbfcd;
    border-radius: 10px;
    background: white;
    color: #263b56;
    font-size: 15px;
}
QPushButton {
    min-height: 44px;
    border: 0;
    border-radius: 12px;
    background: #315c7d;
    color: white;
    font-size: 15px;
    font-weight: 800;
    padding: 0 20px;
}
QPushButton:hover { background: #254b69; }
"""


def resource_path(relative: str) -> Path:
    source_root = Path(__file__).resolve().parents[1]
    base = Path(getattr(sys, "_MEIPASS", source_root))
    return base / relative


def default_language() -> str:
    name = (os.environ.get("LANG") or QLocale.system().name()).lower()
    if name.startswith(("zh_cn", "zh_sg")):
        return "zh-CN"
    if name.startswith("ja"):
        return "ja-JP"
    if name.startswith("en"):
        return "en"
    return "zh-TW"


class PreviewWindow(QMainWindow):
    def __init__(
        self,
        runtime: PreviewRuntime | None = None,
        *,
        language: str | None = None,
    ) -> None:
        super().__init__()
        self.runtime = runtime or PreviewRuntime.current()
        self.language = (
            language if language in SUPPORTED_LANGUAGES else default_language()
        )
        self.setMinimumSize(980, 650)

        root = QWidget(objectName="root")
        layout = QHBoxLayout(root)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(22)
        layout.addWidget(self._build_hero_panel(), 4)
        layout.addWidget(self._build_content_panel(), 6)

        self.setCentralWidget(root)
        self.setStyleSheet(_STYLE)
        self.setWindowIcon(
            QIcon(str(resource_path("installer/artwork/wizard-small.png")))
        )
        self.apply_language(self.language)

    @staticmethod
    def _build_hero_panel() -> QFrame:
        hero_panel = QFrame(objectName="heroPanel")
        hero_layout = QVBoxLayout(hero_panel)
        hero_layout.setContentsMargins(20, 20, 20, 20)
        hero = QLabel(alignment=Qt.AlignmentFlag.AlignCenter)
        pixmap = QPixmap(str(resource_path("installer/artwork/wizard-hero.png")))
        if not pixmap.isNull():
            hero.setPixmap(
                pixmap.scaled(
                    360,
                    590,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
        hero_layout.addWidget(hero, 1)
        return hero_panel

    def _build_content_panel(self) -> QFrame:
        content_panel = QFrame(objectName="contentPanel")
        content = QVBoxLayout(content_panel)
        content.setContentsMargins(34, 30, 34, 28)
        content.setSpacing(12)

        self.badge = QLabel(objectName="badge")
        self.heading = QLabel(objectName="heading", wordWrap=True)
        self.intro = QLabel(objectName="intro", wordWrap=True)
        content.addWidget(self.badge, 0, Qt.AlignmentFlag.AlignLeft)
        content.addWidget(self.heading)
        content.addWidget(self.intro)

        self.language_label = QLabel(objectName="meta")
        self.language_selector = QComboBox()
        for code in SUPPORTED_LANGUAGES:
            self.language_selector.addItem(LANGUAGE_NAMES[code], code)
        self.language_selector.setCurrentIndex(
            self.language_selector.findData(self.language)
        )
        self.language_selector.currentIndexChanged.connect(self._language_changed)
        content.addWidget(self.language_label)
        content.addWidget(self.language_selector)

        self.meta = QLabel(objectName="meta", wordWrap=True)
        content.addWidget(self.meta)

        self.verified_title = QLabel(objectName="sectionTitle")
        self.verified = QLabel(objectName="body", wordWrap=True)
        self.limited_title = QLabel(objectName="sectionTitle")
        self.limited = QLabel(objectName="body", wordWrap=True)
        self.security_title = QLabel(objectName="sectionTitle")
        self.security = QLabel(objectName="body", wordWrap=True)
        for widget in (
            self.verified_title,
            self.verified,
            self.limited_title,
            self.limited,
            self.security_title,
            self.security,
        ):
            content.addWidget(widget)
        content.addStretch(1)

        self.close_button = QPushButton()
        self.close_button.clicked.connect(self.close)
        content.addWidget(self.close_button, 0, Qt.AlignmentFlag.AlignRight)
        return content_panel

    def _language_changed(self) -> None:
        language = str(self.language_selector.currentData())
        self.apply_language(language)

    def apply_language(self, language: str) -> None:
        if language not in SUPPORTED_LANGUAGES:
            raise ValueError(f"Unsupported preview language: {language}")
        self.language = language
        text = _TEXT[language]
        self.setWindowTitle(text["window_title"])
        self.badge.setText(text["badge"])
        self.heading.setText(text["heading"])
        self.intro.setText(text["intro"])
        self.language_label.setText(text["language"])
        self.meta.setText(
            f"{text['platform']}: {self.runtime.platform_name} "
            f"({self.runtime.architecture})   ・   "
            f"{text['version']}: {self.runtime.version}"
        )
        self.verified_title.setText(text["verified_title"])
        self.verified.setText(text["verified"])
        self.limited_title.setText(text["limited_title"])
        self.limited.setText(text["limited"])
        self.security_title.setText(text["security_title"])
        self.security.setText(text["security"])
        self.close_button.setText(text["close"])


def validate_preview_contract(window: PreviewWindow) -> None:
    validate_preview_runtime(window.runtime)
    required_keys = frozenset(_TEXT["zh-TW"])
    for language in SUPPORTED_LANGUAGES:
        if frozenset(_TEXT[language]) != required_keys:
            raise RuntimeError(f"Incomplete Preview translation: {language}")
        window.apply_language(language)
        if not window.windowTitle() or not window.heading.text():
            raise RuntimeError(f"Preview rendering failed: {language}")


def main(argv: list[str] | None = None) -> int:
    values = sys.argv[1:] if argv is None else argv
    args = parse_preview_arguments(values)
    if args.jit_status_output:
        args.jit_status_output.write_text(
            "PACKAGED_JIT_DEFAULT_OK"
            if jit_is_enabled()
            else "PACKAGED_JIT_DEFAULT_FAILED",
            encoding="utf-8",
        )
    if args.preview_smoke_output:
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
    runtime = PreviewRuntime.current(args.preview_platform)
    app = QApplication([sys.argv[0]])
    app.setApplicationName("MoHan Desktop Assistant Preview")
    app.setApplicationVersion(runtime.version)
    app.setFont(QFont("Noto Sans", 11))
    window = PreviewWindow(runtime)

    if args.preview_smoke_output:
        args.preview_smoke_output.parent.mkdir(parents=True, exist_ok=True)
        try:
            validate_preview_contract(window)
            if runtime.version != args.preview_expected_version:
                raise RuntimeError(
                    "Preview package version mismatch: "
                    f"expected {args.preview_expected_version}, got {runtime.version}"
                )
        except Exception:
            args.preview_smoke_output.write_text(
                "PREVIEW_PACKAGE_SMOKE_FAILED", encoding="utf-8"
            )
            window.close()
            return 2
        args.preview_smoke_output.write_text(
            "PREVIEW_PACKAGE_SMOKE_OK", encoding="utf-8"
        )
        window.close()
        app.processEvents()
        return 0

    window.show()
    return app.exec()


__all__ = (
    "LANGUAGE_NAMES",
    "SUPPORTED_LANGUAGES",
    "_STYLE",
    "_TEXT",
    "PreviewRuntime",
    "PreviewWindow",
    "default_language",
    "main",
    "resource_path",
    "validate_preview_contract",
)


if __name__ == "__main__":
    raise SystemExit(main())
