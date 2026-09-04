"""Build the README demonstration video from offscreen, reproducible captures.

The six narration lines are intentionally kept together near the top of this
module so the owner can review or edit them without searching through the
renderer.  Narration is synthesized locally through the OneCore Yating voice;
no cloud provider or SAPI fallback is allowed on this production path.
"""

from __future__ import annotations

lazy import argparse
lazy import hashlib
lazy import json
lazy import math
lazy import os
lazy import shutil
lazy import subprocess
lazy import sys
lazy import tempfile
lazy import wave
lazy from dataclasses import dataclass, replace
lazy from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
TESTS = ROOT / "tests"
if str(TESTS) not in sys.path:
    sys.path.insert(0, str(TESTS))

MEDIA_PROVENANCE_PATH = ROOT / "docs" / "media" / "MEDIA-PROVENANCE.json"
MEDIA_VIDEO_PATH = ROOT / "docs" / "media" / "mohan-demo.mp4"
MEDIA_VIDEO_ENTRY = "docs/media/mohan-demo.mp4"

lazy from PySide6.QtCore import QPoint, QRect, QSize, Qt
lazy from PySide6.QtGui import QColor, QFont, QImage, QLinearGradient, QPainter, QPen
lazy from PySide6.QtWidgets import QApplication

lazy from domain.constants import POSE_ATLAS_GENERATION
lazy from domain.lip_sync import (
    VISEME_CUES_PER_SECOND,
    VisemeDynamics,
    infer_vowel_pcm16,
)
lazy from infrastructure.active_outfit_overlay import ActiveOutfitOverlay
lazy from infrastructure.layered_full_body_renderer import LayeredFullBodyRenderer
lazy from integrations.speech_windows_synthesis import (
    OneCoreVoiceSelection,
    synthesize_windows_speech_to_wave,
)
lazy from test_global_settings_actions import close_dashboard, dependencies
lazy from tools.capture_media_contract import select_dashboard_tab
lazy from tools.capture_readme_media import (
    create_capture_app,
    create_capture_dashboard,
    ffmpeg_binary,
    grab_widget_image,
    prepare_demo_profile,
)
lazy from tools.render_marketing_portraits import render_portrait

WIDTH = 1280
HEIGHT = 720
FPS = 10
MIN_VIDEO_DURATION_SECONDS = 30.0
MAX_VIDEO_DURATION_SECONDS = 60.0
AUDIO_CHANNELS = 1
AUDIO_SAMPLE_WIDTH = 2
AUDIO_SAMPLE_RATE = 22050
AUDIO_SAMPLES_PER_VIDEO_FRAME = AUDIO_SAMPLE_RATE // FPS
LEAD_SILENCE_SECONDS = 1.0
INTER_SCENE_SILENCE_SECONDS = 0.4
TAIL_SILENCE_SECONDS = 1.0
MIN_VISEME_ASSET_VARIANTS = 2
MAKEUP_FULL_INTENSITY_PERCENT = 100
SCENE_CONVERSATION = 0
SCENE_SPEAKING = 1
SCENE_TASKS = 2
SCENE_WARDROBE = 3
SCENE_SECURITY = 4
SCENE_OUTRO = 5
BLINK_START_SECONDS = 1.35
BLINK_END_SECONDS = 1.55
ONECORE_YATING_DISPLAY_NAME = "Microsoft Yating"
# Every scene uses this head-and-shoulders crop so the existing viseme assets
# remain visible at 1280x720. This rect is in the 1254x1254 composed portrait
# coordinate space shared by all generated character assets.
SPEAKING_CHARACTER_CROP = QRect(402, 100, 450, 600)

# The animation contract defines the front-pose mouth in the canonical 465 px
# presentation space. Video frames use the unscaled 1254 px portrait assets,
# so keep the conversion explicit for blink and wardrobe speech compositing.
HALF_BODY_CANVAS_SIZE = 1254
HALF_BODY_PRESENTATION_SIZE = 465
SPEECH_MOUTH_RECT_465 = QRect(202, 195, 62, 43)
SPEECH_MOUTH_RECT = QRect(
    round(SPEECH_MOUTH_RECT_465.x() * HALF_BODY_CANVAS_SIZE / HALF_BODY_PRESENTATION_SIZE),
    round(SPEECH_MOUTH_RECT_465.y() * HALF_BODY_CANVAS_SIZE / HALF_BODY_PRESENTATION_SIZE),
    round(SPEECH_MOUTH_RECT_465.width() * HALF_BODY_CANVAS_SIZE / HALF_BODY_PRESENTATION_SIZE),
    round(SPEECH_MOUTH_RECT_465.height() * HALF_BODY_CANVAS_SIZE / HALF_BODY_PRESENTATION_SIZE),
)

