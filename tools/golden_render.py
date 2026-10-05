"""Render and verify the deterministic MoHan appearance golden matrix."""

from __future__ import annotations

lazy import argparse
lazy import hashlib
lazy import json
lazy import os
lazy import shutil
lazy import socket
lazy import struct
lazy import subprocess
lazy import sys
lazy import time
lazy import uuid
lazy import zipfile
lazy from collections.abc import Iterable
lazy from contextlib import contextmanager
lazy from dataclasses import dataclass
lazy from datetime import date
lazy from pathlib import Path

os.environ["QT_QPA_PLATFORM"] = "offscreen"

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

lazy import numpy as np
lazy from PIL import Image, ImageChops
lazy from PySide6.QtCore import Qt
lazy from PySide6.QtGui import QImage, QPixmap, QPixmapCache
lazy from PySide6.QtWidgets import QApplication

lazy from domain.face_rig import (
    ExpressionShape,
    FaceMotionFrame,
    FacePose,
    MouthShape,
    Viseme,
    blink_for_eye_state,
)
lazy from domain.outfit_pack import clear_appearance_selection, restore_builtin_outfit
lazy from domain.outfit_pack_makeup import (
    DEFAULT_MAKEUP_INTENSITY,
    DEFAULT_SLOT_INTENSITIES_V2,
    select_builtin_makeup,
    write_makeup_intensity,
    write_makeup_slot_intensity,
)
lazy from infrastructure.active_outfit_overlay import ActiveOutfitOverlay
lazy from infrastructure.layered_face_renderer import LayeredParametricFaceRenderer
lazy from infrastructure.layered_face_assets import load_layered_face_assets
lazy from infrastructure.layered_full_body_assets import load_layered_full_body_assets
lazy from infrastructure.layered_full_body_renderer import LayeredFullBodyRenderer
lazy from presentation.companion_face_assets import CompanionFaceAssetMethods

DEFAULT_OUTPUT = ROOT / ".quality-tmp" / "golden-render" / "current"
DEFAULT_BASELINE = ROOT / ".quality-tmp" / "golden-render" / "baseline"
DEFAULT_DIFF = ROOT / ".quality-tmp" / "golden-diff"
GIT_REVISION_LENGTH = 40

_MOHAN_EXPRESSION_POSES = (
    ("glance", "cheek"), ("caught", "cheek"), ("happy", "cheek"),
    ("worried", "cheek"), ("reminder", "cheek"), ("thinking_front", "front"),
    ("gentle_smile_front", "front"), ("worried_front", "front"),
    ("shy_front", "front"), ("mock_scold", "front"),
    ("surprised_front", "front"), ("relieved_front", "front"),
    ("tired_front", "front"), ("proud_front", "front"),
    ("shy_cute_front", "front"), ("mock_hit_front", "front"),
    ("attentive_front", "front"), ("determined_front", "front"),
    ("restrained_amused_front", "front"), ("exasperated_front", "front"),
    ("eureka_front", "front"), ("protective_front", "front"),
)
_MOHAN_EXPRESSION_ASSETS = (
    "idle", "idle_lean", "idle_front", "blink", "blink_lean", "blink_front",
    "glance", "caught", "speaking", "speaking_lean", "speaking_front",
    "happy", "worried", "reminder", "thinking_front", "gentle_smile_front",
    "worried_front", "shy_front", "mock_scold", "surprised_front",
    "relieved_front", "tired_front", "proud_front", "shy_cute_front",
    "mock_hit_front", "attentive_front", "determined_front",
    "restrained_amused_front", "exasperated_front", "eureka_front",
    "protective_front",
    *(
        f"{expression}_speech_{frame}"
        for expression, _pose in _MOHAN_EXPRESSION_POSES
        for frame in ("mid", "open", "round")
    ),
    "thinking_front_speech_blink",
    "idle_front_half", "idle_lean_half", "eureka_front_half",
    "mock_hit_front_half", "mock_scold_half", "idle_lean_closed",
    "idle_front_closed", "eureka_front_closed", "mock_hit_front_closed",
    "mock_scold_closed", "viseme_mid_front", "viseme_wide_front",
    "viseme_round", "viseme_round_lean", "viseme_round_front", "viseme_i",
    "viseme_i_lean", "viseme_i_front", "viseme_o", "viseme_o_lean",
    "viseme_o_front",
)
_MOHAN_FULL_BODY_VIEWS = (
    "yaw+000-pitch+00",
    "yaw+015-pitch+00", "yaw-015-pitch+00",
    "yaw+030-pitch+00", "yaw-030-pitch+00",
    "yaw+045-pitch+00", "yaw-045-pitch+00",
    "yaw+060-pitch+00", "yaw-060-pitch+00",
    "yaw+075-pitch+00", "yaw-075-pitch+00",
    "yaw+090-pitch+00", "yaw-090-pitch+00",
)


