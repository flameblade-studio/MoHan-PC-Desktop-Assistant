from __future__ import annotations

import argparse
import base64
import os
import shutil
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "windows")

ROOT = Path(__file__).resolve().parents[1]
ASSET_DIR = ROOT / "assets"
sys.path.insert(0, str(ROOT))

from PySide6.QtCore import QPoint, QRect, QSize, Qt, QTimer
from PySide6.QtGui import (
    QColor,
    QFont,
    QImage,
    QLinearGradient,
    QPainter,
    QPen,
    QPixmap,
)
from PySide6.QtWidgets import QApplication

from app import CompanionWindow, FirstRunWizard
from db import StudioDB


WIDTH = 1280
HEIGHT = 720
FPS = 10
DEMO_TEXT = (
    "墨寒會在工作列上方陪伴你，自然眨眼，並依語音節奏切換嘴型。"
    "一般語音適合按鍵對談，Realtime 模式適合連續自然對話。"
    "工作模式能整理待辦與靈感；長期記憶可逐項檢視、修改或刪除。"
    "所有電腦工具都必須通過本機權限、確認與稽核，模型不能自行取得權限。"
)


def stop_timers(window: CompanionWindow) -> None:
    for timer in window.findChildren(QTimer):
        timer.stop()


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
    db.add_memory(
        "林小姐是主上的主要出版窗口，固定於週一聯絡。",
        "人物",
        "manual",
        5,
        "主要出版窗口",
    )
    db.add_memory(
        "主上偏好先完成創作，再集中處理行政事項。",
        "偏好",
        "manual",
        4,
        "工作順序偏好",
    )
    db.add_memory(
        "完成墨寒桌面助理的穩定公開版本。",
        "目標",
        "manual",
        5,
        "公開版本目標",
    )
    db.log_chat("user", "墨寒，幫我安排今天的工作。")
    db.log_chat(
        "assistant",
        "主上，妾已依優先順序整理妥當。先完成漫畫分鏡，再校對文章與處理上架資料。",
    )
    db.start_work()


def save_widget(widget, path: Path) -> QImage:
    path.parent.mkdir(parents=True, exist_ok=True)
    image = widget.grab().toImage().convertToFormat(QImage.Format_ARGB32)
    if image.isNull() or not image.save(str(path)):
        raise RuntimeError(f"Could not save {path}")
    return image


