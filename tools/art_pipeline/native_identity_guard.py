"""Validate native RGB ownership for detachable second-generation layers."""

from __future__ import annotations

lazy import hashlib
lazy import re
lazy from collections.abc import Mapping
lazy from dataclasses import dataclass, field
lazy from enum import StrEnum
lazy from io import BytesIO
lazy from pathlib import Path

lazy import numpy as np
lazy from PIL import Image

ALPHA_CHANNEL = 3
CHANNEL_COUNT = 4
RGB_CHANNEL_COUNT = 3
IMAGE_DIMENSIONS = 3
MASK_DIMENSIONS = 2
ALPHA_VISIBLE_THRESHOLD = 0
MASK_BACKGROUND = 0
MASK_FOREGROUND = 255
SHA256_HEX_LENGTH = 64
PNG_HEADER_LENGTH = 26
PNG_BIT_DEPTH_OFFSET = 24
PNG_COLOR_TYPE_OFFSET = 25
NATIVE_PNG_BIT_DEPTH = 8
PNG_RGBA_COLOR_TYPE = 6
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
SHA256_PATTERN = re.compile(r"[0-9a-fA-F]{64}\Z")


class NativeIdentityGuardError(ValueError):
    """Raised when a source cannot be loaded under the native-image contract."""


class NativeIdentityMismatchError(NativeIdentityGuardError):
    """Raised when an overlay differs from its digest-bound native source."""

    def __init__(self, report: NativeIdentityReport) -> None:
        self.report = report
        super().__init__(f"Native identity ownership failed: {report.problems}")


class IdentityIssueCode(StrEnum):
    MISSING_SOURCE = "missing-source"
    INVALID_SOURCE_SHA256 = "invalid-source-sha256"
    INVALID_SOURCE_ARRAY = "invalid-source-array"
    INVALID_SOURCE_PATH = "invalid-source-path"
    INVALID_OVERLAYS = "invalid-overlays"
    NO_OVERLAYS = "no-overlays"
    INVALID_OVERLAY_ARRAY = "invalid-overlay-array"
    EMPTY_OVERLAY_MASK = "empty-overlay-mask"
    SHAPE_MISMATCH = "shape-mismatch"
    INVALID_ALLOWED_MASK = "invalid-allowed-mask"
    EMPTY_ALLOWED_MASK = "empty-allowed-mask"
    MASK_WITHOUT_FACE_CORE = "mask-without-face-core"
    RGB_MISMATCH = "rgb-mismatch"
    ALPHA_INFLATION = "alpha-inflation"


@dataclass(frozen=True, slots=True)
class NativeRgbaSource:
    """An immutable-by-convention RGBA8 source bound to one file digest."""

    path: Path
    sha256: str
    rgba: np.ndarray


@dataclass(frozen=True, slots=True)
class IdentityOverlays:
    """Optional runtime layers to compare against one native source."""

    body: np.ndarray | None = None
    hands: Mapping[str, np.ndarray] = field(default_factory=dict)
    face_core: np.ndarray | None = None
    allowed_dynamic_mask: np.ndarray | None = None


@dataclass(frozen=True, slots=True)
class IdentityIssue:
    code: IdentityIssueCode
    target: str
    detail: str


@dataclass(frozen=True, slots=True)
class OverlayCheck:
    target: str
    visible_pixels: int
    compared_pixels: int
    allowed_pixels: int
    rgb_mismatch_pixels: int
    alpha_inflation_pixels: int
    passed: bool


@dataclass(frozen=True, slots=True)
class NativeIdentityReport:
    passed: bool
    source_path: Path | None
    source_sha256: str | None
    checks: tuple[OverlayCheck, ...]
    issues: tuple[IdentityIssue, ...]

    @property
    def problems(self) -> tuple[str, ...]:
        """Return stable, searchable issue strings for logs and receipts."""
        return tuple(
            f"{issue.code.value}:{issue.target}:{issue.detail}"
            for issue in self.issues
        )

    def to_jsonable(self) -> dict[str, object]:
        """Return JSON-compatible facts suitable for a receipt or exception."""
        return {
            "passed": self.passed,
            "source_path": None if self.source_path is None else str(self.source_path),
            "source_sha256": self.source_sha256,
            "checks": [
                {
                    "target": check.target,
                    "visible_pixels": check.visible_pixels,
                    "compared_pixels": check.compared_pixels,
                    "allowed_pixels": check.allowed_pixels,
                    "rgb_mismatch_pixels": check.rgb_mismatch_pixels,
                    "alpha_inflation_pixels": check.alpha_inflation_pixels,
                    "passed": check.passed,
                }
                for check in self.checks
            ],
            "issues": [
                {
                    "code": issue.code.value,
                    "target": issue.target,
                    "detail": issue.detail,
                }
                for issue in self.issues
            ],
            "problems": list(self.problems),
        }


