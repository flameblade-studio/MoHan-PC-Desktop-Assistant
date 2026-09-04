from __future__ import annotations

lazy import argparse
lazy import os
lazy import shutil
lazy import sys
lazy import tempfile
lazy from pathlib import Path
lazy from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parents[1]
ASSET_DIR = ROOT / "assets"
TESTS = ROOT / "tests"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(TESTS))

lazy from PySide6.QtCore import QPoint, QRect, QSize, Qt, QTimer
lazy from PySide6.QtGui import (
    QColor,
    QFont,
    QImage,
    QLinearGradient,
    QPainter,
    QPen,
    QPixmap,
)
lazy from PySide6.QtWidgets import QApplication

lazy from infrastructure.app_resources import STYLE
lazy from presentation.dashboard_window import Dashboard
lazy from presentation.first_run_wizard import FirstRunWizard
lazy from infrastructure.db import StudioDB
lazy from domain.time_utils import local_wall_time
lazy from test_global_settings_actions import close_dashboard, dependencies
lazy from presentation.lingxiao_widgets import set_motion_override
lazy from tools.capture_media_contract import (
    DASHBOARD_TAB_ALIASES,
    preview_font_family,
    resolve_dashboard_tab,
    select_dashboard_tab,
)
lazy from infrastructure.active_outfit_overlay import ActiveOutfitOverlay
lazy from tools.render_marketing_portraits import render_all, render_portrait

def seed_demo_database(db: StudioDB) -> None:
    settings = {
        "onboarding_complete": True,
        "assistant_name": "墨寒",
        "user_title": "主上",
        "organization_name": "炎劍文化工作室",
        "window_title": "墨寒．炎劍文化工作室",
        "work_type": "創作／出版",
        "wake_word": "墨寒",
        "tts_enabled": False,
        "topmost_mode": "智慧置頂（推薦）",
    }
    for key, value in settings.items():
        db.set_setting(key, value)

    for title, category in (
        ("完成漫畫新章分鏡", "漫畫"),
        ("校對本週專欄文章", "文章"),
        ("整理新曲上架資料", "音樂"),
        ("回覆合作窗口郵件", "行政"),
    ):
        db.add_todo(title, category)

    db.add_idea(
        "雨夜中的赤焰劍",
        "墨寒在雨幕裡聽見劍鳴，轉身看向主上。待補：場景色調與分鏡節奏。",
    )
    db.add_idea(
        "桌面陪伴的微小動作",
        "以眨眼、呼吸、眼神與衣袖擺動呈現安靜而不打擾的陪伴感。",
    )
    seed_demo_memories(db)
    db.log_chat("user", "墨寒，幫我安排今天的工作。")
    db.log_chat(
        "assistant",
        "主上，妾已依優先順序整理妥當。先完成漫畫分鏡，再校對文章與處理上架資料。",
    )
    db.start_work()


def seed_demo_memories(db: StudioDB) -> None:
    """Insert the screenshot fixture without requiring the optional text normalizer."""

    now = local_wall_time().isoformat(timespec="seconds")
    rows = (
        (
            "人物",
            "主要出版窗口",
            "林小姐是主上的主要出版窗口，固定於週一聯絡。",
            "manual",
            5,
        ),
        (
            "偏好",
            "工作順序偏好",
            "主上偏好先完成創作，再集中處理行政事項。",
            "manual",
            4,
        ),
        (
            "目標",
            "公開版本目標",
            "完成墨寒桌面助理的穩定公開版本。",
            "manual",
            5,
        ),
    )
    db.conn.executemany(
        "INSERT INTO memories(category,title,content,source,importance,created_at,updated_at) "
        "VALUES(?,?,?,?,?,?,?) "
        "ON CONFLICT(content) DO UPDATE SET "
        "category=excluded.category,title=excluded.title,source=excluded.source,"
        "importance=MAX(memories.importance,excluded.importance),"
        "updated_at=excluded.updated_at",
        tuple((*row, now, now) for row in rows),
    )
    db.conn.commit()


