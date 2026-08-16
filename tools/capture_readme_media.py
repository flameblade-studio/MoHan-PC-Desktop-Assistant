from __future__ import annotations

lazy import argparse
lazy import base64
lazy import os
lazy import shutil
lazy import subprocess
lazy import sys
lazy import tempfile
lazy import wave
lazy from dataclasses import dataclass
lazy from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "windows")

ROOT = Path(__file__).resolve().parents[1]
ASSET_DIR = ROOT / "assets"
sys.path.insert(0, str(ROOT))

lazy from PySide6.QtCore import QPoint, QRect, QSize, Qt, QTimer
lazy from PySide6.QtGui import (
    QColor,
    QFont,
    QImage,
    QLinearGradient,
    QPainter,
    QPen,
)
lazy from PySide6.QtWidgets import QApplication

lazy from companion_window import CompanionWindow
lazy from first_run_wizard import FirstRunWizard
lazy from infrastructure.db import StudioDB

WIDTH = 1280
HEIGHT = 720
FPS = 10
DEMO_TEXT = (
    "墨寒會在工作列上方陪伴你，自然眨眼，並依語音節奏切換嘴型。"
    "一般語音適合按鍵對談，Realtime 模式適合連續自然對話。"
    "工作模式能整理待辦與靈感；長期記憶可逐項檢視、修改或刪除。"
    "所有電腦工具都必須通過本機權限、確認與稽核，模型不能自行取得權限。"
)


@dataclass(frozen=True, slots=True)
class VideoTiming:
    duration: float
    audio_duration: float


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
        source = QImage(str(ROOT / "assets" / "expressions" / filename))
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


def _alpha_bounds(image: QImage) -> QRect:
    rgba = image.convertToFormat(QImage.Format.Format_RGBA8888)
    data = bytes(rgba.constBits())
    stride = rgba.bytesPerLine()
    left, top = rgba.width(), rgba.height()
    right = bottom = -1
    for y in range(rgba.height()):
        row = y * stride
        for x in range(rgba.width()):
            if data[row + x * 4 + 3]:
                left = min(left, x)
                top = min(top, y)
                right = max(right, x)
                bottom = max(bottom, y)
    if right < left or bottom < top:
        raise RuntimeError("Expression artwork has no visible pixels")
    return QRect(left, top, right - left + 1, bottom - top + 1)