# Owner-approved narration.  Keep the six strings unchanged unless the owner
# explicitly approves a new recording script.
DEMO_NARRATION = (
    "妾乃墨寒，附生於赤焰劍中的劍魂。",
    "你說話，妾便聽著——不必按鈕，也不必上傳到別人的雲端。",
    "今日該做的事，妾都替你記著了。",
    "這身衣裝、妝容與髮飾，妾都能換；喜歡哪一套，你自己挑。",
    "動手之前妾會先問你一聲。危險的事，妾不會擅自替你決定。",
    "……別看妾，快去做事。",
)
DEMO_SUBTITLES = (
    "墨寒·桌面語音互動虛擬助理",
    "說話就能互動，50 Hz 嘴型同步",
    "待辦、靈感、工作計時，都在本機",
    "衣裝、髮型、髮飾、妝容都是可拆圖層",
    "工具執行需經權限、確認與稽核",
    "完整功能免費·MIT 授權",
)
SCENE_LABELS = (
    "角色出現",
    "聲音與嘴型",
    "控制中心",
    "雲裳閣",
    "安全權限",
    "墨寒桌面助理",
)
WARDROBE_SLIDER_VALUES = (100, 55, 25, 70, 100)
VISEME_ASSET_BY_NAME = {
    "CLOSED": "attentive_front.png",
    "CONSONANT": "attentive_front_speech_mid.png",
    "A": "attentive_front_speech_open.png",
    "I": "attentive_front_speech_mid.png",
    "U": "attentive_front_speech_round.png",
    "E": "attentive_front_speech_mid.png",
    "O": "attentive_front_speech_round.png",
}
VISEME_SUFFIX_BY_ASSET = {
    "attentive_front.png": "",
    "attentive_front_speech_mid.png": "_speech_mid",
    "attentive_front_speech_open.png": "_speech_open",
    "attentive_front_speech_round.png": "_speech_round",
}


@dataclass(frozen=True, slots=True)
class SpeechSegment:
    """One sentence's measured audio and visual timeline."""

    index: int
    text: str
    source: Path
    start: float
    end: float
    visual_end: float
    duration: float


@dataclass(frozen=True, slots=True)
class Narration:
    """The final PCM narration plus the six measured sentence windows."""

    audio: Path
    duration: float
    segments: tuple[SpeechSegment, ...]
    voice: OneCoreVoiceSelection
    viseme_assets: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class SceneCaptures:
    """Widget captures used by the six scenes."""

    conversation: QImage
    tasks: QImage
    security: QImage
    wardrobe: tuple[QImage, ...]
    wardrobe_previews: tuple[QImage, ...]


def _silence_frame_count(seconds: float) -> int:
    return round(float(seconds) * AUDIO_SAMPLE_RATE)


def _silence(frames: int) -> bytes:
    return b"\0" * (max(0, int(frames)) * AUDIO_SAMPLE_WIDTH)


def _read_normalized_wave(path: Path) -> tuple[bytes, int]:
    with wave.open(str(path), "rb") as audio:
        params = audio.getparams()
        if (
            params.nchannels != AUDIO_CHANNELS
            or params.sampwidth != AUDIO_SAMPLE_WIDTH
            or params.framerate != AUDIO_SAMPLE_RATE
        ):
            raise RuntimeError(
                "Normalized narration must be mono 16-bit PCM at 22050 Hz: "
                f"{path} has {params.nchannels}ch/{params.sampwidth * 8}bit/"
                f"{params.framerate}Hz."
            )
        return audio.readframes(params.nframes), params.nframes


def _run_ffmpeg(command: list[str]) -> None:
    result = subprocess.run(
        command,
        capture_output=True,
        timeout=180,
        check=False,
    )
    if result.returncode:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(detail[-2000:] or "FFmpeg failed.")


def _ffprobe_binary(ffmpeg: str) -> str:
    ffmpeg_path = Path(ffmpeg)
    sibling_name = (
        f"ffprobe{ffmpeg_path.suffix}" if ffmpeg_path.suffix else "ffprobe"
    )
    candidates = (
        os.getenv("FFPROBE_BINARY", ""),
        str(ffmpeg_path.with_name(sibling_name)),
        shutil.which("ffprobe") or "",
    )
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return str(Path(candidate))
    raise RuntimeError("FFprobe not found. Set FFPROBE_BINARY to ffprobe.exe.")