def grab_widget_image(widget) -> QImage:
    image = widget.grab().toImage().convertToFormat(QImage.Format_ARGB32)
    if image.isNull():
        raise RuntimeError("Could not grab widget image")
    return image


def save_widget(widget, path: Path) -> QImage:
    path.parent.mkdir(parents=True, exist_ok=True)
    image = grab_widget_image(widget)
    if not image.save(str(path)):
        raise RuntimeError(f"Could not save {path}")
    return image


def draw_rounded_panel(
    painter: QPainter,
    rect: QRect,
    fill: QColor,
    border: QColor | None = None,
    radius: int = 22,
) -> None:
    border = border or QColor("#3b7088")
    painter.setPen(QPen(border, 2))
    painter.setBrush(fill)
    painter.drawRoundedRect(rect, radius, radius)


def draw_cover_text(
    painter: QPainter,
    title: str,
    subtitle: str,
    width: int,
) -> None:
    painter.setPen(QColor("#f3fbff"))
    painter.setFont(QFont("Microsoft JhengHei UI", 34, QFont.Bold))
    painter.drawText(QRect(64, 44, width - 128, 58), title)
    painter.setPen(QColor("#a9dff2"))
    painter.setFont(QFont("Microsoft JhengHei UI", 16))
    painter.drawText(QRect(66, 105, width - 132, 34), subtitle)


def scaled_inside(image: QImage, size: QSize) -> QImage:
    normalized = image.copy()
    normalized.setDevicePixelRatio(1.0)
    return normalized.scaled(
        size,
        Qt.KeepAspectRatio,
        Qt.SmoothTransformation,
    )


def compose_hero(
    dashboard: QImage,
    character: QImage,
    output: Path,
) -> None:
    canvas = QImage(1600, 900, QImage.Format_ARGB32)
    canvas.fill(QColor("#eef3f8"))
    painter = QPainter(canvas)
    painter.setRenderHint(QPainter.Antialiasing)
    gradient = QLinearGradient(0, 0, 1600, 900)
    gradient.setColorAt(0.0, QColor("#edf4f8"))
    gradient.setColorAt(0.58, QColor("#f8f9fa"))
    gradient.setColorAt(1.0, QColor("#f8efed"))
    painter.fillRect(canvas.rect(), gradient)
    painter.setPen(QColor("#17344f"))
    painter.setFont(QFont("Microsoft JhengHei UI", 28, QFont.Bold))
    painter.drawText(QRect(55, 40, 1000, 54), "墨寒桌面語音互動虛擬助理")
    painter.setPen(QColor("#48647a"))
    painter.setFont(QFont("Segoe UI", 15))
    painter.drawText(
        QRect(57, 98, 1040, 34),
        "Animated Windows companion · Voice · Memory · Productivity · Safety",
    )

    panel = QRect(55, 175, 1050, 660)
    draw_rounded_panel(
        painter,
        panel,
        QColor("#ffffff"),
        QColor("#b6c8d6"),
        24,
    )
    dash = scaled_inside(dashboard, QSize(1006, 614))
    painter.drawImage(
        QPoint(
            panel.x() + (panel.width() - dash.width()) // 2,
            panel.y() + (panel.height() - dash.height()) // 2,
        ),
        dash,
    )

    character_panel = QRect(1130, 175, 415, 660)
    character_gradient = QLinearGradient(
        character_panel.topLeft(), character_panel.bottomRight()
    )
    character_gradient.setColorAt(0.0, QColor("#fafdff"))
    character_gradient.setColorAt(0.58, QColor("#edf4f8"))
    character_gradient.setColorAt(1.0, QColor("#f8ecef"))
    painter.setPen(QPen(QColor("#b6c8d6"), 2))
    painter.setBrush(character_gradient)
    painter.drawRoundedRect(character_panel, 28, 28)
    char = scaled_inside(character, QSize(405, 575))
    painter.drawImage(
        QPoint(
            character_panel.x() + (character_panel.width() - char.width()) // 2,
            character_panel.y() + 28,
        ),
        char,
    )
    painter.setPen(QColor("#6f4667"))
    painter.setFont(QFont("Microsoft JhengHei UI", 20, QFont.Bold))
    painter.drawText(
        QRect(1145, 678, 385, 44),
        Qt.AlignCenter,
        "北宋千年女劍魂・首席策士",
    )
    painter.setPen(QColor("#62788a"))
    painter.setFont(QFont("Segoe UI", 14))
    painter.drawText(
        QRect(1145, 728, 385, 32),
        Qt.AlignCenter,
        "Voice · Memory · Workflow · Safety",
    )
    painter.end()
    output.parent.mkdir(parents=True, exist_ok=True)
    if not canvas.save(str(output)):
        raise RuntimeError(f"Could not save {output}")