def compose_support_portraits(output_dir: Path) -> None:
    """Build aligned README portraits without changing in-app expression assets."""
    output_dir.mkdir(parents=True, exist_ok=True)
    portraits = {
        "support-proud.png": "proud_front.png",
        "support-shy-aligned.png": "shy_cute_front.png",
        "support-mock-hit.png": "mock_hit_front.png",
    }
    for output_name, source_name in portraits.items():
        source = QImage(str(ASSET_DIR / "expressions" / source_name))
        if source.isNull():
            raise RuntimeError(f"Could not load expression artwork: {source_name}")
        content = source.copy(_alpha_bounds(source))
        scaled = content.scaled(
            QSize(600, 590),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        canvas = QImage(640, 640, QImage.Format.Format_ARGB32)
        canvas.fill(Qt.GlobalColor.transparent)
        painter = QPainter(canvas)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        painter.drawImage((640 - scaled.width()) // 2, 20, scaled)
        painter.end()
        if not canvas.save(str(output_dir / output_name)):
            raise RuntimeError(f"Could not save {output_dir / output_name}")


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
        check=False,
    )
    if result.returncode or not output.exists():
        detail = result.stderr.decode("utf-8", errors="replace")[:400]
        raise RuntimeError(detail or "Could not synthesize demo narration")
    with wave.open(str(output), "rb") as audio:
        return audio.getnframes() / audio.getframerate()


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


def demo_video_command(
    ffmpeg: str,
    narration: Path,
    output: Path,
) -> list[str]:
    return [
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


def video_character_cache() -> dict[str, QImage]:
    character_names = {
        "attentive_front.png",
        "blink_front.png",
        "attentive_front_speech_mid.png",
        "attentive_front_speech_open.png",
        "attentive_front_speech_round.png",
    }
    return {
        name: scaled_inside(
            QImage(str(ROOT / "assets" / "expressions" / name)),
            QSize(390, 510),
        )
        for name in character_names
    }


def render_video_scene_base(
    media: dict[str, QImage],
    scene: str,
    heading: str,
    caption: str,
) -> QImage:
    base = QImage(WIDTH, HEIGHT, QImage.Format_ARGB32)
    painter = QPainter(base)
    painter.setRenderHint(QPainter.Antialiasing)
    gradient = QLinearGradient(0, 0, WIDTH, HEIGHT)
    gradient.setColorAt(0.0, QColor("#07131e"))
    gradient.setColorAt(1.0, QColor("#16354b"))
    painter.fillRect(base.rect(), gradient)
    painter.setPen(QColor("#f2fbff"))
    painter.setFont(QFont("Microsoft JhengHei UI", 27, QFont.Bold))
    painter.drawText(QRect(46, 26, 1180, 50), "墨寒桌面語音互動虛擬助理")
    painter.setPen(QColor("#f0afd8"))
    painter.setFont(QFont("Microsoft JhengHei UI", 21, QFont.Bold))
    painter.drawText(QRect(48, 83, 740, 42), heading)
    painter.setPen(QColor("#a9dff2"))
    painter.setFont(QFont("Microsoft JhengHei UI", 14))
    painter.drawText(QRect(49, 126, 760, 32), caption)
    panel = QRect(40, 172, 830, 492)
    draw_rounded_panel(painter, panel, QColor(9, 25, 38, 235))
    page = scaled_inside(media[scene], QSize(794, 456))
    painter.drawImage(
        QPoint(
            panel.x() + (panel.width() - page.width()) // 2,
            panel.y() + (panel.height() - page.height()) // 2,
        ),
        page,
    )
    painter.setPen(QColor("#d7edf6"))
    painter.setFont(QFont("Microsoft JhengHei UI", 12))
    painter.drawText(
        QRect(883, 642, 350, 30),
        Qt.AlignCenter,
        "安全展示資料・不含 API 金鑰與私人內容",
    )
    painter.end()
    return base


def render_video_frame(
    media: dict[str, QImage],
    base_cache: dict[tuple[str, str, str], QImage],
    character_cache: dict[str, QImage],
    second: float,
    timing: VideoTiming,
) -> QImage:
    scene, heading, caption = video_scene(second, timing.duration)
    base_key = (scene, heading, caption)
    if base_key not in base_cache:
        base_cache[base_key] = render_video_scene_base(
            media,
            scene,
            heading,
            caption,
        )
    frame = base_cache[base_key].copy()
    painter = QPainter(frame)
    painter.setRenderHint(QPainter.Antialiasing)
    speaking = (
        5.0
        < second
        < min(
            timing.audio_duration + 0.4,
            timing.duration - 0.8,
        )
    )
    character_name = (
        speech_character_filename(second) if speaking else "attentive_front.png"
    )
    painter.drawImage(QPoint(870, 165), character_cache[character_name])
    painter.end()
    return frame


def write_video_frames(
    process: subprocess.Popen[bytes],
    media: dict[str, QImage],
    audio_duration: float,
    duration: float,
) -> None:
    assert process.stdin is not None
    base_cache: dict[tuple[str, str, str], QImage] = {}
    character_cache = video_character_cache()
    timing = VideoTiming(duration=duration, audio_duration=audio_duration)
    frame_count = round(duration * FPS)
    for frame_index in range(frame_count):
        frame = render_video_frame(
            media,
            base_cache,
            character_cache,
            frame_index / FPS,
            timing,
        )
        # Keep the converted QImage alive while copying its backing store.
        # Calling bits() on a temporary QImage can release the native image
        # before PySide finishes copying and crash with an access violation.
        converted = frame.convertToFormat(QImage.Format_ARGB32)
        process.stdin.write(converted.bits().tobytes())


def finish_video_process(process: subprocess.Popen[bytes]) -> None:
    assert process.stdin is not None
    process.stdin.close()
    stderr = process.stderr.read() if process.stderr else b""
    return_code = process.wait(timeout=120)
    if return_code:
        raise RuntimeError(stderr.decode("utf-8", errors="replace")[-1200:])


def write_demo_video(
    media: dict[str, QImage],
    output: Path,
    ffmpeg: str,
) -> float:
    with tempfile.TemporaryDirectory(prefix="mohan-readme-video-") as temp_dir:
        narration = Path(temp_dir) / "narration.wav"
        audio_duration = synthesize_demo_audio(narration)
        duration = 36.0
        process = subprocess.Popen(
            demo_video_command(ffmpeg, narration, output),
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
        write_video_frames(process, media, audio_duration, duration)
        finish_video_process(process)
        return duration


def prepare_demo_profile(temp_dir: str) -> None:
    database = StudioDB(Path(temp_dir) / "mohan.db")
    seed_demo_database(database)
    database.close()


def create_capture_app() -> QApplication:
    app = QApplication.instance() or QApplication([])
    app.setStyleSheet(__import__("app").STYLE)
    return app


def capture_first_run_wizard(
    app: QApplication,
    temp_dir: str,
    output_dir: Path,
) -> None:
    wizard_db = StudioDB(Path(temp_dir) / "first-run.db")
    wizard = FirstRunWizard(wizard_db)
    wizard.show()
    app.processEvents()
    save_widget(wizard, output_dir / "first-run-wizard.png")
    wizard.close()
    wizard_db.close()


def create_capture_window(app: QApplication) -> CompanionWindow:
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
    return window


def capture_conversation_assets(
    app: QApplication,
    window: CompanionWindow,
    output_dir: Path,
) -> QImage:
    window.dashboard.tabs.setCurrentIndex(0)
    app.processEvents()
    dashboard = save_widget(window.dashboard, output_dir / "conversation.png")
    save_widget(window, output_dir / "desktop-character.png")
    return dashboard


def representative_character() -> QImage:
    character = QImage(str(ASSET_DIR / "expressions" / "attentive_front.png"))
    if character.isNull():
        raise RuntimeError("Could not load representative character artwork")
    return character


def capture_task_assets(
    app: QApplication,
    window: CompanionWindow,
    output_dir: Path,
) -> QImage:
    window.dashboard.tabs.setCurrentIndex(1)
    app.processEvents()
    tasks = save_widget(window.dashboard, output_dir / "tasks-and-ideas.png")
    character = representative_character()
    compose_hero(tasks, character, output_dir / "mohan-hero.png")
    compose_github_social_preview(
        tasks,
        character,
        output_dir / "github-social-preview.png",
    )
    return tasks


def capture_dashboard_tab(
    app: QApplication,
    window: CompanionWindow,
    index: int,
    output: Path,
) -> QImage:
    window.dashboard.tabs.setCurrentIndex(index)
    app.processEvents()
    return save_widget(window.dashboard, output)


def capture_security_assets(
    app: QApplication,
    window: CompanionWindow,
    output_dir: Path,
) -> QImage:
    window.dashboard.tabs.setCurrentIndex(5)
    window.dashboard.flagship_center.tabs.setCurrentIndex(5)
    app.processEvents()
    return save_widget(window.dashboard, output_dir / "security-permissions.png")


def capture_static_media(
    app: QApplication,
    window: CompanionWindow,
    output_dir: Path,
) -> dict[str, QImage]:
    dashboard = capture_conversation_assets(app, window, output_dir)
    tasks = capture_task_assets(app, window, output_dir)
    memory = capture_dashboard_tab(
        app,
        window,
        3,
        output_dir / "long-term-memory.png",
    )
    voice = capture_dashboard_tab(
        app,
        window,
        4,
        output_dir / "voice-modes.png",
    )
    security = capture_security_assets(app, window, output_dir)
    compose_expression_showcase(output_dir / "expressions.png")
    compose_support_portraits(output_dir)
    return {
        "hero": dashboard,
        "voice": voice,
        "tasks": tasks,
        "memory": memory,
        "security": security,
    }


def maybe_write_demo_video(
    media: dict[str, QImage],
    output_dir: Path,
    ffmpeg: str | None,
) -> float | None:
    if not ffmpeg:
        return None
    return write_demo_video(media, output_dir / "mohan-demo.mp4", ffmpeg)


def capture_media(output_dir: Path, ffmpeg: str | None) -> float | None:
    output_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="mohan-readme-profile-") as temp_dir:
        os.environ["MOHAN_DATA_DIR"] = temp_dir
        prepare_demo_profile(temp_dir)
        app = create_capture_app()
        capture_first_run_wizard(app, temp_dir, output_dir)
        window = create_capture_window(app)
        media = capture_static_media(app, window, output_dir)
        duration = maybe_write_demo_video(media, output_dir, ffmpeg)
        window.dashboard.flagship_center.close_services()
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