def _probe_video_specs(
    video: Path,
    ffprobe: str,
) -> dict[str, int | float | str]:
    result = subprocess.run(
        [
            ffprobe,
            "-v",
            "error",
            "-print_format",
            "json",
            "-show_streams",
            "-show_format",
            str(video),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30,
        check=False,
    )
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or "FFprobe failed.")
    try:
        metadata = json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise RuntimeError("FFprobe returned invalid JSON.") from error
    if not isinstance(metadata, dict):
        raise RuntimeError("FFprobe returned an invalid metadata object.")
    streams = metadata.get("streams")
    if not isinstance(streams, list):
        raise RuntimeError("FFprobe returned no stream list.")
    video_stream = next(
        (
            stream
            for stream in streams
            if isinstance(stream, dict) and stream.get("codec_type") == "video"
        ),
        None,
    )
    audio_stream = next(
        (
            stream
            for stream in streams
            if isinstance(stream, dict) and stream.get("codec_type") == "audio"
        ),
        None,
    )
    format_info = metadata.get("format")
    if (
        not isinstance(video_stream, dict)
        or not isinstance(audio_stream, dict)
        or not isinstance(format_info, dict)
    ):
        raise RuntimeError("FFprobe did not return video, audio, and format data.")
    try:
        return {
            "width": int(video_stream["width"]),
            "height": int(video_stream["height"]),
            "fps": str(video_stream["r_frame_rate"]),
            "duration_seconds": float(format_info["duration"]),
            "audio_sample_rate": int(audio_stream["sample_rate"]),
            "audio_channels": int(audio_stream["channels"]),
        }
    except (KeyError, TypeError, ValueError) as error:
        raise RuntimeError("FFprobe metadata is missing required video specs.") from error