def paint_social_header(painter: QPainter) -> None:
    painter.setPen(QColor("#17344f"))
    painter.setFont(QFont("Microsoft JhengHei UI", 27, QFont.Bold))
    painter.drawText(QRect(48, 34, 820, 50), "墨寒 MoHan Desktop Assistant")
    painter.setPen(QColor("#6f4667"))
    painter.setFont(QFont("Segoe UI", 15, QFont.Bold))
    painter.drawText(
        QRect(50, 87, 820, 30),
        "OPEN-SOURCE WINDOWS DESKTOP COMPANION",
    )


def paint_social_dashboard(painter: QPainter, dashboard: QImage) -> None:
    panel = QRect(48, 142, 805, 356)
    draw_rounded_panel(
        painter,
        panel,
        QColor("#ffffff"),
        QColor("#b6c8d6"),
        22,
    )
    dash = scaled_inside(dashboard, QSize(765, 316))
    painter.drawImage(
        QPoint(
            panel.x() + (panel.width() - dash.width()) // 2,
            panel.y() + (panel.height() - dash.height()) // 2,
        ),
        dash,
    )


def paint_social_character(painter: QPainter, character: QImage) -> None:
    character_panel = QRect(880, 40, 352, 458)
    character_gradient = QLinearGradient(
        character_panel.topLeft(), character_panel.bottomRight()
    )
    character_gradient.setColorAt(0.0, QColor("#fafdff"))
    character_gradient.setColorAt(0.62, QColor("#edf4f8"))
    character_gradient.setColorAt(1.0, QColor("#f8ecef"))
    painter.setPen(QPen(QColor("#b6c8d6"), 2))
    painter.setBrush(character_gradient)
    painter.drawRoundedRect(character_panel, 24, 24)
    char = scaled_inside(character, QSize(340, 395))
    painter.drawImage(
        QPoint(
            character_panel.x() + (character_panel.width() - char.width()) // 2,
            character_panel.y() + 18,
        ),
        char,
    )
    painter.setPen(QColor("#6f4667"))
    painter.setFont(QFont("Microsoft JhengHei UI", 16, QFont.Bold))
    painter.drawText(
        QRect(895, 430, 322, 38),
        Qt.AlignCenter,
        "北宋千年女劍魂・首席策士",
    )


def paint_social_badges(painter: QPainter) -> None:
    badges = (
        ("WINDOWS CI", "VERIFIED"),
        ("SHA256", "CHECKSUM"),
        ("SBOM", "ATTESTED"),
    )
    for index, (title, subtitle) in enumerate(badges):
        badge = QRect(48 + (index * 266), 522, 245, 76)
        painter.setPen(QPen(QColor("#9fb7c9"), 1))
        painter.setBrush(QColor("#ffffff"))
        painter.drawRoundedRect(badge, 16, 16)
        painter.setPen(QColor("#17344f"))
        painter.setFont(QFont("Segoe UI", 13, QFont.Bold))
        painter.drawText(
            QRect(badge.x(), badge.y() + 10, badge.width(), 26),
            Qt.AlignCenter,
            title,
        )
        painter.setPen(QColor("#527188"))
        painter.setFont(QFont("Segoe UI", 10))
        painter.drawText(
            QRect(badge.x(), badge.y() + 38, badge.width(), 22),
            Qt.AlignCenter,
            subtitle,
        )