@dataclass(frozen=True, slots=True)
class GoldenCharacterSettings:
    """Character-owned catalogs and paths consumed by the golden harness."""

    character_id: str
    manifest_schema: str
    approval_schema: str
    makeups: tuple[str, ...]
    eye_states: tuple[str, ...]
    half_expressions: tuple[str, ...]
    expression_poses: tuple[tuple[str, str], ...]
    expression_assets: tuple[str, ...]
    full_body_views: tuple[str, ...]
    half_size: tuple[int, int]
    full_size: tuple[int, int]
    official_pack_root: str
    half_expression_root: str
    half_layered_root: str
    half_detachable_root: str
    full_layered_root: str
    full_authority_root: str

    def __post_init__(self) -> None:
        text_fields = (
            self.character_id,
            self.manifest_schema,
            self.approval_schema,
            *self.makeups,
            *self.eye_states,
            *self.half_expressions,
            *self.expression_assets,
            *self.full_body_views,
        )
        if not all(isinstance(value, str) and value for value in text_fields):
            raise ValueError("角色設定的識別碼、schema 與清單項目必須是非空字串。")
        if len(set(self.makeups)) != len(self.makeups):
            raise ValueError("角色設定的妝容清單不得重複。")
        if len(set(self.eye_states)) != len(self.eye_states):
            raise ValueError("角色設定的眼態清單不得重複。")
        if len(set(self.half_expressions)) != len(self.half_expressions):
            raise ValueError("角色設定的表情清單不得重複。")
        if len(set(self.full_body_views)) != len(self.full_body_views):
            raise ValueError("角色設定的全身視角清單不得重複。")
        pose_names = [expression for expression, _pose in self.expression_poses]
        if len(set(pose_names)) != len(pose_names):
            raise ValueError("角色設定的表情姿勢映射不得重複。")
        if any(value <= 0 for value in (*self.half_size, *self.full_size)):
            raise ValueError("角色設定的畫布尺寸必須是正整數。")
        for value in self.asset_paths():
            path = Path(value)
            if path.is_absolute() or ".." in path.parts or not path.parts:
                raise ValueError(f"角色素材路徑必須是安全的相對路徑：{value}")

    def asset_paths(self) -> tuple[str, ...]:
        return (
            self.official_pack_root,
            self.half_expression_root,
            self.half_layered_root,
            self.half_detachable_root,
            self.full_layered_root,
            self.full_authority_root,
        )

    def expression_pose_map(self) -> dict[str, str]:
        return dict(self.expression_poses)

    def resolve_asset_path(self, asset_root: Path, relative: str) -> Path:
        root = Path(asset_root).resolve()
        resolved = (root / relative).resolve()
        if not resolved.is_relative_to(root):
            raise ValueError(f"角色素材路徑逸出素材根目錄：{relative}")
        return resolved


DEFAULT_CHARACTER_SETTINGS = GoldenCharacterSettings(
    character_id="flameblade.mohan",
    manifest_schema="mohan.golden-render.v1",
    approval_schema="mohan.golden-render-approval.v1",
    makeups=("none", "light", "classic", "glamorous"),
    eye_states=("rest", "half", "closed"),
    half_expressions=(
        "idle", "idle_lean", "idle_front",
        *(expression for expression, _pose in _MOHAN_EXPRESSION_POSES),
    ),
    expression_poses=_MOHAN_EXPRESSION_POSES,
    expression_assets=_MOHAN_EXPRESSION_ASSETS,
    full_body_views=_MOHAN_FULL_BODY_VIEWS,
    half_size=(465, 465),
    full_size=(1024, 1536),
    official_pack_root="assets/official-packs",
    half_expression_root="assets/expressions",
    half_layered_root="assets/expressions/layered",
    half_detachable_root="assets/expressions/detachable",
    full_layered_root="assets/pose-atlas/v5-base-layered",
    full_authority_root="assets/pose-atlas/v5-base",
)