def load_native_rgba_source(path: Path, expected_sha256: str) -> NativeRgbaSource:
    """Load and digest-bind one native 8-bit RGBA PNG."""
    expected = _normalise_sha256(expected_sha256)
    if not isinstance(path, Path):
        raise NativeIdentityGuardError("source path must be a pathlib.Path")
    if path.is_symlink():
        raise NativeIdentityGuardError("source path must not be a symbolic link")
    resolved = path
    try:
        resolved = path.resolve()
        payload = resolved.read_bytes()
    except (OSError, RuntimeError) as error:
        raise NativeIdentityGuardError(f"cannot read source: {resolved}") from error
    actual = hashlib.sha256(payload).hexdigest()
    if actual != expected:
        raise NativeIdentityGuardError(
            f"source SHA-256 mismatch: expected {expected}, got {actual}"
        )
    rgba = _decode_native_rgba(payload, resolved)
    rgba.setflags(write=False)
    return NativeRgbaSource(resolved, actual, rgba)


def validate_native_identity(
    source: NativeRgbaSource | None,
    overlays: IdentityOverlays | None = None,
) -> NativeIdentityReport:
    """Check visible RGB ownership and alpha containment without changing pixels."""
    if source is None:
        return _report(None, (), (_issue(
            IdentityIssueCode.MISSING_SOURCE,
            "source",
            "a native RGBA source is required",
        ),))
    issues: list[IdentityIssue] = []
    shape = _validate_source(source, issues)
    if shape is None:
        return _report(source, (), tuple(issues))
    if overlays is not None and not isinstance(overlays, IdentityOverlays):
        issues.append(_issue(
            IdentityIssueCode.INVALID_OVERLAYS,
            "overlays",
            "expected IdentityOverlays",
        ))
        return _report(source, (), tuple(issues))
    config = overlays or IdentityOverlays()
    items = _overlay_items(config, issues)
    allowed = _allowed_mask(config, shape, issues)
    if not items:
        issues.append(_issue(
            IdentityIssueCode.NO_OVERLAYS,
            "overlays",
            "at least one body, hand, or face overlay is required",
        ))
    checks: list[OverlayCheck] = []
    for target, overlay, is_face in items:
        mask = allowed if is_face else None
        check, item_issues = _check_overlay(target, overlay, source.rgba, mask)
        checks.append(check)
        issues.extend(item_issues)
    passed = bool(checks) and not issues and all(check.passed for check in checks)
    return NativeIdentityReport(
        passed,
        _source_path(source),
        _source_sha256(source),
        tuple(checks),
        tuple(issues),
    )


def assert_native_identity(
    source: NativeRgbaSource | None,
    overlays: IdentityOverlays | None = None,
) -> dict[str, object]:
    """Return JSONable identity facts, raising on any ownership difference."""
    report = validate_native_identity(source, overlays)
    if not report.passed:
        raise NativeIdentityMismatchError(report)
    return report.to_jsonable()


def _normalise_sha256(value: object) -> str:
    if not isinstance(value, str) or SHA256_PATTERN.fullmatch(value) is None:
        raise NativeIdentityGuardError(
            f"expected SHA-256 must contain {SHA256_HEX_LENGTH} hexadecimal characters"
        )
    return value.lower()