def paint_social_footer(painter: QPainter) -> None:
    painter.setPen(QColor("#48647a"))
    painter.setFont(QFont("Segoe UI", 13))
    painter.drawText(
        QRect(880, 527, 352, 62),
        Qt.AlignCenter | Qt.TextWordWrap,
        "Python 3.14 · Windows x64\nMIT License · Safety First",
    )


def compose_github_social_preview(
    dashboard: QImage,
    character: QImage,
    output: Path,
) -> None:
    """Build the release/supply-chain visual from the current real UI capture."""
    canvas = QImage(1280, 640, QImage.Format_ARGB32)
    canvas.fill(QColor("#eef3f8"))
    painter = QPainter(canvas)
    painter.setRenderHint(QPainter.Antialiasing)
    background = QLinearGradient(0, 0, 1280, 640)
    background.setColorAt(0.0, QColor("#edf4f8"))
    background.setColorAt(0.62, QColor("#f9fafb"))
    background.setColorAt(1.0, QColor("#f8eeee"))
    painter.fillRect(canvas.rect(), background)
    paint_social_header(painter)
    paint_social_dashboard(painter, dashboard)
    paint_social_character(painter, character)
    paint_social_badges(painter)
    paint_social_footer(painter)
    painter.end()
    output.parent.mkdir(parents=True, exist_ok=True)
    if not canvas.save(str(output)):
        raise RuntimeError(f"Could not save {output}")