# Public compatibility aliases keep existing callers and the approved manifest stable.
SCHEMA = DEFAULT_CHARACTER_SETTINGS.manifest_schema
APPROVAL_SCHEMA = DEFAULT_CHARACTER_SETTINGS.approval_schema
MANIFEST_PATH = ROOT / "tests" / "golden" / "golden-manifest.json"
MAKEUPS = DEFAULT_CHARACTER_SETTINGS.makeups
EYE_STATES = DEFAULT_CHARACTER_SETTINGS.eye_states
HALF_EXPRESSIONS = DEFAULT_CHARACTER_SETTINGS.half_expressions
FULL_BODY_VIEWS = DEFAULT_CHARACTER_SETTINGS.full_body_views
HALF_SIZE = DEFAULT_CHARACTER_SETTINGS.half_size
FULL_SIZE = DEFAULT_CHARACTER_SETTINGS.full_size


@dataclass(frozen=True, slots=True)
class GoldenCell:
    cell_id: str
    kind: str
    makeup: str
    eye_state: str
    expression: str | None = None
    pose: str | None = None
    view_id: str | None = None

    @property
    def filename(self) -> str:
        return f"{self.cell_id}.png"

    def inputs(self) -> dict[str, str]:
        values = {"kind": self.kind, "makeup": self.makeup, "eye_state": self.eye_state}
        for key in ("expression", "pose", "view_id"):
            value = getattr(self, key)
            if value is not None:
                values[key] = value
        return values


def matrix_cells(
    settings: GoldenCharacterSettings = DEFAULT_CHARACTER_SETTINGS,
) -> tuple[GoldenCell, ...]:
    cells: list[GoldenCell] = []
    expression_poses = settings.expression_pose_map()
    for expression in settings.half_expressions:
        pose = expression_poses.get(
            expression,
            "lean" if expression == "idle_lean" else "front" if expression == "idle_front" else "cheek",
        )
        cells.extend(
            GoldenCell(
                    f"half__{expression}__{makeup}__{eye_state}",
                    "half-body", makeup, eye_state, expression=expression, pose=pose,
            )
            for makeup in settings.makeups
            for eye_state in settings.eye_states
        )
    for view_id in settings.full_body_views:
        cells.extend(
            GoldenCell(
                f"full__{view_id}__{makeup}__rest",
                "full-body", makeup, "rest", view_id=view_id,
            )
            for makeup in settings.makeups
        )
    return tuple(cells)


