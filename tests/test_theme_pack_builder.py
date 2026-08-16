from __future__ import annotations

lazy import hashlib
lazy import json
lazy import struct
lazy import sys
lazy import zipfile
lazy from pathlib import Path
lazy from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

lazy from build_theme_pack import ThemePackBuildError, build_theme_pack

lazy from theme_pack import inspect_theme_pack


def _spec() -> dict:
    return {
        "id": "moonlit-blue",
        "display_names": {
            "zh-TW": "月映深藍",
            "zh-CN": "月映深蓝",
            "en": "Moonlit Blue",
            "ja-JP": "月映えの藍",
        },
        "colors": {"window": "#101828", "text": "#F4F7FB"},
        "font": "Noto Sans TC",
        "radius": 16,
        "source": {
            "channel": "user-authored",
            "kind": "original",
            "author": "Example Artist",
            "license": "MIT",
            "reference_included": False,
        },
    }


def _write_spec(path: Path, payload: dict) -> Path:
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path


def _png() -> bytes:
    return b"\x89PNG\r\n\x1a\n" + b"\0\0\0\rIHDR" + struct.pack(">II", 800, 600)


def _reject(spec: Path, output: Path, background: Path | None = None) -> None:
    try:
        build_theme_pack(spec, output, background)
    except ThemePackBuildError:
        assert not output.exists()
        assert not list(output.parent.glob(f".{output.name}.*.tmp"))
        return
    raise AssertionError("invalid theme build must fail closed")


def run() -> None:
    with TemporaryDirectory() as temporary:
        root = Path(temporary)
        spec = _write_spec(root / "theme.json", _spec())
        background = root / "background.png"
        background.write_bytes(_png())

        output = root / "theme.mohan-theme"
        theme = build_theme_pack(spec, output, background)
        assert theme == inspect_theme_pack(output)
        with zipfile.ZipFile(output) as archive:
            assert archive.namelist() == ["manifest.json", "assets/background.png"]
            assert all(info.date_time == (1980, 1, 1, 0, 0, 0) for info in archive.infolist())

        no_background = root / "plain.mohan-theme"
        assert build_theme_pack(spec, no_background).background is None
        with zipfile.ZipFile(no_background) as archive:
            assert archive.namelist() == ["manifest.json"]

        first = root / "first.mohan-theme"
        second = root / "second.mohan-theme"
        build_theme_pack(spec, first, background)
        build_theme_pack(spec, second, background)
        assert hashlib.sha256(first.read_bytes()).digest() == hashlib.sha256(second.read_bytes()).digest()

        dangerous = root / "dangerous.svg"
        dangerous.write_text(
            '<svg width="800" height="600" onload="bad()"><script>bad()</script></svg>',
            encoding="utf-8",
        )
        _reject(spec, root / "dangerous.mohan-theme", dangerous)

        missing_language = _spec()
        del missing_language["display_names"]["ja-JP"]
        _reject(
            _write_spec(root / "missing-language.json", missing_language),
            root / "missing-language.mohan-theme",
        )

        wrong_order = _spec()
        wrong_order["display_names"] = {
            "en": "Moonlit Blue",
            "zh-TW": "月映深藍",
            "zh-CN": "月映深蓝",
            "ja-JP": "月映えの藍",
        }
        _reject(
            _write_spec(root / "wrong-order.json", wrong_order),
            root / "wrong-order.mohan-theme",
        )

        failed_output = root / "failed.mohan-theme"
        invalid = _spec()
        invalid["colors"]["window"] = "not-a-color"
        _reject(_write_spec(root / "invalid.json", invalid), failed_output)
    print("THEME_PACK_BUILDER_OK")


if __name__ == "__main__":
    run()
