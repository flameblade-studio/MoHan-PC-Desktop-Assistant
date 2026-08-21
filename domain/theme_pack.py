from __future__ import annotations

lazy import json
lazy import os
lazy import re
lazy import struct
lazy import zipfile
lazy from dataclasses import dataclass
lazy from pathlib import Path, PurePosixPath
lazy from tempfile import NamedTemporaryFile
lazy from xml.etree import ElementTree

FORMAT = "mohan-theme-pack"
VERSION = 2
MANIFEST = "manifest.json"
MAX_ARCHIVE_BYTES = 16 * 1024 * 1024
MAX_MEMBER_BYTES = 12 * 1024 * 1024
MAX_TOTAL_BYTES = 16 * 1024 * 1024
MAX_COMPRESSION_RATIO = 100
MAX_IMAGE_WIDTH = 4096
MAX_IMAGE_HEIGHT = 4096
SYMLINK_FILE_TYPE = 0o120000
MIN_PNG_HEADER_LENGTH = 24
VIEWBOX_DIMENSIONS = 4
MAX_NAME_LENGTH = 80
MAX_RADIUS = 48
MIN_CONTRAST_RATIO = 4.5
SRGB_LINEAR_THRESHOLD = 0.04045
LANGUAGES = frozenset({"zh-TW", "zh-CN", "en", "ja-JP"})
MEMBERS = frozenset({MANIFEST, "assets/background.svg", "assets/background.png"})
MANIFEST_KEYS = frozenset({
    "format",
    "version",
    "id",
    "display_names",
    "colors",
    "font",
    "radius",
    "background",
    "source",
})
SOURCE_KEYS = frozenset({"channel", "kind", "author", "license", "reference_included"})
SOURCE_CHANNELS = frozenset({"flameblade-official", "user-authored", "mohan-generated"})
SOURCE_KINDS = frozenset({"original", "concept", "reference-derived"})
SOURCE_TEXT = re.compile(r"[^\x00-\x1f\x7f]{1,120}\Z")
DEFAULT_TOKENS = frozendict(
    {
        "window": "#EEF3F8",
        "background": "#EEF3F8",
        "card": "#FFFFFF",
        "surface": "#FFFFFF",
        "text": "#24364A",
        "title": "#17344F",
        "muted": "#60788D",
        "border": "#B9C9D8",
        "primary": "#2F6987",
        "danger": "#B42318",
        "focus": "#7BB8D8",
    }
)
COLOR = re.compile(r"#[0-9A-Fa-f]{6}(?:[0-9A-Fa-f]{2})?\Z")
IDENTIFIER = re.compile(r"[a-z0-9](?:[a-z0-9.-]{0,62}[a-z0-9])?\Z")
FONT = re.compile(r"[\w .,-]{1,80}\Z", re.UNICODE)
SVG_ELEMENTS = frozenset({
    "svg",
    "g",
    "defs",
    "linearGradient",
    "radialGradient",
    "stop",
    "path",
    "rect",
    "circle",
    "ellipse",
    "line",
    "polyline",
    "polygon",
})


class ThemePackError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class ThemePack:
    theme_id: str
    display_names: frozendict[str, str]
    tokens: frozendict[str, str]
    font_family: str
    radius: int
    background: str | None
    source_channel: str
    source_kind: str
    author: str
    license_name: str


def _safe_member(info: zipfile.ZipInfo) -> None:
    path = PurePosixPath(info.filename)
    if (
        info.is_dir()
        or path.is_absolute()
        or ".." in path.parts
        or "\\" in info.filename
    ):
        raise ThemePackError("Unsafe archive path.")
    if info.flag_bits & 1 or info.file_size > MAX_MEMBER_BYTES:
        raise ThemePackError("Unsafe archive member.")
    if (info.external_attr >> 16) & 0o170000 == SYMLINK_FILE_TYPE:
        raise ThemePackError("Symbolic links are forbidden.")
    compressed = max(1, info.compress_size)
    if info.file_size / compressed > MAX_COMPRESSION_RATIO:
        raise ThemePackError("Suspicious compression ratio.")


def _png_dimensions(data: bytes) -> tuple[int, int]:
    if len(data) < MIN_PNG_HEADER_LENGTH or data[:8] != b"\x89PNG\r\n\x1a\n" or data[12:16] != b"IHDR":
        raise ThemePackError("Invalid PNG background.")
    return struct.unpack(">II", data[16:24])


def _svg_dimensions(data: bytes) -> tuple[int, int]:
    lowered = data.lower()
    if b"<!doctype" in lowered or b"<!entity" in lowered:
        raise ThemePackError("DTD is forbidden in SVG.")
    try:
        root = ElementTree.fromstring(data)
    except ElementTree.ParseError:
        raise ThemePackError("Invalid SVG background.") from None
    _validate_svg_tree(root)
    return _declared_svg_dimensions(root)


