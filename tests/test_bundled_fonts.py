"""Acceptance checks for the two bundled SIL OFL fonts."""

from __future__ import annotations

lazy import hashlib
lazy import os
lazy import re
lazy import sys
lazy from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

lazy from PySide6.QtGui import QFontDatabase
lazy from PySide6.QtWidgets import QApplication

lazy from presentation.lingxiao_fonts import register_bundled_fonts
lazy from presentation.lingxiao_tokens import font_stack

FONT_ROOT = PROJECT_ROOT / "assets" / "fonts"
LANGUAGE_COUNT = 4
FONT_SPECS = {
    "LXGW-WenKai-TC": {
        "family": "LXGW WenKai TC",
        "font": "LXGWWenKaiTC-Regular.ttf",
        "license_sha256": "1a13783bf4337242834b60309cdcdbeb566ae3f923576fdbba8b78db9d174def",
    },
    "Cinzel": {
        "family": "Cinzel",
        "font": "Cinzel[wght].ttf",
        "license_sha256": "f2b3029aba64c378bf0963b62945eee15e564fe4330b934c8f2eb058282b5e83",
    },
}
SHA_PATTERN = re.compile(r"[0-9a-f]{64}")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _documented_hash(family: str, filename: str) -> str:
    document = (PROJECT_ROOT / "third_party_licenses" / "FONTS.md").read_text(
        encoding="utf-8"
    )
    for line in document.splitlines():
        if family in line and filename in line:
            match = SHA_PATTERN.search(line)
            if match:
                return match.group(0)
    raise AssertionError(f"Missing documented SHA-256 for {family}/{filename}")


def test_bundled_font_files_and_licenses_exist() -> None:
    for directory, spec in FONT_SPECS.items():
        root = FONT_ROOT / directory
        assert (root / spec["font"]).is_file()
        license_path = root / "OFL.txt"
        assert license_path.is_file()
        assert "Copyright" in license_path.read_text(encoding="utf-8")
        assert "SIL Open Font License, Version 1.1" in license_path.read_text(
            encoding="utf-8"
        )


def test_bundled_font_hashes_match_license_manifest() -> None:
    document = (PROJECT_ROOT / "third_party_licenses" / "FONTS.md").read_text(
        encoding="utf-8"
    )
    for directory, spec in FONT_SPECS.items():
        path = FONT_ROOT / directory / spec["font"]
        assert _sha256(path) == _documented_hash(directory, spec["font"])
        license_hash = _sha256(FONT_ROOT / directory / "OFL.txt")
        assert license_hash == spec["license_sha256"]
        assert license_hash in document


def test_qt_loads_bundled_fonts_and_exposes_families() -> None:
    application = QApplication.instance() or QApplication([])
    registered = register_bundled_fonts()
    assert register_bundled_fonts() is registered
    assert set(registered) == set(FONT_ROOT.rglob("*.ttf"))
    families = set(QFontDatabase.families())
    for spec in FONT_SPECS.values():
        assert spec["family"] in families
    assert application is not None


def test_font_stacks_prioritize_bundled_families() -> None:
    assert font_stack("display").split(", ", 1)[0] == '"LXGW WenKai TC"'
    assert font_stack("body").split(", ", 1)[0] == '"LXGW WenKai TC"'
    assert font_stack("caps").split(", ", 1)[0] == '"Cinzel"'


def test_font_manifest_is_four_language_and_packaging_is_explicit() -> None:
    document = (PROJECT_ROOT / "third_party_licenses" / "FONTS.md").read_text(
        encoding="utf-8"
    )
    for heading in ("## 繁體中文", "## 简体中文", "## English", "## 日本語"):
        assert heading in document
    assert document.count("| LXGW WenKai TC |") == LANGUAGE_COUNT
    assert document.count("| Cinzel |") == LANGUAGE_COUNT

    preview = (PROJECT_ROOT / "tools" / "build_preview_package.py").read_text(
        encoding="utf-8"
    )
    assert 'f"{FONT_ROOT}{data_separator}assets/fonts"' in preview
    installer = (PROJECT_ROOT / "installer" / "build_installers.ps1").read_text(
        encoding="utf-8"
    )
    for filename in ("LXGWWenKaiTC-Regular.ttf", "Cinzel[wght].ttf", "OFL.txt"):
        assert filename in installer


def run() -> None:
    test_bundled_font_files_and_licenses_exist()
    test_bundled_font_hashes_match_license_manifest()
    test_qt_loads_bundled_fonts_and_exposes_families()
    test_font_stacks_prioritize_bundled_families()
    test_font_manifest_is_four_language_and_packaging_is_explicit()
    print("BUNDLED_FONTS_TESTS_OK")


if __name__ == "__main__":
    run()