def _write_video_provenance(
    provenance_path: Path,
    digest: str,
    specs: dict[str, int | float | str],
) -> None:
    manifest = json.loads(provenance_path.read_text(encoding="utf-8"))
    entries = manifest.get("entries")
    entry = entries.get(MEDIA_VIDEO_ENTRY) if isinstance(entries, dict) else None
    if not isinstance(entry, dict):
        raise RuntimeError("Media provenance is missing the demonstration video entry.")
    entry["sha256"] = digest
    entry.update(specs)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=provenance_path.parent,
            prefix=".MEDIA-PROVENANCE-",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary = Path(handle.name)
            json.dump(manifest, handle, ensure_ascii=False, indent=4)
            handle.write("\n")
        temporary.replace(provenance_path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def _normalize_narration_wave(
    ffmpeg: str,
    source: Path,
    target: Path,
) -> None:
    _run_ffmpeg(
        [
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(source),
            "-map",
            "0:a:0",
            "-ac",
            str(AUDIO_CHANNELS),
            "-ar",
            str(AUDIO_SAMPLE_RATE),
            "-c:a",
            "pcm_s16le",
            str(target),
        ]
    )


def _assemble_narration(
    normalized: tuple[Path, ...],
    output: Path,
    voice: OneCoreVoiceSelection,
) -> Narration:
    if len(normalized) != len(DEMO_NARRATION):
        raise RuntimeError("The six narration files were not produced.")
    output.parent.mkdir(parents=True, exist_ok=True)
    segments: list[SpeechSegment] = []
    cursor = _silence_frame_count(LEAD_SILENCE_SECONDS)
    gap_frames = _silence_frame_count(INTER_SCENE_SILENCE_SECONDS)
    with wave.open(str(output), "wb") as combined:
        combined.setnchannels(AUDIO_CHANNELS)
        combined.setsampwidth(AUDIO_SAMPLE_WIDTH)
        combined.setframerate(AUDIO_SAMPLE_RATE)
        combined.writeframes(_silence(cursor))
        for index, (text, source) in enumerate(zip(DEMO_NARRATION, normalized)):
            frames, frame_count = _read_normalized_wave(source)
            start_frame = cursor
            combined.writeframes(frames)
            cursor += frame_count
            end_frame = cursor
            visual_end = end_frame + (gap_frames if index < len(normalized) - 1 else 0)
            segments.append(
                SpeechSegment(
                    index=index,
                    text=text,
                    source=source,
                    start=start_frame / AUDIO_SAMPLE_RATE,
                    end=end_frame / AUDIO_SAMPLE_RATE,
                    visual_end=visual_end / AUDIO_SAMPLE_RATE,
                    duration=frame_count / AUDIO_SAMPLE_RATE,
                )
            )
            if index < len(normalized) - 1:
                combined.writeframes(_silence(gap_frames))
                cursor += gap_frames
        combined.writeframes(_silence(_silence_frame_count(TAIL_SILENCE_SECONDS)))
        cursor += _silence_frame_count(TAIL_SILENCE_SECONDS)
        aligned_cursor = (
            math.ceil(cursor / AUDIO_SAMPLES_PER_VIDEO_FRAME)
            * AUDIO_SAMPLES_PER_VIDEO_FRAME
        )
        combined.writeframes(_silence(aligned_cursor - cursor))
        cursor = aligned_cursor
    return Narration(
        audio=output,
        duration=cursor / AUDIO_SAMPLE_RATE,
        segments=tuple(segments),
        voice=voice,
        viseme_assets=(),
    )


def _build_narration(temp_dir: Path, ffmpeg: str) -> Narration:
    raw_dir = temp_dir / "onecore"
    normalized_dir = temp_dir / "normalized"
    raw_dir.mkdir(parents=True, exist_ok=True)
    normalized_dir.mkdir(parents=True, exist_ok=True)
    normalized: list[Path] = []
    selected_voice: OneCoreVoiceSelection | None = None
    for index, text in enumerate(DEMO_NARRATION, start=1):
        raw = raw_dir / f"line-{index:02d}.wav"
        voice = synthesize_windows_speech_to_wave(
            text,
            raw,
            voice_name=ONECORE_YATING_DISPLAY_NAME,
        )
        if selected_voice is None:
            selected_voice = voice
        elif voice != selected_voice:
            raise RuntimeError("OneCore selected different voices between lines.")
        target = normalized_dir / f"line-{index:02d}.wav"
        _normalize_narration_wave(ffmpeg, raw, target)
        normalized.append(target)
    if selected_voice is None:
        raise RuntimeError("OneCore Yating did not produce any narration.")
    narration = _assemble_narration(
        tuple(normalized),
        temp_dir / "narration-22050-mono.wav",
        selected_voice,
    )
    if narration.duration > MAX_VIDEO_DURATION_SECONDS:
        raise RuntimeError(
            "Normal-speed OneCore/Yating narration is "
            f"{narration.duration:.3f}s, over the 60s test boundary; "
            "do not speed it up. Owner decision required: raise the test "
            "limit or shorten the approved lines."
        )
    if narration.duration < MIN_VIDEO_DURATION_SECONDS:
        raise RuntimeError(
            "Normal-speed OneCore/Yating narration is "
            f"{narration.duration:.3f}s, below the 30s test boundary; "
            "the recording must follow the approved audio timing and was not padded."
        )
    # The video timeline contains all six lines plus the measured lead,
    # inter-scene, and tail silence. Drive every rendered scene from that
    # assembled clock so speech never falls back to a static mouth outside
    # scene two.
    viseme_assets = _viseme_track(narration.audio)
    return replace(narration, viseme_assets=viseme_assets)


def _viseme_track(path: Path) -> tuple[str, ...]:
    """Run the same 50 Hz acoustic cue cadence used by the speech runtime."""

    with wave.open(str(path), "rb") as audio:
        if (
            audio.getnchannels() != AUDIO_CHANNELS
            or audio.getsampwidth() != AUDIO_SAMPLE_WIDTH
            or audio.getframerate() != AUDIO_SAMPLE_RATE
        ):
            raise RuntimeError("The viseme source wave is not normalized audio.")
        pcm = audio.readframes(audio.getnframes())
    cue_frames = AUDIO_SAMPLE_RATE // VISEME_CUES_PER_SECOND
    dynamics = VisemeDynamics()
    track: list[str] = []
    for offset in range(0, len(pcm), cue_frames * AUDIO_SAMPLE_WIDTH):
        chunk = pcm[offset : offset + cue_frames * AUDIO_SAMPLE_WIDTH]
        level, vowel = infer_vowel_pcm16(chunk, AUDIO_SAMPLE_RATE)
        frame = dynamics.advance(level, vowel)
        track.append(VISEME_ASSET_BY_NAME[frame.selected])
    if len(set(track)) < MIN_VISEME_ASSET_VARIANTS:
        raise RuntimeError("The 50 Hz OneCore viseme track did not move.")
    return tuple(track)


def _demo_dependencies(root: Path):
    """Use the capture fixture while opting its wardrobe preview into runtime composition."""

    base = dependencies(root)
    if base.presentation_ports is None:
        raise RuntimeError("The capture fixture did not provide presentation ports.")

    def outfit_overlay_factory(*, on_stale_body_profile=None):
        return ActiveOutfitOverlay(
            root / "outfits",
            ROOT,
            on_stale_body_profile=on_stale_body_profile,
        )

    def full_body_renderer_factory(*, outfit_overlay=None):
        return LayeredFullBodyRenderer(outfit_overlay=outfit_overlay)

    ports = replace(
        base.presentation_ports,
        outfit_overlay_factory=outfit_overlay_factory,
        full_body_renderer_factory=full_body_renderer_factory,
    )
    return replace(base, presentation_ports=ports)


def _process_events(app: QApplication, rounds: int = 3) -> None:
    for _ in range(rounds):
        app.processEvents()


def _capture_wardrobe_states(
    app: QApplication,
    dashboard,
) -> tuple[tuple[QImage, ...], tuple[QImage, ...]]:
    select_dashboard_tab(dashboard, "wardrobe")
    _process_events(app)
    # The actual dashboard timer is disabled by create_capture_dashboard; call
    # the same runtime preview method directly after each slider mutation.
    compose_preview = getattr(dashboard, "_compose_wardrobe_preview", None)
    if compose_preview is None:
        raise RuntimeError("Dashboard wardrobe preview is unavailable.")
    slider = dashboard.wardrobe_makeup_intensity
    captures: list[QImage] = []
    previews: list[QImage] = []
    for value in WARDROBE_SLIDER_VALUES:
        slider.setValue(value)
        _process_events(app)
        compose_preview()
        _process_events(app)
        captures.append(grab_widget_image(dashboard))
        pixmap = dashboard.wardrobe_character_preview.pixmap()
        if pixmap is None or pixmap.isNull():
            raise RuntimeError("Wardrobe preview did not produce a composed character.")
        preview = pixmap.toImage().convertToFormat(QImage.Format_ARGB32)
        previews.append(preview)
    overlay = dashboard._wardrobe_outfit_overlay
    if overlay.layer_count("yaw+000-pitch+00") <= 0:
        raise RuntimeError("Wardrobe preview did not use the active runtime overlay.")
    if dashboard.wardrobe_makeup_intensity.value() != MAKEUP_FULL_INTENSITY_PERCENT:
        raise RuntimeError("The final wardrobe capture did not restore makeup to 100%.")
    return tuple(captures), tuple(previews)


def _capture_scene_widgets(temp_dir: Path) -> SceneCaptures:
    os.environ["MOHAN_DATA_DIR"] = str(temp_dir)
    prepare_demo_profile(str(temp_dir))
    app = create_capture_app()
    database, dashboard = create_capture_dashboard(
        app,
        str(temp_dir),
        dependencies_factory=_demo_dependencies,
    )
    try:
        select_dashboard_tab(dashboard, "conversation")
        _process_events(app)
        conversation = grab_widget_image(dashboard)
        select_dashboard_tab(dashboard, "tasks")
        _process_events(app)
        tasks = grab_widget_image(dashboard)
        select_dashboard_tab(dashboard, "security")
        _process_events(app)
        security = grab_widget_image(dashboard)
        wardrobe, previews = _capture_wardrobe_states(app, dashboard)
        return SceneCaptures(conversation, tasks, security, wardrobe, previews)
    finally:
        close_dashboard(dashboard, database)
        _process_events(app)


def _speech_mouth_overlay(base: QImage, speech: QImage) -> QImage:
    """Put only the official speech-mouth region over another portrait."""

    if speech.size() != base.size():
        speech = speech.scaled(
            base.size(),
            Qt.IgnoreAspectRatio,
            Qt.SmoothTransformation,
        )
    masked = QImage(base.size(), QImage.Format_ARGB32)
    masked.fill(Qt.transparent)
    mask_painter = QPainter(masked)
    mask_painter.setRenderHint(QPainter.Antialiasing)
    mask_painter.drawImage(0, 0, speech)
    mask_painter.setCompositionMode(QPainter.CompositionMode_DestinationIn)
    mask_painter.setPen(Qt.NoPen)
    mask_painter.setBrush(QColor(255, 255, 255, 255))
    mouth_rect = QRect(
        round(SPEECH_MOUTH_RECT.x() * base.width() / HALF_BODY_CANVAS_SIZE),
        round(SPEECH_MOUTH_RECT.y() * base.height() / HALF_BODY_CANVAS_SIZE),
        round(SPEECH_MOUTH_RECT.width() * base.width() / HALF_BODY_CANVAS_SIZE),
        round(SPEECH_MOUTH_RECT.height() * base.height() / HALF_BODY_CANVAS_SIZE),
    )
    radius = round(38 * min(
        base.width() / HALF_BODY_CANVAS_SIZE,
        base.height() / HALF_BODY_CANVAS_SIZE,
    ))
    mask_painter.drawRoundedRect(mouth_rect, radius, radius)
    mask_painter.end()

    result = base.copy()
    painter = QPainter(result)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.drawImage(0, 0, masked)
    painter.end()
    return result


def _render_character_assets(temp_dir: Path) -> dict[str, QImage]:
    overlay = ActiveOutfitOverlay(temp_dir / "marketing-store", ROOT)
    names = {
        "attentive_front.png",
        "blink_front.png",
        "determined_front.png",
        "gentle_smile_front.png",
    }
    for expression in ("attentive_front", "determined_front", "gentle_smile_front"):
        names.update(
            f"{expression}_speech_{frame}.png"
            for frame in ("mid", "open", "round")
        )
    characters = {
        name: render_portrait(overlay, name.removesuffix(".png"))
        for name in sorted(names)
    }
    for frame in ("mid", "open", "round"):
        characters[f"blink_front_speech_{frame}.png"] = _speech_mouth_overlay(
            characters["blink_front.png"],
            characters[f"gentle_smile_front_speech_{frame}.png"],
        )
    return characters


def _viseme_asset_at(
    timeline_seconds: float,
    viseme_assets: tuple[str, ...],
) -> str:
    if not viseme_assets:
        raise RuntimeError("The video has no full-track viseme schedule.")
    cue_index = min(
        len(viseme_assets) - 1,
        max(0, int(timeline_seconds * VISEME_CUES_PER_SECOND)),
    )
    return viseme_assets[cue_index]


def _speech_asset_name(expression: str, viseme_asset: str) -> str:
    try:
        suffix = VISEME_SUFFIX_BY_ASSET[viseme_asset]
    except KeyError as error:
        raise RuntimeError(f"Unknown video viseme asset: {viseme_asset}") from error
    return f"{expression}{suffix}.png"


def _dynamic_character_image(
    expression: str,
    timeline_seconds: float,
    characters: dict[str, QImage],
    viseme_assets: tuple[str, ...],
) -> QImage:
    viseme_asset = _viseme_asset_at(timeline_seconds, viseme_assets)
    name = _speech_asset_name(expression, viseme_asset)
    if name not in characters:
        raise RuntimeError(f"Video character asset is missing: {name}")
    return characters[name]


def _dynamic_wardrobe_preview(
    preview: QImage,
    timeline_seconds: float,
    characters: dict[str, QImage],
    viseme_assets: tuple[str, ...],
) -> QImage:
    viseme_asset = _viseme_asset_at(timeline_seconds, viseme_assets)
    speech_name = _speech_asset_name("attentive_front", viseme_asset)
    return _speech_mouth_overlay(preview, characters[speech_name])


def _scaled_inside(image: QImage, size: QSize) -> QImage:
    normalized = image.copy()
    normalized.setDevicePixelRatio(1.0)
    return normalized.scaled(size, Qt.KeepAspectRatio, Qt.SmoothTransformation)


def _character_panel_crop(image: QImage) -> QImage:
    """Crop every scene to the same face-visible head-and-shoulders framing."""

    crop = QRect(
        round(SPEAKING_CHARACTER_CROP.x() * image.width() / HALF_BODY_CANVAS_SIZE),
        round(SPEAKING_CHARACTER_CROP.y() * image.height() / HALF_BODY_CANVAS_SIZE),
        round(SPEAKING_CHARACTER_CROP.width() * image.width() / HALF_BODY_CANVAS_SIZE),
        round(SPEAKING_CHARACTER_CROP.height() * image.height() / HALF_BODY_CANVAS_SIZE),
    )
    if crop.right() >= image.width() or crop.bottom() >= image.height():
        raise RuntimeError("Character panel crop does not fit the portrait canvas.")
    return image.copy(crop)


def _draw_panel(
    painter: QPainter,
    rect: QRect,
    fill: QColor,
    border: QColor = QColor("#b6c8d6"),
) -> None:
    painter.setPen(QPen(border, 2))
    painter.setBrush(fill)
    painter.drawRoundedRect(rect, 22, 22)


def _scene_dashboard_image(
    scene_index: int,
    local_progress: float,
    captures: SceneCaptures,
) -> QImage | None:
    if scene_index in {SCENE_CONVERSATION, SCENE_SPEAKING}:
        return captures.conversation
    if scene_index == SCENE_TASKS:
        return captures.tasks
    if scene_index == SCENE_WARDROBE:
        index = min(
            len(captures.wardrobe) - 1,
            int(local_progress * len(captures.wardrobe)),
        )
        return captures.wardrobe[index]
    if scene_index == SCENE_SECURITY:
        return captures.security
    return None


def _scene_character_image(
    scene_index: int,
    local_seconds: float,
    local_progress: float,
    captures: SceneCaptures,
    characters: dict[str, QImage],
    viseme_assets: tuple[str, ...],
    timeline_seconds: float,
) -> QImage:
    if scene_index == SCENE_CONVERSATION:
        blink_phase = local_seconds % 3.2
        expression = (
            "blink_front"
            if BLINK_START_SECONDS <= blink_phase < BLINK_END_SECONDS
            else "gentle_smile_front"
        )
        return _dynamic_character_image(
            expression,
            timeline_seconds,
            characters,
            viseme_assets,
        )
    if scene_index == SCENE_SPEAKING:
        return _dynamic_character_image(
            "attentive_front",
            timeline_seconds,
            characters,
            viseme_assets,
        )
    if scene_index == SCENE_WARDROBE:
        preview_index = min(
            len(captures.wardrobe_previews) - 1,
            int(local_progress * len(captures.wardrobe_previews)),
        )
        return _dynamic_wardrobe_preview(
            captures.wardrobe_previews[preview_index],
            timeline_seconds,
            characters,
            viseme_assets,
        )
    if scene_index == SCENE_SECURITY:
        return _dynamic_character_image(
            "determined_front",
            timeline_seconds,
            characters,
            viseme_assets,
        )
    return _dynamic_character_image(
        "gentle_smile_front",
        timeline_seconds,
        characters,
        viseme_assets,
    )


def _compose_end_card(painter: QPainter) -> None:
    card = QRect(48, 145, 782, 420)
    _draw_panel(painter, card, QColor(255, 255, 255, 238))
    painter.setPen(QColor("#17344f"))
    painter.setFont(QFont("Microsoft JhengHei UI", 32, QFont.Bold))
    painter.drawText(QRect(card.x() + 38, card.y() + 52, 700, 56), "墨寒桌面助理")
    painter.setPen(QColor("#48647a"))
    painter.setFont(QFont("Microsoft JhengHei UI", 19))
    painter.drawText(
        QRect(card.x() + 40, card.y() + 135, 690, 42),
        "本機語音・本機資料・使用者掌握權限",
    )
    painter.setPen(QColor("#8a506e"))
    painter.setFont(QFont("Microsoft JhengHei UI", 18, QFont.Bold))
    painter.drawText(
        QRect(card.x() + 40, card.y() + 225, 690, 44),
        "完整功能免費 · MIT License",
    )


def _compose_frame(
    scene_index: int,
    subtitle: str,
    dashboard: QImage | None,
    character: QImage,
) -> QImage:
    canvas = QImage(WIDTH, HEIGHT, QImage.Format_ARGB32)
    canvas.fill(QColor("#eef3f8"))
    painter = QPainter(canvas)
    painter.setRenderHint(QPainter.Antialiasing)
    gradient = QLinearGradient(0, 0, WIDTH, HEIGHT)
    gradient.setColorAt(0.0, QColor("#edf4f8"))
    gradient.setColorAt(0.58, QColor("#f8f9fa"))
    gradient.setColorAt(1.0, QColor("#f8efed"))
    painter.fillRect(canvas.rect(), gradient)
    painter.setPen(QColor("#17344f"))
    painter.setFont(QFont("Microsoft JhengHei UI", 25, QFont.Bold))
    painter.drawText(QRect(38, 20, 850, 42), "墨寒·桌面語音互動虛擬助理")
    painter.setPen(QColor("#48647a"))
    painter.setFont(QFont("Microsoft JhengHei UI", 13))
    painter.drawText(
        QRect(40, 61, 940, 28),
        f"本機互動展示  ·  {SCENE_LABELS[scene_index]}",
    )

    if dashboard is None:
        _compose_end_card(painter)
    else:
        panel = QRect(28, 103, 832, 503)
        _draw_panel(painter, panel, QColor(255, 255, 255, 238))
        page = _scaled_inside(dashboard, QSize(808, 479))
        painter.drawImage(
            QPoint(
                panel.x() + (panel.width() - page.width()) // 2,
                panel.y() + (panel.height() - page.height()) // 2,
            ),
            page,
        )

    character_panel = QRect(874, 103, 378, 503)
    _draw_panel(painter, character_panel, QColor(255, 255, 255, 238))
    portrait = _scaled_inside(_character_panel_crop(character), QSize(350, 466))
    painter.drawImage(
        QPoint(
            character_panel.x() + (character_panel.width() - portrait.width()) // 2,
            character_panel.y() + (character_panel.height() - portrait.height()) // 2,
        ),
        portrait,
    )

    subtitle_bar = QRect(28, 632, 1224, 64)
    _draw_panel(painter, subtitle_bar, QColor(23, 52, 79, 242), QColor("#8ab7c8"))
    painter.setPen(QColor("#ffffff"))
    painter.setFont(QFont("Microsoft JhengHei UI", 23, QFont.Bold))
    painter.drawText(subtitle_bar, Qt.AlignCenter, subtitle)
    painter.end()
    return canvas


def _scene_for_time(
    second: float,
    segments: tuple[SpeechSegment, ...],
) -> tuple[int, SpeechSegment, float, float]:
    for segment in segments:
        if second < segment.visual_end:
            visual_duration = max(0.1, segment.visual_end - segment.start)
            local = max(0.0, second - segment.start)
            return segment.index, segment, local, min(1.0, local / visual_duration)
    last = segments[-1]
    return last.index, last, max(0.0, second - last.start), 1.0


def _render_frame_sequence(
    frames_dir: Path,
    narration: Narration,
    captures: SceneCaptures,
    characters: dict[str, QImage],
) -> int:
    frames_dir.mkdir(parents=True, exist_ok=True)
    frame_count = math.ceil(narration.duration * FPS)
    if frame_count != math.ceil(narration.duration * FPS):
        raise AssertionError("Frame count must be derived from narration duration.")
    for frame_index in range(frame_count):
        second = frame_index / FPS
        scene_index, segment, local_seconds, progress = _scene_for_time(
            second,
            narration.segments,
        )
        dashboard = _scene_dashboard_image(scene_index, progress, captures)
        character = _scene_character_image(
            scene_index,
            local_seconds,
            progress,
            captures,
            characters,
            narration.viseme_assets,
            second,
        )
        frame = _compose_frame(
            scene_index,
            DEMO_SUBTITLES[scene_index],
            dashboard,
            character,
        )
        target = frames_dir / f"frame-{frame_index:06d}.png"
        if not frame.save(str(target), "PNG"):
            raise RuntimeError(f"Could not save temporary video frame: {target}")
    return frame_count


def _video_command(
    ffmpeg: str,
    frames_dir: Path,
    frame_count: int,
    audio: Path,
    output: Path,
) -> list[str]:
    return [
        ffmpeg,
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-framerate",
        str(FPS),
        "-start_number",
        "0",
        "-i",
        str(frames_dir / "frame-%06d.png"),
        "-i",
        str(audio),
        "-map",
        "0:v:0",
        "-map",
        "1:a:0",
        "-frames:v",
        str(frame_count),
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "20",
        "-pix_fmt",
        "yuv420p",
        "-r",
        str(FPS),
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        "-ar",
        str(AUDIO_SAMPLE_RATE),
        "-ac",
        str(AUDIO_CHANNELS),
        "-shortest",
        "-movflags",
        "+faststart",
        str(output),
    ]


def record_demo_video(output: Path, ffmpeg: str) -> tuple[Narration, int]:
    """Record the video atomically and return measured narration/frame data."""

    output = Path(output)
    ffprobe = _ffprobe_binary(ffmpeg)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix=".mohan-demo-record-",
        dir=str(output.parent),
    ) as temporary:
        temp_dir = Path(temporary)
        narration = _build_narration(temp_dir, ffmpeg)
        captures = _capture_scene_widgets(temp_dir / "profile")
        characters = _render_character_assets(temp_dir)
        frames_dir = temp_dir / "frames"
        frame_count = _render_frame_sequence(
            frames_dir,
            narration,
            captures,
            characters,
        )
        encoded = temp_dir / "mohan-demo.mp4"
        _run_ffmpeg(
            _video_command(
                ffmpeg,
                frames_dir,
                frame_count,
                narration.audio,
                encoded,
            )
        )
        if not encoded.is_file() or encoded.stat().st_size <= 0:
            raise RuntimeError("FFmpeg did not produce the demonstration video.")
        specs = _probe_video_specs(encoded, ffprobe)
        encoded.replace(output)
        if output.resolve() == MEDIA_VIDEO_PATH.resolve():
            digest = hashlib.sha256(output.read_bytes()).hexdigest()
            _write_video_provenance(MEDIA_PROVENANCE_PATH, digest, specs)
        return narration, frame_count


def _arguments(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "docs" / "media" / "mohan-demo.mp4",
    )
    parser.add_argument("--ffmpeg", default="")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    arguments = _arguments(argv)
    ffmpeg = ffmpeg_binary(arguments.ffmpeg)
    narration, frame_count = record_demo_video(arguments.output, ffmpeg)
    digest = hashlib.sha256(arguments.output.read_bytes()).hexdigest()
    print(
        f"README_DEMO_VIDEO_OK output={arguments.output} "
        f"generation={POSE_ATLAS_GENERATION} duration={narration.duration:.3f}s "
        f"frames={frame_count} fps={FPS} sha256={digest} "
        f"voice_display_name={narration.voice.display_name} "
        f"voice_id={narration.voice.voice_id} onecore=true",
        flush=True,
    )
    for segment in narration.segments:
        print(
            f"AUDIO_SEGMENT index={segment.index + 1} "
            f"duration={segment.duration:.3f}s "
            f"start={segment.start:.3f}s end={segment.end:.3f}s",
            flush=True,
        )
    print(
        "VISEME_TRACK "
        f"cues={len(narration.viseme_assets)} "
        f"unique_assets={len(set(narration.viseme_assets))}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