def draw_rounded_panel(
    painter: QPainter,
    rect: QRect,
    fill: QColor,
    border: QColor = QColor("#3b7088"),
    radius: int = 22,
) -> None:
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
    canvas.fill(QColor("#08141f"))
    painter = QPainter(canvas)
    painter.setRenderHint(QPainter.Antialiasing)
    gradient = QLinearGradient(0, 0, 1600, 900)
    gradient.setColorAt(0.0, QColor("#08131e"))
    gradient.setColorAt(0.55, QColor("#102a3b"))
    gradient.setColorAt(1.0, QColor("#17334a"))
    painter.fillRect(canvas.rect(), gradient)
    draw_cover_text(
        painter,
        "墨寒桌面語音互動虛擬助理",
        "Animated Windows companion · Voice · Memory · Productivity · Safety",
        1600,
    )

    panel = QRect(55, 175, 1050, 660)
    draw_rounded_panel(painter, panel, QColor(11, 29, 43, 236))
    dash = scaled_inside(dashboard, QSize(1006, 614))
    painter.drawImage(
        QPoint(panel.x() + (panel.width() - dash.width()) // 2,
               panel.y() + (panel.height() - dash.height()) // 2),
        dash,
    )

    char = scaled_inside(character, QSize(560, 720))
    painter.drawImage(QPoint(1030, 175), char)
    painter.setPen(QColor("#efb4dc"))
    painter.setFont(QFont("Microsoft JhengHei UI", 21, QFont.Bold))
    painter.drawText(QRect(1120, 785, 410, 44), Qt.AlignCenter, "北宋千年女劍魂・首席策士")
    painter.end()
    output.parent.mkdir(parents=True, exist_ok=True)
    if not canvas.save(str(output)):
        raise RuntimeError(f"Could not save {output}")


def compose_expression_showcase(output: Path) -> None:
    cards = (
        ("attentive_front.png", "專注"),
        ("thinking_front.png", "思考"),
        ("gentle_smile_front.png", "溫柔"),
        ("shy_cute_front.png", "嬌羞"),
        ("worried_front.png", "擔心"),
        ("mock_hit_front.png", "佯怒"),
    )
    canvas = QImage(1500, 940, QImage.Format_ARGB32)
    canvas.fill(QColor("#0a1824"))
    painter = QPainter(canvas)
    painter.setRenderHint(QPainter.Antialiasing)
    draw_cover_text(
        painter,
        "墨寒表情系統",
        "情緒仲裁器依語意、狀態與冷卻時間選擇表情；不以隨機誇張表情打擾使用者。",
        1500,
    )
    card_width, card_height = 440, 330
    for index, (filename, label) in enumerate(cards):
        row, column = divmod(index, 3)
        x = 55 + column * 480
        y = 160 + row * 370
        rect = QRect(x, y, card_width, card_height)
        draw_rounded_panel(painter, rect, QColor("#122838"))
        source = QImage(str(ROOT / "assets" / "expressions" / filename))
        picture = scaled_inside(source, QSize(300, 268))
        painter.drawImage(
            QPoint(x + (card_width - picture.width()) // 2, y + 8),
            picture,
        )
        painter.setPen(QColor("#eaf6fb"))
        painter.setFont(QFont("Microsoft JhengHei UI", 17, QFont.Bold))
        painter.drawText(QRect(x, y + 285, card_width, 32), Qt.AlignCenter, label)
    painter.end()
    if not canvas.save(str(output)):
        raise RuntimeError(f"Could not save {output}")


def synthesize_demo_audio(output: Path) -> float:
    text_encoded = base64.b64encode(DEMO_TEXT.encode("utf-8")).decode("ascii")
    path_encoded = base64.b64encode(str(output).encode("utf-8")).decode("ascii")
    script = (
        "Add-Type -AssemblyName System.Speech;"
        "$s=New-Object System.Speech.Synthesis.SpeechSynthesizer;"
        "$v=$s.GetInstalledVoices()|?{$_.VoiceInfo.Culture.Name -eq 'zh-TW'}|select -First 1;"
        "if(-not $v){$v=$s.GetInstalledVoices()|?{$_.VoiceInfo.Culture.Name -like 'zh-*'}|select -First 1};"
        "if($v){$s.SelectVoice($v.VoiceInfo.Name)};"
        "$s.Rate=-1;"
        f"$t=[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('{text_encoded}'));"
        f"$p=[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('{path_encoded}'));"
        "$s.SetOutputToWaveFile($p);$s.Speak($t);$s.Dispose()"
    )
    encoded = base64.b64encode(script.encode("utf-16le")).decode("ascii")
    result = subprocess.run(
        ["powershell.exe", "-NoProfile", "-EncodedCommand", encoded],
        capture_output=True,
        timeout=120,
    )
    if result.returncode or not output.exists():
        detail = result.stderr.decode("utf-8", errors="replace")[:400]
        raise RuntimeError(detail or "Could not synthesize demo narration")
    with wave.open(str(output), "rb") as audio:
        return audio.getnframes() / audio.getframerate()


def ffmpeg_binary(explicit: str = "") -> str:
    candidates = [explicit, os.getenv("FFMPEG_BINARY", ""), shutil.which("ffmpeg") or ""]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return str(Path(candidate))
    raise RuntimeError("FFmpeg not found. Set FFMPEG_BINARY to ffmpeg.exe.")


def video_scene(second: float, duration: float) -> tuple[str, str, str]:
    progress = second / duration
    if progress < 0.18:
        return "hero", "桌面陪伴", "自然眨眼、呼吸與視線反應"
    if progress < 0.40:
        return "voice", "一般語音模式", "按下麥克風後轉錄、回答並朗讀"
    if progress < 0.58:
        return "voice", "Realtime 自然語音", "連續收音、最終確認轉錄與回音抑制"
    if progress < 0.72:
        return "tasks", "工作模式", "待辦、靈感、工作計時與休息提醒"
    if progress < 0.86:
        return "memory", "可控長期記憶", "逐項分類、編輯、儲存或刪除"
    return "security", "安全權限", "工具執行前經過權限、確認與稽核"


def speech_character_filename(second: float) -> str:
    blink_phase = int(second * 10) % 43
    if blink_phase in (0, 1):
        filename = "blink_front.png"
    else:
        sequence = (
            "attentive_front_speech_mid.png",
            "attentive_front_speech_open.png",
            "attentive_front_speech_mid.png",
            "attentive_front_speech_round.png",
        )
        filename = sequence[int(second * 6.2) % len(sequence)]
    return filename


def write_demo_video(
    media: dict[str, QImage],
    output: Path,
    ffmpeg: str,
) -> float:
    with tempfile.TemporaryDirectory(prefix="mohan-readme-video-") as temp_dir:
        narration = Path(temp_dir) / "narration.wav"
        audio_duration = synthesize_demo_audio(narration)
        duration = 36.0
        frame_count = round(duration * FPS)
        command = [
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-f",
            "rawvideo",
            "-pixel_format",
            "bgra",
            "-video_size",
            f"{WIDTH}x{HEIGHT}",
            "-framerate",
            str(FPS),
            "-i",
            "pipe:0",
            "-i",
            str(narration),
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "25",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            "-movflags",
            "+faststart",
            str(output),
        ]
        process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
        assert process.stdin is not None
        base_cache: dict[tuple[str, str, str], QImage] = {}
        character_names = {
            "attentive_front.png",
            "blink_front.png",
            "attentive_front_speech_mid.png",
            "attentive_front_speech_open.png",
            "attentive_front_speech_round.png",
        }
        character_cache = {
            name: scaled_inside(
                QImage(str(ROOT / "assets" / "expressions" / name)),
                QSize(390, 510),
            )
            for name in character_names
        }
        for frame_index in range(frame_count):
            second = frame_index / FPS
            scene, heading, caption = video_scene(second, duration)
            base_key = (scene, heading, caption)
            if base_key not in base_cache:
                base = QImage(WIDTH, HEIGHT, QImage.Format_ARGB32)
                base_painter = QPainter(base)
                base_painter.setRenderHint(QPainter.Antialiasing)
                gradient = QLinearGradient(0, 0, WIDTH, HEIGHT)
                gradient.setColorAt(0.0, QColor("#07131e"))
                gradient.setColorAt(1.0, QColor("#16354b"))
                base_painter.fillRect(base.rect(), gradient)
                base_painter.setPen(QColor("#f2fbff"))
                base_painter.setFont(
                    QFont("Microsoft JhengHei UI", 27, QFont.Bold)
                )
                base_painter.drawText(
                    QRect(46, 26, 1180, 50),
                    "墨寒桌面語音互動虛擬助理",
                )
                base_painter.setPen(QColor("#f0afd8"))
                base_painter.setFont(
                    QFont("Microsoft JhengHei UI", 21, QFont.Bold)
                )
                base_painter.drawText(QRect(48, 83, 740, 42), heading)
                base_painter.setPen(QColor("#a9dff2"))
                base_painter.setFont(QFont("Microsoft JhengHei UI", 14))
                base_painter.drawText(QRect(49, 126, 760, 32), caption)
                panel = QRect(40, 172, 830, 492)
                draw_rounded_panel(
                    base_painter,
                    panel,
                    QColor(9, 25, 38, 235),
                )
                page = scaled_inside(media[scene], QSize(794, 456))
                base_painter.drawImage(
                    QPoint(
                        panel.x() + (panel.width() - page.width()) // 2,
                        panel.y() + (panel.height() - page.height()) // 2,
                    ),
                    page,
                )
                base_painter.setPen(QColor("#d7edf6"))
                base_painter.setFont(QFont("Microsoft JhengHei UI", 12))
                base_painter.drawText(
                    QRect(883, 642, 350, 30),
                    Qt.AlignCenter,
                    "安全展示資料・不含 API 金鑰與私人內容",
                )
                base_painter.end()
                base_cache[base_key] = base
            frame = base_cache[base_key].copy()
            painter = QPainter(frame)
            painter.setRenderHint(QPainter.Antialiasing)

            speaking = 5.0 < second < min(audio_duration + 0.4, duration - 0.8)
            character_name = (
                speech_character_filename(second)
                if speaking
                else "attentive_front.png"
            )
            painter.drawImage(QPoint(870, 165), character_cache[character_name])
            painter.end()
            # Keep the converted QImage alive while copying its backing store.
            # Calling bits() on a temporary QImage can release the native image
            # before PySide finishes copying and crash with an access violation.
            converted = frame.convertToFormat(QImage.Format_ARGB32)
            raw = converted.bits().tobytes()
            process.stdin.write(raw)
        process.stdin.close()
        stderr = process.stderr.read() if process.stderr else b""
        return_code = process.wait(timeout=120)
        if return_code:
            raise RuntimeError(stderr.decode("utf-8", errors="replace")[-1200:])
        return duration


def capture_media(output_dir: Path, ffmpeg: str | None) -> float | None:
    output_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="mohan-readme-profile-") as temp_dir:
        os.environ["MOHAN_DATA_DIR"] = temp_dir
        database = StudioDB(Path(temp_dir) / "mohan.db")
        seed_demo_database(database)
        database.close()

        app = QApplication.instance() or QApplication([])
        app.setStyleSheet(__import__("app").STYLE)

        wizard_db = StudioDB(Path(temp_dir) / "first-run.db")
        wizard = FirstRunWizard(wizard_db)
        wizard.show()
        app.processEvents()
        save_widget(wizard, output_dir / "first-run-wizard.png")
        wizard.close()
        wizard_db.close()

        window = CompanionWindow(startup_speech=False)
        window.show()
        window.dashboard.show()
        window.dashboard.resize(1400, 900)
        window.dashboard.move(40, 40)
        window.idle_pose = "front"
        window._set_expression("attentive_front", fade=False)
        window.dashboard.mode_combo.setCurrentText("工作")
        # Dashboard construction already loads the seeded profile. Rebuilding
        # the card lists again in the same event turn leaves deleteLater()
        # widgets visible behind their replacements in screenshots.
        app.processEvents()
        stop_timers(window)

        window.dashboard.tabs.setCurrentIndex(0)
        app.processEvents()
        dashboard = save_widget(window.dashboard, output_dir / "conversation.png")
        save_widget(window, output_dir / "desktop-character.png")

        window.dashboard.tabs.setCurrentIndex(1)
        app.processEvents()
        tasks = save_widget(window.dashboard, output_dir / "tasks-and-ideas.png")
        character = QImage(str(ASSET_DIR / "expressions" / "attentive_front.png"))
        if character.isNull():
            raise RuntimeError("Could not load representative character artwork")
        compose_hero(tasks, character, output_dir / "mohan-hero.png")

        window.dashboard.tabs.setCurrentIndex(3)
        app.processEvents()
        memory = save_widget(window.dashboard, output_dir / "long-term-memory.png")

        window.dashboard.tabs.setCurrentIndex(4)
        app.processEvents()
        voice = save_widget(window.dashboard, output_dir / "voice-modes.png")

        window.dashboard.tabs.setCurrentIndex(5)
        flagship = window.dashboard.flagship_center
        flagship.tabs.setCurrentIndex(5)
        app.processEvents()
        security = save_widget(window.dashboard, output_dir / "security-permissions.png")

        compose_expression_showcase(output_dir / "expressions.png")
        media = {
            "hero": dashboard,
            "voice": voice,
            "tasks": tasks,
            "memory": memory,
            "security": security,
        }
        duration = None
        if ffmpeg:
            duration = write_demo_video(
                media,
                output_dir / "mohan-demo.mp4",
                ffmpeg,
            )
        flagship.close_services()
        window.close()
        app.processEvents()
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
        "--screenshots-only",
        action="store_true",
        help="Capture current UI images without rebuilding the demo video.",
    )
    args = parser.parse_args()
    ffmpeg = None if args.screenshots_only else ffmpeg_binary(args.ffmpeg)
    duration = capture_media(args.output, ffmpeg)
    if duration is None:
        print(f"README_SCREENSHOTS_OK output={args.output}")
    else:
        print(f"README_MEDIA_OK duration={duration:.2f}s output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