def _decode_native_rgba(payload: bytes, path: Path) -> np.ndarray:
    if (
        len(payload) < PNG_HEADER_LENGTH
        or payload[: len(PNG_SIGNATURE)] != PNG_SIGNATURE
        or payload[PNG_BIT_DEPTH_OFFSET] != NATIVE_PNG_BIT_DEPTH
        or payload[PNG_COLOR_TYPE_OFFSET] != PNG_RGBA_COLOR_TYPE
    ):
        raise NativeIdentityGuardError(f"source must be an 8-bit RGBA PNG: {path}")
    try:
        with Image.open(BytesIO(payload)) as image:
            if image.format != "PNG" or image.mode != "RGBA":
                raise NativeIdentityGuardError(
                    f"source must decode as RGBA: {path}"
                )
            image.load()
            rgba = np.array(image, dtype=np.uint8, copy=True)
    except NativeIdentityGuardError:
        raise
    except (OSError, TypeError, ValueError) as error:
        raise NativeIdentityGuardError(f"cannot decode source PNG: {path}") from error
    if (
        rgba.ndim != IMAGE_DIMENSIONS
        or rgba.shape[2] != CHANNEL_COUNT
        or rgba.dtype != np.uint8
    ):
        raise NativeIdentityGuardError(f"decoded source is not RGBA8: {path}")
    return np.ascontiguousarray(rgba)


def _validate_source(
    source: NativeRgbaSource,
    issues: list[IdentityIssue],
) -> tuple[int, int] | None:
    if not isinstance(source.path, Path):
        issues.append(_issue(
            IdentityIssueCode.INVALID_SOURCE_PATH,
            "source",
            "path must be a pathlib.Path",
        ))
    if not isinstance(source.sha256, str) or SHA256_PATTERN.fullmatch(source.sha256) is None:
        issues.append(_issue(
            IdentityIssueCode.INVALID_SOURCE_SHA256,
            "source",
            "source SHA-256 must contain 64 hexadecimal characters",
        ))
    rgba = source.rgba
    if (
        not isinstance(rgba, np.ndarray)
        or rgba.ndim != IMAGE_DIMENSIONS
        or rgba.shape[2] != CHANNEL_COUNT
        or rgba.dtype != np.uint8
    ):
        issues.append(_issue(
            IdentityIssueCode.INVALID_SOURCE_ARRAY,
            "source",
            "source must be an HxWx4 uint8 array",
        ))
        return None
    return rgba.shape[:2]


def _overlay_items(
    config: IdentityOverlays,
    issues: list[IdentityIssue],
) -> tuple[tuple[str, np.ndarray, bool], ...]:
    items: list[tuple[str, np.ndarray, bool]] = []
    if config.body is not None:
        items.append(("body", config.body, False))
    hands = config.hands
    if not isinstance(hands, Mapping):
        issues.append(_issue(
            IdentityIssueCode.INVALID_OVERLAYS,
            "hands",
            "hands must be a mapping of side names to RGBA arrays",
        ))
    else:
        named_hands: list[tuple[str, np.ndarray]] = []
        for name, overlay in hands.items():
            if not isinstance(name, str) or not name.strip():
                issues.append(_issue(
                    IdentityIssueCode.INVALID_OVERLAYS,
                    "hands",
                    "each hand name must be a nonempty string",
                ))
                continue
            named_hands.append((name, overlay))
        items.extend((f"hand:{name}", overlay, False)
                     for name, overlay in sorted(named_hands))
    if config.face_core is not None:
        items.append(("face_core", config.face_core, True))
    return tuple(items)


def _allowed_mask(
    config: IdentityOverlays,
    shape: tuple[int, int],
    issues: list[IdentityIssue],
) -> np.ndarray | None:
    mask = config.allowed_dynamic_mask
    if mask is None:
        return None
    if config.face_core is None:
        issues.append(_issue(
            IdentityIssueCode.MASK_WITHOUT_FACE_CORE,
            "allowed_dynamic_mask",
            "the mask is only valid with face_core",
        ))
        return None
    if (
        not isinstance(mask, np.ndarray)
        or mask.ndim != MASK_DIMENSIONS
        or mask.shape != shape
        or mask.dtype not in (np.bool_, np.uint8)
    ):
        issues.append(_issue(
            IdentityIssueCode.INVALID_ALLOWED_MASK,
            "allowed_dynamic_mask",
            "mask must be a same-sized 2D bool or binary uint8 array",
        ))
        return None
    if mask.dtype == np.uint8 and not np.isin(mask, [MASK_BACKGROUND, MASK_FOREGROUND]).all():
        issues.append(_issue(
            IdentityIssueCode.INVALID_ALLOWED_MASK,
            "allowed_dynamic_mask",
            "uint8 mask values must be 0 or 255",
        ))
        return None
    result = mask.astype(bool, copy=False)
    if not np.any(result):
        issues.append(_issue(
            IdentityIssueCode.EMPTY_ALLOWED_MASK,
            "allowed_dynamic_mask",
            "an allowed mask must select at least one pixel",
        ))
        return None
    return result