def _validate_svg_tree(root: ElementTree.Element) -> None:
    for element in root.iter():
        tag = element.tag.rsplit("}", 1)[-1]
        if tag not in SVG_ELEMENTS:
            raise ThemePackError("Forbidden SVG element.")
        for name, value in element.attrib.items():
            local = name.rsplit("}", 1)[-1].lower()
            lowered_value = value.lower()
            if local.startswith("on") or local in {"href", "src"}:
                raise ThemePackError("SVG links and events are forbidden.")
            if (
                "url(" in lowered_value
                or "javascript:" in lowered_value
                or "data:" in lowered_value
            ):
                raise ThemePackError("External SVG content is forbidden.")


def _declared_svg_dimensions(root: ElementTree.Element) -> tuple[int, int]:
    width = root.attrib.get("width", "")
    height = root.attrib.get("height", "")
    try:
        dimensions = int(float(width)), int(float(height))
    except ValueError:
        viewbox = root.attrib.get("viewBox", "").split()
        if len(viewbox) != VIEWBOX_DIMENSIONS:
            raise ThemePackError("SVG requires numeric dimensions.") from None
        try:
            dimensions = int(float(viewbox[2])), int(float(viewbox[3]))
        except ValueError:
            raise ThemePackError("Invalid SVG dimensions.") from None
    return dimensions


def _validate_dimensions(width: int, height: int) -> None:
    if not (1 <= width <= MAX_IMAGE_WIDTH and 1 <= height <= MAX_IMAGE_HEIGHT):
        raise ThemePackError("Background dimensions are outside the allowed range.")


def _text_map(value: object) -> frozendict[str, str]:
    if not isinstance(value, dict) or set(value) != LANGUAGES:
        raise ThemePackError("All four localized display names are required.")
    result = {str(key): str(text).strip() for key, text in value.items()}
    if any(not text or len(text) > MAX_NAME_LENGTH for text in result.values()):
        raise ThemePackError("Invalid localized display name.")
    return frozendict(result)


def _validated_archive_names(infos: list[zipfile.ZipInfo]) -> set[str]:
    names = {info.filename for info in infos}
    if len(names) != len(infos) or MANIFEST not in names or not names <= MEMBERS:
        raise ThemePackError("Theme archive contains unexpected members.")
    for info in infos:
        _safe_member(info)
    if sum(info.file_size for info in infos) > MAX_TOTAL_BYTES:
        raise ThemePackError("Theme archive expands beyond the allowed size.")
    return names


def _validated_manifest(value: object) -> dict[str, object]:
    if not isinstance(value, dict) or set(value) != MANIFEST_KEYS:
        raise ThemePackError("Invalid theme manifest.")
    if value["format"] != FORMAT or value["version"] != VERSION:
        raise ThemePackError("Unsupported theme format.")
    return value


def _validated_colors(value: object) -> frozendict[str, str]:
    if not isinstance(value, dict):
        raise ThemePackError("Invalid theme colors.")
    colors = {str(key): str(color) for key, color in value.items()}
    if any(not isinstance(raw, str) for raw in value.values()) or any(
        not COLOR.fullmatch(color) for color in colors.values()
    ):
        raise ThemePackError("Invalid theme colors.")
    known = {key: color for key, color in colors.items() if key in DEFAULT_TOKENS}
    return frozendict({**DEFAULT_TOKENS, **known})


def _validated_background(
    archive: zipfile.ZipFile,
    names: set[str],
    value: object,
) -> str | None:
    if value is None:
        return None
    if value not in {"assets/background.svg", "assets/background.png"}:
        raise ThemePackError("Invalid theme background path.")
    if value not in names:
        raise ThemePackError("Theme background is missing.")
    data = archive.read(value)
    dimensions = (
        _svg_dimensions(data) if value.endswith(".svg") else _png_dimensions(data)
    )
    _validate_dimensions(*dimensions)
    return value


def _validated_source(value: object) -> tuple[str, str, str, str]:
    if not isinstance(value, dict) or set(value) != SOURCE_KEYS:
        raise ThemePackError("Invalid theme source declaration.")
    channel = value["channel"]
    kind = value["kind"]
    author = value["author"]
    license_name = value["license"]
    if channel not in SOURCE_CHANNELS or kind not in SOURCE_KINDS:
        raise ThemePackError("Invalid theme source declaration.")
    if value["reference_included"] is not False:
        raise ThemePackError("Reference assets must not be included.")
    if not isinstance(author, str) or not SOURCE_TEXT.fullmatch(author.strip()):
        raise ThemePackError("Invalid theme source declaration.")
    if not isinstance(license_name, str) or not SOURCE_TEXT.fullmatch(license_name.strip()):
        raise ThemePackError("Invalid theme source declaration.")
    return str(channel), str(kind), author.strip(), license_name.strip()


