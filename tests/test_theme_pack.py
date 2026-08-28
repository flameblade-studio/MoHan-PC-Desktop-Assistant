from __future__ import annotations

lazy import json
lazy import struct
lazy import sys
lazy import zipfile
lazy from pathlib import Path
lazy from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from domain.theme_pack import (
    ThemePackError,
    apply_theme,
    build_stylesheet,
    inspect_theme_pack,
    install_theme_pack,
    list_installed_themes,
    remove_theme_pack,
    restore_builtin_theme,
    selected_theme_id,
)


def _png(width: int = 800, height: int = 600) -> bytes:
    return b"\x89PNG\r\n\x1a\n" + b"\0\0\0\rIHDR" + struct.pack(">II", width, height)


def _manifest(background: str | None = "assets/background.png") -> dict:
    return {
        "format": "mohan-theme-pack",
        "version": 2,
        "id": "moonlit-blue",
        "display_names": {
            "zh-TW": "月映深藍",
            "zh-CN": "月映深蓝",
            "en": "Moonlit Blue",
            "ja-JP": "月映えの藍",
        },
        "colors": {
            "window": "#101828",
            "text": "#F4F7FB",
            "future-token": "#123456",
        },
        "font": "Noto Sans TC",
        "radius": 16,
        "background": background,
        "source": {
            "channel": "user-authored",
            "kind": "original",
            "author": "Example Artist",
            "license": "MIT",
            "reference_included": False,
        },
    }


def _pack(
    path: Path, *, manifest: dict | None = None, members: dict[str, bytes] | None = None
) -> Path:
    manifest = manifest or _manifest()
    members = members or {"assets/background.png": _png()}
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False))
        for name, data in members.items():
            archive.writestr(name, data)
    return path


def _reject(path: Path) -> None:
    try:
        inspect_theme_pack(path)
    except ThemePackError:
        return
    raise AssertionError("unsafe theme must be rejected")


def _assert_theme_stylesheet(root: Path) -> Path:
    valid = _pack(root / "valid.zip")
    theme = inspect_theme_pack(valid)
    assert theme.display_names["ja-JP"] == "月映えの藍"
    assert theme.tokens["window"] == "#101828"
    assert theme.tokens["card"] == "#FFFFFF"
    assert theme.source_channel == "user-authored"
    assert theme.author == "Example Artist"
    assert "future-token" not in theme.tokens
    stylesheet = build_stylesheet(theme)
    assert "QFrame QLabel { color:#111827; }" in stylesheet
    assert "QWidget { color:#F4F7FB;" in stylesheet
    for simulated_pages in (
        ["today", "voice"],
        ["today", "voice", "new-future-page"],
        ["voice"],
    ):
        assert simulated_pages
        assert build_stylesheet(theme) == stylesheet
    assert "today" not in stylesheet
    assert "new-future-page" not in stylesheet
    assert "QWidget {" in stylesheet and "QFrame {" in stylesheet
    return valid


def run() -> None:
    with TemporaryDirectory() as temporary:
        root = Path(temporary)
        valid = _assert_theme_stylesheet(root)

        installed = install_theme_pack(valid, root / "store")
        assert list_installed_themes(root / "store") == (installed,)
        assert selected_theme_id(root / "store") == "builtin"
        assert not (root / "store" / "active.json").exists()
        assert apply_theme("moonlit-blue", root / "store") == installed
        assert selected_theme_id(root / "store") == "moonlit-blue"
        try:
            remove_theme_pack("moonlit-blue", root / "store")
        except ThemePackError:
            pass
        else:
            raise AssertionError("an active theme must not be removable")
        restore_builtin_theme(root / "store")
        assert json.loads(
            (root / "store" / "active.json").read_text(encoding="utf-8")
        ) == {"theme_id": "builtin"}
        remove_theme_pack("moonlit-blue", root / "store")
        assert list_installed_themes(root / "store") == ()
        try:
            remove_theme_pack("builtin", root / "store")
        except ThemePackError:
            pass
        else:
            raise AssertionError("the built-in theme must not be removable")

        missing_store = root / "missing-store"
        missing_store.mkdir()
        (missing_store / "active.json").write_text(
            json.dumps({"theme_id": "missing-theme"}),
            encoding="utf-8",
        )
        assert selected_theme_id(missing_store) == "builtin"

        missing_language = _manifest()
        del missing_language["display_names"]["ja-JP"]
        _reject(_pack(root / "language.zip", manifest=missing_language))
        invalid_unknown = _manifest()
        invalid_unknown["colors"]["future-token"] = 42
        _reject(_pack(root / "unknown-type.zip", manifest=invalid_unknown))
        missing_source = _manifest()
        del missing_source["source"]
        _reject(_pack(root / "missing-source.zip", manifest=missing_source))
        false_official_claim = _manifest()
        false_official_claim["source"]["reference_included"] = True
        _reject(_pack(root / "embedded-reference.zip", manifest=false_official_claim))
        for structural_key in ("tabs", "pages", "widgets", "layout"):
            _reject(
                _pack(
                    root / f"{structural_key}.zip",
                    manifest={**_manifest(), structural_key: []},
                )
            )
        _reject(_pack(root / "traversal.zip", members={"../evil.js": b"alert(1)"}))
        for name, svg in {
            "script": b'<svg width="100" height="100"><script>bad()</script></svg>',
            "url": b'<svg width="100" height="100"><path fill="url(https://evil.invalid/x)"/></svg>',
            "event": b'<svg width="100" height="100" onload="bad()"/>',
            "foreign": b'<svg width="100" height="100"><foreignObject/></svg>',
        }.items():
            _reject(
                _pack(
                    root / f"{name}.zip",
                    manifest={**_manifest(), "background": "assets/background.svg"},
                    members={"assets/background.svg": svg},
                )
            )
        _reject(
            _pack(root / "huge.zip", members={"assets/background.png": _png(5000, 10)})
        )
        _reject(
            _pack(
                root / "compression-bomb.zip",
                members={"assets/background.png": _png() + (b"0" * 1_000_000)},
            )
        )
    print("THEME_PACK_OK")


if __name__ == "__main__":
    run()