def _check_overlay(
    target: str,
    overlay: object,
    source: np.ndarray,
    allowed: np.ndarray | None,
) -> tuple[OverlayCheck, tuple[IdentityIssue, ...]]:
    shape = source.shape
    if (
        not isinstance(overlay, np.ndarray)
        or overlay.ndim != IMAGE_DIMENSIONS
        or overlay.dtype != np.uint8
    ):
        return (
            OverlayCheck(target, 0, 0, 0, 0, 0, False),
            (_issue(
                IdentityIssueCode.INVALID_OVERLAY_ARRAY,
                target,
                "overlay must be a same-sized HxWx4 uint8 array",
            ),),
        )
    if overlay.shape != shape:
        return (
            OverlayCheck(target, 0, 0, 0, 0, 0, False),
            (_issue(
                IdentityIssueCode.SHAPE_MISMATCH,
                target,
                "overlay must be a same-sized HxWx4 uint8 array",
            ),),
        )
    visible = overlay[:, :, ALPHA_CHANNEL] > ALPHA_VISIBLE_THRESHOLD
    visible_pixels = int(np.count_nonzero(visible))
    if not visible_pixels:
        return (
            OverlayCheck(target, 0, 0, 0, 0, 0, False),
            (_issue(
                IdentityIssueCode.EMPTY_OVERLAY_MASK,
                target,
                "overlay alpha selects no visible pixels",
            ),),
        )
    allowed_pixels_mask = visible & allowed if allowed is not None else np.zeros_like(visible)
    compared = visible & ~allowed_pixels_mask
    alpha_inflation = int(np.count_nonzero(
        overlay[:, :, ALPHA_CHANNEL] > source[:, :, ALPHA_CHANNEL]
    ))
    rgb_difference = np.any(
        overlay[compared, :RGB_CHANNEL_COUNT]
        != source[compared, :RGB_CHANNEL_COUNT],
        axis=1,
    )
    mismatch_pixels = int(np.count_nonzero(rgb_difference))
    issues: list[IdentityIssue] = []
    if mismatch_pixels:
        issues.append(_issue(
            IdentityIssueCode.RGB_MISMATCH,
            target,
            f"{mismatch_pixels} visible RGB pixels differ outside the allowed mask",
        ))
    if alpha_inflation:
        issues.append(_issue(
            IdentityIssueCode.ALPHA_INFLATION,
            target,
            f"{alpha_inflation} pixels exceed native alpha",
        ))
    check = OverlayCheck(
        target,
        visible_pixels,
        int(np.count_nonzero(compared)),
        int(np.count_nonzero(allowed_pixels_mask)),
        mismatch_pixels,
        alpha_inflation,
        not issues,
    )
    return check, tuple(issues)


def _issue(code: IdentityIssueCode, target: str, detail: str) -> IdentityIssue:
    return IdentityIssue(code, target, detail)


def _report(
    source: NativeRgbaSource | None,
    checks: tuple[OverlayCheck, ...],
    issues: tuple[IdentityIssue, ...],
) -> NativeIdentityReport:
    return NativeIdentityReport(
        False,
        _source_path(source),
        _source_sha256(source),
        checks,
        issues,
    )


def _source_path(source: NativeRgbaSource | None) -> Path | None:
    if source is None or not isinstance(source.path, Path):
        return None
    return source.path


def _source_sha256(source: NativeRgbaSource | None) -> str | None:
    if source is None or not isinstance(source.sha256, str):
        return None
    if SHA256_PATTERN.fullmatch(source.sha256) is None:
        return None
    return source.sha256
