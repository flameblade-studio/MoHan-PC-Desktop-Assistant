from __future__ import annotations

lazy import argparse
lazy import json
lazy import os
lazy import zipfile
lazy from pathlib import Path
lazy from tempfile import NamedTemporaryFile

lazy from theme_pack import ThemePack, ThemePackError, inspect_theme_pack

LANGUAGE_ORDER = ("zh-TW", "zh-CN", "en", "ja-JP")
SPEC_KEYS = frozenset({"id", "display_names", "colors", "font", "radius", "source"})
FIXED_TIMESTAMP = (1980, 1, 1, 0, 0, 0)
COMPRESSION_LEVEL = 9


class ThemePackBuildError(RuntimeError):
    """A safe, user-facing build failure that never includes specification data."""


def _load_spec(path: Path) -> dict[str, object]:
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        raise ThemePackBuildError(f"Unable to read valid UTF-8 JSON: {path}") from None
    if not isinstance(payload, dict) or set(payload) != SPEC_KEYS:
        raise ThemePackBuildError(f"Theme specification has invalid fields: {path}")
    names = payload.get("display_names")
    if not isinstance(names, dict) or tuple(names) != LANGUAGE_ORDER:
        raise ThemePackBuildError(
            f"Display names must be ordered zh-TW, zh-CN, en, ja-JP: {path}"
        )
    return payload


def _background(path: Path | None) -> tuple[str | None, bytes | None]:
    if path is None:
        return None, None
    source = Path(path)
    suffix = source.suffix.lower()
    if suffix not in {".png", ".svg"}:
        raise ThemePackBuildError(f"Background must be a local PNG or SVG: {source}")
    try:
        data = source.read_bytes()
    except OSError:
        raise ThemePackBuildError(f"Unable to read background: {source}") from None
    return f"assets/background{suffix}", data


def _manifest(spec: dict[str, object], background: str | None) -> bytes:
    payload = {
        "format": "mohan-theme-pack",
        "version": 2,
        "id": spec["id"],
        "display_names": spec["display_names"],
        "colors": spec["colors"],
        "font": spec["font"],
        "radius": spec["radius"],
        "background": background,
        "source": spec["source"],
    }
    text = json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return (text + "\n").encode("utf-8")


def _member(name: str) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(name, FIXED_TIMESTAMP)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.create_system = 0
    info.external_attr = 0o600 << 16
    return info


def _write_archive(
    path: Path,
    manifest: bytes,
    background_name: str | None,
    background_data: bytes | None,
) -> None:
    with zipfile.ZipFile(
        path,
        "w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=COMPRESSION_LEVEL,
        strict_timestamps=True,
    ) as archive:
        archive.writestr(_member("manifest.json"), manifest, compresslevel=COMPRESSION_LEVEL)
        if background_name is not None and background_data is not None:
            archive.writestr(
                _member(background_name),
                background_data,
                compresslevel=COMPRESSION_LEVEL,
            )


def build_theme_pack(
    specification: Path,
    output: Path,
    background: Path | None = None,
) -> ThemePack:
    """Build, self-validate, and atomically publish one reproducible theme pack."""

    destination = Path(output)
    if destination.suffix.lower() != ".mohan-theme":
        raise ThemePackBuildError(f"Output must use .mohan-theme: {destination}")
    spec = _load_spec(Path(specification))
    background_name, background_data = _background(background)
    manifest = _manifest(spec, background_name)
    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
        with NamedTemporaryFile(
            "wb",
            prefix=f".{destination.name}.",
            suffix=".tmp",
            dir=destination.parent,
            delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)
        try:
            _write_archive(
                temporary_path,
                manifest,
                background_name,
                background_data,
            )
            theme = inspect_theme_pack(temporary_path)
            # Windows requires a writable descriptor for ``os.fsync``.  Open
            # the completed archive without truncating it so the same durable
            # atomic-publication path works on every supported platform.
            with temporary_path.open("rb+") as archive_file:
                os.fsync(archive_file.fileno())
            os.replace(temporary_path, destination)
            return theme
        finally:
            temporary_path.unlink(missing_ok=True)
    except (OSError, ThemePackError, zipfile.BadZipFile):
        raise ThemePackBuildError(f"Theme pack build failed: {destination}") from None


def main() -> int:
    parser = argparse.ArgumentParser(description="Build one self-contained MoHan theme pack.")
    parser.add_argument("specification", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--background", type=Path)
    arguments = parser.parse_args()
    try:
        build_theme_pack(arguments.specification, arguments.output, arguments.background)
    except ThemePackBuildError as error:
        parser.exit(2, f"error: {error}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