def compose_expression_showcase(
    output: Path,
    overlay: ActiveOutfitOverlay,
) -> None:
    cards = (
        ("attentive_front.png", "專注"),
        ("thinking_front.png", "思考"),
        ("gentle_smile_front.png", "溫柔"),
        ("shy_cute_front.png", "嬌羞"),
        ("worried_front.png", "擔心"),
        ("mock_hit_front.png", "佯怒"),
    )
    canvas = QImage(1500, 940, QImage.Format_ARGB32)
    canvas.fill(QColor("#eef3f8"))
    painter = QPainter(canvas)
    painter.setRenderHint(QPainter.Antialiasing)
    background = QLinearGradient(0, 0, 1500, 940)
    background.setColorAt(0.0, QColor("#edf3f8"))
    background.setColorAt(0.58, QColor("#f7f8fa"))
    background.setColorAt(1.0, QColor("#f7f1ed"))
    painter.fillRect(canvas.rect(), background)
    painter.setPen(QColor("#17344f"))
    painter.setFont(QFont("Microsoft JhengHei UI", 26, QFont.Bold))
    painter.drawText(QRect(55, 36, 1390, 48), "墨寒表情系統")
    painter.setPen(QColor("#48647a"))
    painter.setFont(QFont("Microsoft JhengHei UI", 15))
    painter.drawText(
        QRect(56, 88, 1388, 34),
        "情緒仲裁器依語意、狀態與冷卻時間選擇表情；不以隨機誇張表情打擾使用者。",
    )
    card_width, card_height = 440, 330
    for index, (filename, label) in enumerate(cards):
        row, column = divmod(index, 3)
        x = 55 + column * 480
        y = 160 + row * 370
        rect = QRect(x, y, card_width, card_height)
        draw_rounded_panel(
            painter,
            rect,
            QColor("#ffffff"),
            QColor("#b6c8d6"),
            18,
        )
        source = render_portrait(overlay, filename.removesuffix(".png"))
        picture = scaled_inside(source, QSize(300, 268))
        painter.drawImage(
            QPoint(x + (card_width - picture.width()) // 2, y + 8),
            picture,
        )
        painter.setPen(QColor("#20364a"))
        painter.setFont(QFont("Microsoft JhengHei UI", 17, QFont.Bold))
        painter.drawText(QRect(x, y + 285, card_width, 32), Qt.AlignCenter, label)
    painter.end()
    if not canvas.save(str(output)):
        raise RuntimeError(f"Could not save {output}")


def compose_support_portraits(output_dir: Path) -> None:
    """Build fixed-size README portraits through the runtime overlay renderer."""
    render_all(
        ("proud_front", "shy_cute_front", "mock_hit_front"),
        output_dir,
        output_size=(640, 640),
        output_names=(
            "support-proud.png",
            "support-shy-aligned.png",
            "support-mock-hit.png",
        ),
        crop_alpha=True,
        content_size=(600, 590),
        content_offset=(0, 20),
    )


def ffmpeg_binary(explicit: str = "") -> str:
    candidates = [
        explicit,
        os.getenv("FFMPEG_BINARY", ""),
        shutil.which("ffmpeg") or "",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return str(Path(candidate))
    raise RuntimeError("FFmpeg not found. Set FFMPEG_BINARY to ffmpeg.exe.")


def prepare_demo_profile(temp_dir: str) -> None:
    database = StudioDB(Path(temp_dir) / "mohan-zh-TW.db")
    seed_demo_database(database)
    database.close()


def create_capture_app() -> QApplication:
    app = QApplication.instance() or QApplication([])
    app.setFont(QFont(preview_font_family(), 10))
    app.setStyleSheet(STYLE)
    return app


def capture_first_run_wizard(
    app: QApplication,
    temp_dir: str,
    output_dir: Path,
    overlay: ActiveOutfitOverlay,
) -> None:
    wizard_db = StudioDB(Path(temp_dir) / "first-run.db")
    composed_hero = QPixmap.fromImage(render_portrait(overlay, "idle_front"))
    wizard = FirstRunWizard(wizard_db, appearance_pixmap=composed_hero)
    wizard.show()
    app.processEvents()
    save_widget(wizard, output_dir / "first-run-wizard.png")
    wizard.close()
    wizard_db.close()


def create_capture_dashboard(
    app: QApplication,
    temp_dir: str,
    *,
    dependencies_factory=dependencies,
) -> tuple[StudioDB, Dashboard]:
    """Build a dashboard over the prepared demo database without resetting it."""

    set_motion_override(False)
    db = StudioDB(Path(temp_dir) / "mohan-zh-TW.db")
    with patch.object(QTimer, "start", return_value=None):
        dashboard = Dashboard(db, dependencies_factory(Path(temp_dir)))
    dashboard.resize(1400, 900)
    dashboard.show()
    app.processEvents()
    return db, dashboard


def capture_conversation_assets(
    app: QApplication,
    dashboard: Dashboard,
    output_dir: Path,
    overlay: ActiveOutfitOverlay,
) -> QImage:
    conversation = capture_dashboard_tab(
        app,
        dashboard,
        0,
        output_dir / "conversation.png",
    )
    character = representative_character(overlay)
    if not character.save(str(output_dir / "desktop-character.png")):
        raise RuntimeError("Could not save the desktop character preview")
    return conversation


def representative_character(overlay: ActiveOutfitOverlay) -> QImage:
    return render_portrait(overlay, "attentive_front")


def capture_task_assets(
    app: QApplication,
    dashboard: Dashboard,
    output_dir: Path,
    overlay: ActiveOutfitOverlay,
) -> QImage:
    tasks = capture_dashboard_tab(
        app,
        dashboard,
        1,
        output_dir / "tasks-and-ideas.png",
    )
    character = representative_character(overlay)
    compose_hero(tasks, character, output_dir / "mohan-hero.png")
    compose_github_social_preview(
        tasks,
        character,
        output_dir / "github-social-preview.png",
    )
    return tasks


def capture_dashboard_tab(
    app: QApplication,
    dashboard: Dashboard,
    index: int,
    output: Path,
) -> QImage:
    dashboard.tabs.setCurrentIndex(index)
    app.processEvents()
    return save_widget(dashboard, output)


def capture_security_assets(
    app: QApplication,
    dashboard: Dashboard,
    output_dir: Path,
) -> QImage:
    select_dashboard_tab(dashboard, "security")
    app.processEvents()
    return save_widget(dashboard, output_dir / "security-permissions.png")


DASHBOARD_TAB_OUTPUTS = {
    0: "conversation.png",
    1: "tasks-and-ideas.png",
    2: "work-platforms.png",
    3: "long-term-memory.png",
    4: "voice-modes.png",
    5: "security-permissions.png",
    6: "wardrobe.png",
    7: "settings.png",
}


def capture_static_media(
    app: QApplication,
    dashboard: Dashboard,
    output_dir: Path,
    overlay: ActiveOutfitOverlay,
    selected_tab: str | None = None,
) -> dict[str, QImage]:
    if selected_tab is not None:
        index = resolve_dashboard_tab(dashboard, selected_tab)
        image = (
            capture_security_assets(app, dashboard, output_dir)
            if index == DASHBOARD_TAB_ALIASES["security"]
            else capture_dashboard_tab(
                app,
                dashboard,
                index,
                output_dir / DASHBOARD_TAB_OUTPUTS[index],
            )
        )
        return {str(index): image}

    conversation = capture_conversation_assets(app, dashboard, output_dir, overlay)
    tasks = capture_task_assets(app, dashboard, output_dir, overlay)
    memory = capture_dashboard_tab(
        app,
        dashboard,
        3,
        output_dir / "long-term-memory.png",
    )
    voice = capture_dashboard_tab(
        app,
        dashboard,
        4,
        output_dir / "voice-modes.png",
    )
    security = capture_security_assets(app, dashboard, output_dir)
    compose_expression_showcase(output_dir / "expressions.png", overlay)
    compose_support_portraits(output_dir)
    return {
        "hero": conversation,
        "voice": voice,
        "tasks": tasks,
        "memory": memory,
        "security": security,
    }


def maybe_write_demo_video(
    output_dir: Path,
    ffmpeg: str | None,
) -> float | None:
    if not ffmpeg:
        return None
    from tools.record_demo_video import record_demo_video

    narration, _frame_count = record_demo_video(
        output_dir / "mohan-demo.mp4",
        ffmpeg,
    )
    return narration.duration


def capture_media(
    output_dir: Path,
    ffmpeg: str | None,
    selected_tab: str = "all",
) -> float | None:
    output_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="mohan-readme-profile-") as temp_dir:
        os.environ["MOHAN_DATA_DIR"] = temp_dir
        prepare_demo_profile(temp_dir)
        app = create_capture_app()
        overlay = ActiveOutfitOverlay(Path(temp_dir) / "marketing-store", ROOT)
        if selected_tab == "first-run":
            capture_first_run_wizard(app, temp_dir, output_dir, overlay)
            app.processEvents()
            return None
        if selected_tab == "all":
            capture_first_run_wizard(app, temp_dir, output_dir, overlay)
        db, dashboard = create_capture_dashboard(app, temp_dir)
        try:
            capture_static_media(
                app,
                dashboard,
                output_dir,
                overlay,
                None if selected_tab == "all" else selected_tab,
            )
        finally:
            close_dashboard(dashboard, db)
            app.processEvents()
        duration = maybe_write_demo_video(output_dir, ffmpeg)
        return duration


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "docs" / "media",
    )
    parser.add_argument("--ffmpeg", default="")
    parser.add_argument(
        "--tab",
        default="all",
        help=(
            "Capture one dashboard tab by stable name, visible label, or "
            "index; use 'all' for the complete README media set."
        ),
    )
    parser.add_argument(
        "--screenshots-only",
        action="store_true",
        help="Capture current UI images without rebuilding the demo video.",
    )
    args = parser.parse_args()
    selected_tab = args.tab.strip().casefold()
    ffmpeg = (
        None
        if args.screenshots_only or selected_tab != "all"
        else ffmpeg_binary(args.ffmpeg)
    )
    duration = capture_media(args.output, ffmpeg, selected_tab)
    if duration is None:
        print(f"README_SCREENSHOTS_OK output={args.output}")
    else:
        print(f"README_MEDIA_OK duration={duration:.2f}s output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