def _rgba_bytes(image: QImage) -> bytes:
    """Return straight RGBA8888 bytes with an exact, CPU-independent conversion.

    Qt's SIMD unpremultiply uses the approximate reciprocal instruction, whose
    result differs between Intel and AMD processors, so the golden contract
    never asks Qt to leave premultiplied alpha.  Rounding is exact integer
    arithmetic: channel = round(premultiplied * 255 / alpha).
    """
    source_format = image.format()
    if source_format not in {
        QImage.Format_ARGB32,
        QImage.Format_ARGB32_Premultiplied,
        QImage.Format_RGB32,
    }:
        image = image.convertToFormat(QImage.Format_ARGB32_Premultiplied)
        source_format = QImage.Format_ARGB32_Premultiplied
    width, height = image.width(), image.height()
    rows = np.frombuffer(bytes(image.constBits()), dtype=np.uint8)
    bgra = rows.reshape(height, image.bytesPerLine())[:, : width * 4].reshape(height, width, 4)
    alpha = bgra[:, :, 3].astype(np.uint32)
    color = bgra[:, :, 2::-1].astype(np.uint32)
    if source_format == QImage.Format_RGB32:
        alpha = np.full_like(alpha, 255)
    elif source_format == QImage.Format_ARGB32_Premultiplied:
        safe_alpha = np.maximum(alpha, 1)[:, :, None]
        color = np.where(
            alpha[:, :, None] > 0,
            (color * 255 + safe_alpha // 2) // safe_alpha,
            0,
        )
    rgba = np.dstack((np.minimum(color, 255), alpha)).astype(np.uint8)
    return rgba.tobytes()


def pixel_sha256(image: QImage) -> str:
    payload = struct.pack(">II", image.width(), image.height()) + _rgba_bytes(image)
    return hashlib.sha256(payload).hexdigest()


def _save_pixmap(pixmap: QPixmap, path: Path) -> dict[str, object]:
    image = pixmap.toImage()
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.frombytes("RGBA", (image.width(), image.height()), _rgba_bytes(image)).save(path, "PNG")
    # Reload the persisted PNG before hashing so the manifest describes the
    # decoded RGBA pixels a reviewer sees, not an in-memory paint buffer.
    decoded = QImage(str(path))
    return {
        "width": decoded.width(),
        "height": decoded.height(),
        "mode": "RGBA",
        "pixel_sha256": pixel_sha256(decoded),
        "png_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }


@contextmanager
def _network_disabled():
    original_connect = socket.socket.connect
    original_create_connection = socket.create_connection

    def blocked(*_args, **_kwargs):
        raise RuntimeError("golden render 已停用網路連線")

    socket.socket.connect = blocked
    socket.create_connection = blocked
    try:
        yield
    finally:
        socket.socket.connect = original_connect
        socket.create_connection = original_create_connection


@contextmanager
def _official_pack_root(asset_root: Path, settings: GoldenCharacterSettings):
    from domain import outfit_pack

    previous = outfit_pack.OFFICIAL_PACK_ROOT
    outfit_pack.OFFICIAL_PACK_ROOT = settings.resolve_asset_path(
        asset_root, settings.official_pack_root,
    )
    try:
        yield
    finally:
        outfit_pack.OFFICIAL_PACK_ROOT = previous


def _prepare_store(store: Path, makeup: str) -> None:
    store.mkdir(parents=True, exist_ok=True)
    restore_builtin_outfit(store)
    write_makeup_intensity(store, DEFAULT_MAKEUP_INTENSITY)
    for slot, intensity in DEFAULT_SLOT_INTENSITIES_V2.items():
        write_makeup_slot_intensity(store, slot, intensity)
    if makeup == "none":
        clear_appearance_selection(store, "makeup")
    else:
        select_builtin_makeup(store, makeup)


@contextmanager
def _render_environment(local_appdata: Path):
    previous = {key: os.environ.get(key) for key in ("QT_QPA_PLATFORM", "LOCALAPPDATA")}
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    os.environ["LOCALAPPDATA"] = str(local_appdata)
    try:
        yield
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def _motion(expression: str, pose: str, eye_state: str = "rest") -> FaceMotionFrame:
    return FaceMotionFrame(
        FacePose(pose), expression, Viseme.CLOSED, MouthShape(),
        ExpressionShape(blink=blink_for_eye_state(eye_state)),
        breath=0.0,
    )


def _scaled_expression(
    asset_root: Path,
    stem: str,
    settings: GoldenCharacterSettings,
) -> QPixmap:
    expression_root = settings.resolve_asset_path(asset_root, settings.half_expression_root)
    pixmap = QPixmap(str(expression_root / f"{stem}.png"))
    if pixmap.isNull():
        raise FileNotFoundError(f"缺少表情素材：{stem}")
    return pixmap.scaled(*settings.half_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)


class _BlinkHarness(CompanionFaceAssetMethods):
    """Small runtime-equivalent host for the real companion blink compositor."""

    def __init__(
        self,
        asset_root: Path,
        renderer: LayeredParametricFaceRenderer,
        settings: GoldenCharacterSettings,
    ) -> None:
        self.state = "idle"
        self.face_renderer = renderer
        self.active_physics_pose = "front"
        self.physics_expression_poses = {
            "idle": "cheek", "idle_lean": "lean", "idle_front": "front",
            **settings.expression_pose_map(),
        }
        self.expression_anchor_profiles = {}
        expression_root = settings.resolve_asset_path(asset_root, settings.half_expression_root)
        self.expression_pixmaps = {
            stem: _scaled_expression(asset_root, stem, settings)
            for stem in settings.expression_assets
            if (expression_root / f"{stem}.png").is_file()
        }
        self._build_expression_anchor_profiles()
        self._build_blink_masks(self._blink_regions())


def _render_half_cell(
    cell: GoldenCell,
    renderer: LayeredParametricFaceRenderer,
    harness: _BlinkHarness,
    settings: GoldenCharacterSettings,
) -> QPixmap:
    base = QPixmap(*settings.half_size)
    base.fill(Qt.transparent)
    rest = renderer.render(base, _motion(cell.expression or "idle", cell.pose or "front"), None)
    if rest.isNull() or (rest.width(), rest.height()) != settings.half_size:
        raise RuntimeError(f"半身渲染尺寸錯誤：{cell.cell_id}")
    if cell.eye_state == "rest":
        return rest
    # Complete emotional portraits expose their expression-bound eye endpoints
    # through the speaking/blink route.  The compositor still preserves an
    # expression unchanged when no endpoint is bound to that exact portrait.
    harness.state = "speaking"
    return harness._blink_composite(
        rest,
        cell.expression or "idle",
        blink_for_eye_state(cell.eye_state),
    )


def _render_full_cell(
    cell: GoldenCell,
    renderer: LayeredFullBodyRenderer,
    settings: GoldenCharacterSettings,
) -> QPixmap:
    rendered = renderer.render_view(
        cell.view_id or settings.full_body_views[0],
        _motion("idle_front", "front"),
    )
    if rendered.isNull() or (rendered.width(), rendered.height()) != settings.full_size:
        raise RuntimeError(f"全身渲染尺寸錯誤：{cell.cell_id}")
    return rendered


def render_matrix(
    output: Path,
    *,
    asset_root: Path = ROOT,
    cells: Iterable[GoldenCell] | None = None,
    settings: GoldenCharacterSettings = DEFAULT_CHARACTER_SETTINGS,
) -> dict[str, object]:
    selected = tuple(matrix_cells(settings) if cells is None else cells)
    output = Path(output).resolve()
    asset_root = Path(asset_root).resolve()
    runtime_root = output / "runtime"
    local_appdata = runtime_root / "localappdata"
    local_appdata.mkdir(parents=True, exist_ok=True)
    QApplication.instance() or QApplication([])
    # Each standard capture starts with the same Qt file-pixmap cache state,
    # including when a test renders twice in one interpreter.
    QPixmapCache.clear()
    started = time.perf_counter()
    entries: list[dict[str, object]] = []

    with _render_environment(local_appdata), _network_disabled(), _official_pack_root(
        asset_root, settings,
    ):
        for makeup in settings.makeups:
            makeup_cells = tuple(cell for cell in selected if cell.makeup == makeup)
            if not makeup_cells:
                continue
            store = runtime_root / "stores" / makeup
            _prepare_store(store, makeup)
            overlay = ActiveOutfitOverlay(store, asset_root)
            half_renderer = LayeredParametricFaceRenderer(
                manifest=load_layered_face_assets(settings.resolve_asset_path(
                    asset_root, settings.half_layered_root,
                )),
                outfit_overlay=overlay,
                authority_dir=settings.resolve_asset_path(
                    asset_root, settings.half_expression_root,
                ),
                detachable_dir=settings.resolve_asset_path(
                    asset_root, settings.half_detachable_root,
                ),
            ) if any(cell.kind == "half-body" for cell in makeup_cells) else None
            harness = (
                _BlinkHarness(asset_root, half_renderer, settings)
                if half_renderer is not None else None
            )
            full_manifest = load_layered_full_body_assets(
                settings.resolve_asset_path(asset_root, settings.full_layered_root)
            ) if any(cell.kind == "full-body" for cell in makeup_cells) else None
            full_renderer = LayeredFullBodyRenderer(
                full_manifest,
                outfit_overlay=overlay,
                authority_root=settings.resolve_asset_path(
                    asset_root, settings.full_authority_root,
                ),
            ) if full_manifest is not None else None
            for cell in makeup_cells:
                frame = (
                    _render_half_cell(cell, half_renderer, harness, settings)
                    if cell.kind == "half-body"
                    else _render_full_cell(cell, full_renderer, settings)
                )
                path = output / cell.filename
                measurements = _save_pixmap(frame, path)
                entries.append({
                    "id": cell.cell_id,
                    "file": cell.filename,
                    "inputs": cell.inputs(),
                    **measurements,
                })

    entries.sort(key=lambda item: str(item["id"]))
    return {
        "schema": settings.manifest_schema,
        "hash_contract": "sha256(width_be32 + height_be32 + decoded_rgba8888_pixels)",
        "pixel_tolerance": 0,
        "matrix": {
            "half_body_cells": sum(item["inputs"]["kind"] == "half-body" for item in entries),
            "full_body_cells": sum(item["inputs"]["kind"] == "full-body" for item in entries),
            "total_cells": len(entries),
        },
        "environment": {
            "qt_qpa_platform": "offscreen",
            "network": "disabled",
            "store_policy": "isolated-fixed-per-makeup",
            "localappdata_policy": "isolated-fixed",
        },
        "elapsed_seconds": round(time.perf_counter() - started, 3),
        "cells": entries,
    }


def _load_json(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON 根節點必須是物件：{path}")
    return value


def validate_approval(
    path: Path,
    cell_ids: frozenset[str],
    *,
    known_ids: frozenset[str] | None = None,
    settings: GoldenCharacterSettings = DEFAULT_CHARACTER_SETTINGS,
) -> dict[str, object]:
    approval = _load_json(path)
    required = {"schema", "owner", "date", "quote", "cells"}
    if set(approval) != required or approval.get("schema") != settings.approval_schema:
        raise ValueError(f"核准紀錄必須符合 {settings.approval_schema}。")
    for key in ("owner", "date", "quote"):
        if not isinstance(approval[key], str) or not approval[key].strip():
            raise ValueError(f"核准紀錄欄位 {key} 必須是非空字串。")
    date.fromisoformat(str(approval["date"]))
    covered = approval["cells"]
    if covered == "*":
        return approval
    if not isinstance(covered, list) or not all(isinstance(item, str) for item in covered):
        raise ValueError("核准紀錄 cells 必須是 '*' 或格子 ID 陣列。")
    missing = cell_ids - frozenset(covered)
    unknown = frozenset(covered) - (known_ids if known_ids is not None else cell_ids)
    if missing or unknown:
        raise ValueError(
            f"核准涵蓋不完整：missing={sorted(missing)} unknown={sorted(unknown)}"
        )
    return approval


def _manifest_for_commit(rendered: dict[str, object], approval_path: Path) -> dict[str, object]:
    manifest = dict(rendered)
    manifest.pop("elapsed_seconds", None)
    manifest["source_revision"] = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True,
    ).strip()
    harness_source = Path(__file__).read_bytes()
    manifest["harness"] = {
        "source": harness_source.decode("utf-8"),
        "sha256": hashlib.sha256(harness_source).hexdigest(),
    }
    manifest["approval"] = {
        "path": approval_path.relative_to(ROOT).as_posix(),
        "sha256": hashlib.sha256(approval_path.read_bytes()).hexdigest(),
    }
    for cell in manifest["cells"]:
        cell.pop("png_sha256", None)
    return manifest


def _recover_originals(expected: dict[str, object], cells: list[dict], baseline_dir: Path) -> None:
    """Reconstruct absent originals from the recorded Git revision, then verify pixels."""
    revision = expected.get("source_revision")
    if not isinstance(revision, str) or len(revision) != GIT_REVISION_LENGTH or any(
        char not in "0123456789abcdef" for char in revision
    ):
        raise ValueError("原圖快取缺失；清單需要有效 source_revision 才能重建核准原圖。")
    staging = ROOT / ".quality-tmp" / "golden-reference" / uuid.uuid4().hex
    staging.mkdir(parents=True)
    archive_path = staging / "source.zip"
    subprocess.run(
        ["git", "archive", "--format=zip", f"--output={archive_path}", revision],
        cwd=ROOT, check=True,
    )
    reference_root = staging / "source"
    with zipfile.ZipFile(archive_path) as archive:
        archive.extractall(reference_root)
    # Freeze the capture driver too: future harness changes must not alter
    # reconstruction of the approved production modules and assets.
    harness = expected.get("harness")
    harness_path = reference_root / "tools" / "golden_render.py"
    if isinstance(harness, dict) and isinstance(harness.get("source"), str):
        payload = harness["source"].encode("utf-8")
        if hashlib.sha256(payload).hexdigest() != harness.get("sha256"):
            raise ValueError("基準渲染 harness 的 SHA-256 不符。")
        harness_path.write_bytes(payload)
    else:
        shutil.copy2(Path(__file__), harness_path)
    request_path = staging / "cells.json"
    request_path.write_text(json.dumps([cell["id"] for cell in cells]), encoding="utf-8")
    output = staging / "images"
    script = (
        "import json,sys; from pathlib import Path; "
        "from tools.golden_render import matrix_cells,render_matrix; "
        "ids=json.loads(Path(sys.argv[1]).read_text(encoding='utf-8')); "
        "render_matrix(Path(sys.argv[2]),cells=[c for c in matrix_cells() if c.cell_id in ids])"
    )
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(reference_root)
    subprocess.run(
        [sys.executable, "-c", script, str(request_path), str(output)],
        cwd=reference_root, env=environment, check=True,
    )
    baseline_dir.mkdir(parents=True, exist_ok=True)
    # Keep every unmatched rebuild so CI can upload it for a pixel-level review.
    unrecoverable = ROOT / ".quality-tmp" / "golden-diff" / "unrecoverable"
    mismatched: list[str] = []
    for cell in cells:
        original = output / str(cell["file"])
        actual = pixel_sha256(QImage(str(original)))
        if actual != cell["pixel_sha256"]:
            unrecoverable.mkdir(parents=True, exist_ok=True)
            shutil.copy2(original, unrecoverable / str(cell["file"]))
            mismatched.append(f"{cell['id']}={actual}")
            continue
        shutil.copy2(original, baseline_dir / str(cell["file"]))
    if mismatched:
        raise ValueError(
            f"歷史重建像素與核准雜湊不同（{len(mismatched)} 格）：{', '.join(mismatched)}；"
            f"重建影像保存在 {unrecoverable.relative_to(ROOT).as_posix()}。"
        )


def _write_diff(expected: Path | None, actual: Path, target: Path) -> None:
    target.mkdir(parents=True, exist_ok=True)
    shutil.copy2(actual, target / "new.png")
    if expected is None or not expected.is_file():
        (target / "original-unavailable.txt").write_text(
            "本機尚無基準 PNG；先以核准紀錄執行 --update 產生本機基準影像。\n",
            encoding="utf-8",
        )
        return
    shutil.copy2(expected, target / "original.png")
    original = Image.open(expected).convert("RGBA")
    new = Image.open(actual).convert("RGBA")
    # RGB makes equal-alpha colour changes visible; an RGBA difference would
    # carry alpha=0 for those pixels and appear fully transparent.
    if original.size != new.size:
        canvas_size = (max(original.width, new.width), max(original.height, new.height))
        old_canvas = Image.new("RGBA", canvas_size)
        new_canvas = Image.new("RGBA", canvas_size)
        old_canvas.paste(original, (0, 0))
        new_canvas.paste(new, (0, 0))
        original, new = old_canvas, new_canvas
    channels = ImageChops.difference(original, new).split()
    intensity = channels[0]
    for channel in channels[1:]:
        intensity = ImageChops.lighter(intensity, channel)
    intensity.convert("RGB").save(target / "difference.png")


def compare_manifest(
    rendered: dict[str, object],
    expected: dict[str, object],
    *,
    output: Path,
    baseline_dir: Path = DEFAULT_BASELINE,
    diff_dir: Path = DEFAULT_DIFF,
) -> list[str]:
    expected_by_id = {str(cell["id"]): cell for cell in expected.get("cells", [])}
    actual_by_id = {str(cell["id"]): cell for cell in rendered.get("cells", [])}
    changed: list[str] = []
    originals_needed: list[dict] = []
    for cell_id in sorted(set(expected_by_id) | set(actual_by_id)):
        old = expected_by_id.get(cell_id)
        new = actual_by_id.get(cell_id)
        compared_fields = ("pixel_sha256", "inputs", "width", "height", "mode", "file")
        if old is not None and new is not None and all(
            old.get(field) == new.get(field) for field in compared_fields
        ):
            continue
        changed.append(cell_id)
        if old is not None and new is not None:
            original = baseline_dir / str(old["file"])
            if not original.is_file() or pixel_sha256(QImage(str(original))) != old["pixel_sha256"]:
                originals_needed.append(old)
    if originals_needed:
        _recover_originals(expected, originals_needed, baseline_dir)
    for cell_id in changed:
        old = expected_by_id.get(cell_id)
        new = actual_by_id.get(cell_id)
        if new is not None:
            _write_diff(
                baseline_dir / str(old["file"]) if old is not None else None,
                output / str(new["file"]),
                diff_dir / cell_id,
            )
    return changed


def _write_manifest(path: Path, manifest: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _require_committed_render_sources() -> None:
    changed = subprocess.check_output(
        ["git", "status", "--porcelain", "--", "assets", "domain", "infrastructure", "presentation"],
        cwd=ROOT, text=True,
    ).strip()
    if changed:
        raise ValueError("請先提交渲染程式與素材，再核准更新；source_revision 必須可重建基準。")


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--manifest", type=Path, default=MANIFEST_PATH)
    parser.add_argument("--update", action="store_true")
    parser.add_argument("--approval", type=Path)
    args = parser.parse_args(tuple(argv) if argv is not None else None)
    if args.update != (args.approval is not None):
        parser.error("--update 必須與 --approval <核准紀錄 JSON> 同時使用")
    if args.update:
        validate_approval(
            args.approval, frozenset(),
            known_ids=frozenset(cell.cell_id for cell in matrix_cells()),
        )
        _require_committed_render_sources()

    rendered = render_matrix(args.output)
    output_manifest = dict(rendered)
    output_manifest.pop("elapsed_seconds", None)
    _write_manifest(args.output / "render-manifest.json", output_manifest)
    print(
        f"GOLDEN_RENDER cells={rendered['matrix']['total_cells']} "
        f"seconds={rendered['elapsed_seconds']:.3f} output={args.output}"
    )
    if args.update:
        cell_ids = frozenset(str(cell["id"]) for cell in rendered["cells"])
        approval_path = args.approval.resolve()
        old_cells = (
            {cell["id"]: cell for cell in _load_json(args.manifest)["cells"]}
            if args.manifest.is_file() else {}
        )
        changed_ids = frozenset(
            str(cell["id"]) for cell in rendered["cells"]
            if any(
                old_cells.get(cell["id"], {}).get(field) != cell.get(field)
                for field in ("pixel_sha256", "inputs", "width", "height", "mode", "file")
            )
        ) | (frozenset(old_cells) - cell_ids)
        validate_approval(approval_path, changed_ids, known_ids=cell_ids | frozenset(old_cells))
        manifest = _manifest_for_commit(rendered, approval_path)
        _write_manifest(args.manifest, manifest)
        DEFAULT_BASELINE.mkdir(parents=True, exist_ok=True)
        for cell in rendered["cells"]:
            shutil.copy2(args.output / str(cell["file"]), DEFAULT_BASELINE / str(cell["file"]))
        print(f"GOLDEN_UPDATED manifest={args.manifest} approval={approval_path}")
        return 0

    if not args.manifest.is_file():
        print(f"缺少 golden 清單：{args.manifest}", file=sys.stderr)
        return 2
    changed = compare_manifest(rendered, _load_json(args.manifest), output=args.output)
    if changed:
        print("GOLDEN_CHANGED " + " ".join(changed), file=sys.stderr)
        return 1
    print("GOLDEN_MATCH")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