def _theme_from_manifest(
    archive: zipfile.ZipFile,
    names: set[str],
    manifest: dict[str, object],
) -> ThemePack:
    theme_id = str(manifest["id"])
    if not IDENTIFIER.fullmatch(theme_id):
        raise ThemePackError("Invalid theme identifier.")
    font = str(manifest["font"])
    if not FONT.fullmatch(font):
        raise ThemePackError("Invalid theme font.")
    radius = manifest["radius"]
    if not isinstance(radius, int) or isinstance(radius, bool) or not 0 <= radius <= MAX_RADIUS:
        raise ThemePackError("Invalid theme radius.")
    source_channel, source_kind, author, license_name = _validated_source(
        manifest["source"]
    )
    return ThemePack(
        theme_id,
        _text_map(manifest["display_names"]),
        _validated_colors(manifest["colors"]),
        font,
        radius,
        _validated_background(archive, names, manifest["background"]),
        source_channel,
        source_kind,
        author,
        license_name,
    )


def inspect_theme_pack(source: Path) -> ThemePack:
    path = Path(source)
    if not path.is_file() or path.stat().st_size > MAX_ARCHIVE_BYTES:
        raise ThemePackError("Theme archive size is invalid.")
    try:
        with zipfile.ZipFile(path) as archive:
            infos = archive.infolist()
            names = _validated_archive_names(infos)
            manifest = _validated_manifest(
                json.loads(archive.read(MANIFEST).decode("utf-8"))
            )
            expected_names = {MANIFEST}
            if manifest["background"] is not None:
                expected_names.add(str(manifest["background"]))
            if names != expected_names:
                raise ThemePackError("Every theme asset must be referenced.")
            return _theme_from_manifest(archive, names, manifest)
    except (
        OSError,
        zipfile.BadZipFile,
        UnicodeError,
        json.JSONDecodeError,
        KeyError,
        TypeError,
    ):
        raise ThemePackError("Invalid theme archive.") from None


def _atomic_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, delete=False
    ) as temporary:
        json.dump(payload, temporary, ensure_ascii=False, sort_keys=True)
        temporary.flush()
        os.fsync(temporary.fileno())
        temporary_path = Path(temporary.name)
    try:
        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)


def install_theme_pack(source: Path, store: Path) -> ThemePack:
    """Validate and atomically install one self-contained pack.

    Installation deliberately does not activate the theme.  Preview and the
    control panel's global Save action own that separate state transition.
    """

    theme = inspect_theme_pack(source)
    packages = Path(store) / "packages"
    packages.mkdir(parents=True, exist_ok=True)
    destination = packages / f"{theme.theme_id}.mohan-theme"
    with NamedTemporaryFile("wb", dir=packages, delete=False) as temporary:
        temporary.write(Path(source).read_bytes())
        temporary.flush()
        os.fsync(temporary.fileno())
        temporary_path = Path(temporary.name)
    try:
        os.replace(temporary_path, destination)
    finally:
        temporary_path.unlink(missing_ok=True)
    return theme


def list_installed_themes(store: Path) -> tuple[ThemePack, ...]:
    packages = Path(store) / "packages"
    if not packages.is_dir():
        return ()
    return tuple(
        inspect_theme_pack(path) for path in sorted(packages.glob("*.mohan-theme"))
    )


def apply_theme(theme_id: str, store: Path) -> ThemePack:
    """Persist one previously installed theme after an explicit Save action."""

    if not IDENTIFIER.fullmatch(theme_id):
        raise ThemePackError("Invalid theme identifier.")
    source = Path(store) / "packages" / f"{theme_id}.mohan-theme"
    theme = inspect_theme_pack(source)
    if theme.theme_id != theme_id:
        raise ThemePackError("Theme identifier does not match its package.")
    _atomic_json(Path(store) / "active.json", {"theme_id": theme_id})
    return theme


def selected_theme_id(store: Path) -> str:
    """Return a valid active ID, safely falling back when a pack is missing."""

    active = Path(store) / "active.json"
    if not active.is_file():
        return "builtin"
    try:
        payload = json.loads(active.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return "builtin"
    if not isinstance(payload, dict) or set(payload) != {"theme_id"}:
        return "builtin"
    theme_id = str(payload["theme_id"])
    if theme_id == "builtin":
        return theme_id
    package = Path(store) / "packages" / f"{theme_id}.mohan-theme"
    try:
        theme = inspect_theme_pack(package)
    except ThemePackError:
        return "builtin"
    return theme_id if theme.theme_id == theme_id else "builtin"


def remove_theme_pack(theme_id: str, store: Path) -> None:
    """Remove one inactive installed pack without touching any other data."""

    if theme_id == "builtin":
        raise ThemePackError("The built-in theme cannot be removed.")
    if not IDENTIFIER.fullmatch(theme_id):
        raise ThemePackError("Invalid theme identifier.")
    if selected_theme_id(store) == theme_id:
        raise ThemePackError("An active theme cannot be removed.")
    package = Path(store) / "packages" / f"{theme_id}.mohan-theme"
    theme = inspect_theme_pack(package)
    if theme.theme_id != theme_id:
        raise ThemePackError("Theme identifier does not match its package.")
    try:
        package.unlink()
    except OSError:
        raise ThemePackError("Unable to remove theme package.") from None


def restore_builtin_theme(store: Path) -> None:
    _atomic_json(Path(store) / "active.json", {"theme_id": "builtin"})


def materialize_theme_background(theme_id: str, store: Path) -> Path | None:
    """Write the single validated background member to a private cache path."""

    if theme_id == "builtin":
        return None
    if not IDENTIFIER.fullmatch(theme_id):
        raise ThemePackError("Invalid theme identifier.")
    source = Path(store) / "packages" / f"{theme_id}.mohan-theme"
    theme = inspect_theme_pack(source)
    if theme.theme_id != theme_id:
        raise ThemePackError("Theme identifier does not match its package.")
    if theme.background is None:
        return None
    suffix = Path(theme.background).suffix.casefold()
    if suffix not in {".png", ".svg"}:
        raise ThemePackError("Invalid theme background path.")
    try:
        with zipfile.ZipFile(source) as archive:
            data = archive.read(theme.background)
    except (OSError, KeyError, zipfile.BadZipFile):
        raise ThemePackError("Unable to read theme background.") from None
    cache = Path(store) / "cache"
    cache.mkdir(parents=True, exist_ok=True)
    destination = cache / f"{theme_id}{suffix}"
    with NamedTemporaryFile("wb", dir=cache, delete=False) as temporary:
        temporary.write(data)
        temporary.flush()
        os.fsync(temporary.fileno())
        temporary_path = Path(temporary.name)
    try:
        os.replace(temporary_path, destination)
    finally:
        temporary_path.unlink(missing_ok=True)
    return destination


def build_stylesheet(theme: ThemePack) -> str:
    """Render only stable widget-role selectors; page structure stays application-owned."""

    token = theme.tokens
    window_text = _readable_foreground(token["window"], token["text"])
    card_text = _readable_foreground(token["card"], token["text"])
    surface_text = _readable_foreground(token["surface"], token["text"])
    action_text = _readable_foreground(token["primary"], token["surface"])
    return (
        f"QWidget {{ color:{window_text}; font-family:'{theme.font_family}'; }}"
        f"QDialog, QMainWindow {{ background:{token['window']}; }}"
        f"QFrame {{ background:{token['card']}; border:1px solid {token['border']};"
        f" border-radius:{theme.radius}px; }}"
        f"QFrame QLabel {{ color:{card_text}; }}"
        f"QPushButton {{ background:{token['primary']}; color:{action_text};"
        f" border-radius:{theme.radius}px; }}"
        f"QLineEdit, QTextEdit, QComboBox, QSpinBox {{ background:{token['surface']};"
        f" color:{surface_text}; border:1px solid {token['border']};"
        f" border-radius:{theme.radius}px; }}"
        f"QLineEdit:focus, QTextEdit:focus, QComboBox:focus {{ border-color:{token['focus']}; }}"
    )


def _readable_foreground(background: str, preferred: str) -> str:
    """Keep theme text readable when a package supplies a deep or pale surface."""

    if _contrast_ratio(background, preferred) >= MIN_CONTRAST_RATIO:
        return preferred
    candidates = ("#111827", "#FFFFFF")
    return max(candidates, key=lambda color: _contrast_ratio(background, color))


def _contrast_ratio(first: str, second: str) -> float:
    brighter, darker = sorted(
        (_relative_luminance(first), _relative_luminance(second)),
        reverse=True,
    )
    return (brighter + 0.05) / (darker + 0.05)


def _relative_luminance(color: str) -> float:
    channels = tuple(
        int(color[index : index + 2], 16) / 255.0
        for index in (1, 3, 5)
    )
    linear = tuple(
        channel / 12.92
        if channel <= SRGB_LINEAR_THRESHOLD
        else ((channel + 0.055) / 1.055) ** 2.4
        for channel in channels
    )
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]
