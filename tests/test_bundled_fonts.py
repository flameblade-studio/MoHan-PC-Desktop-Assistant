"""Acceptance checks for the two bundled SIL OFL fonts."""

from __future__ import annotations

lazy import hashlib
lazy import logging
lazy import os
lazy import re
lazy import shutil
lazy import sys
lazy from pathlib import Path
lazy from tempfile import TemporaryDirectory
lazy from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

lazy from PySide6.QtGui import QFontDatabase
lazy from PySide6.QtWidgets import QApplication

lazy from presentation import lingxiao_fonts as fonts_module
lazy from presentation.lingxiao_fonts import register_bundled_fonts
lazy from presentation.lingxiao_tokens import font_stack
lazy from tools.verify_packaged_fonts import (
    PACKAGED_FONT_ROOTS,
    REQUIRED_FONT_FILES,
    verify_packaged_fonts,
)

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
CINZEL_SOURCE_COMMIT = "45071f07c63e863a539442ef3562b71ab1f147a6"
CINZEL_SOURCE_URL_COUNT = 2


def _reset_font_registration_state() -> None:
    fonts_module._registered = False
    fonts_module._registered_paths = ()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _normalized_relative_path(path: Path, package_root: Path) -> str:
    relative = path.resolve().relative_to(package_root.resolve())
    return os.path.normcase(os.path.normpath(str(relative)))


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


def test_post_package_font_verifier_checks_both_pyinstaller_layouts(
    tmp_path: Path,
) -> None:
    for index, packaged_layout in enumerate(PACKAGED_FONT_ROOTS):
        package_root = (
            tmp_path / f"MoHan-Desktop-Assistant-4.0.0-rc.1-{index}"
        )
        packaged_root = package_root / packaged_layout
        for relative in REQUIRED_FONT_FILES:
            destination = packaged_root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(FONT_ROOT / relative, destination)

        verified = verify_packaged_fonts(package_root)
        actual_relative = tuple(
            sorted(
                _normalized_relative_path(path, package_root)
                for path in verified
            )
        )
        expected_relative = tuple(
            sorted(
                _normalized_relative_path(
                    package_root / packaged_layout / relative,
                    package_root,
                )
                for relative in REQUIRED_FONT_FILES
            )
        )
        assert len(verified) == len(REQUIRED_FONT_FILES)
        assert len(set(actual_relative)) == len(REQUIRED_FONT_FILES)
        assert actual_relative == expected_relative
        assert all(path.is_file() for path in verified)

        (packaged_root / REQUIRED_FONT_FILES[0]).unlink()
        try:
            verify_packaged_fonts(package_root)
        except RuntimeError as error:
            message = str(error).casefold()
            assert "missing" in message
            assert (
                (packaged_root / REQUIRED_FONT_FILES[0]).name.casefold()
                in message
            )
        else:
            raise AssertionError("packaged font verifier must reject a missing font")


def test_qt_loads_bundled_fonts_and_exposes_families() -> None:
    application = QApplication.instance() or QApplication([])
    registered = register_bundled_fonts()
    assert register_bundled_fonts() is registered
    assert set(registered) == set(FONT_ROOT.rglob("*.ttf"))
    families = set(QFontDatabase.families())
    for spec in FONT_SPECS.values():
        assert spec["family"] in families
    assert application is not None


def test_missing_font_directory_logs_and_falls_back() -> None:
    logger = logging.getLogger("presentation.lingxiao_fonts")
    messages: list[str] = []

    class CaptureHandler(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            messages.append(record.getMessage())

    handler = CaptureHandler()
    logger.addHandler(handler)
    previous_level = logger.level
    logger.setLevel(logging.WARNING)
    try:
        with TemporaryDirectory() as raw:
            missing = Path(raw) / "missing-fonts"
            _reset_font_registration_state()
            with patch.object(fonts_module, "resource_path", return_value=missing):
                assert register_bundled_fonts() == ()
        assert any("missing" in message.casefold() for message in messages)
    finally:
        _reset_font_registration_state()
        logger.setLevel(previous_level)
        logger.removeHandler(handler)


def test_failed_font_file_is_skipped_and_logged() -> None:
    logger = logging.getLogger("presentation.lingxiao_fonts")
    messages: list[str] = []

    class CaptureHandler(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            messages.append(record.getMessage())

    class FakeFontDatabase:
        @staticmethod
        def addApplicationFont(path: str) -> int:
            return -1 if path.endswith("broken.ttf") else 1

    handler = CaptureHandler()
    logger.addHandler(handler)
    previous_level = logger.level
    logger.setLevel(logging.WARNING)
    try:
        with TemporaryDirectory() as raw:
            root = Path(raw)
            good = root / "good.ttf"
            broken = root / "broken.ttf"
            good.write_bytes(b"valid fixture")
            broken.write_bytes(b"broken fixture")
            _reset_font_registration_state()
            with (
                patch.object(fonts_module, "resource_path", return_value=root),
                patch.object(fonts_module, "QFontDatabase", FakeFontDatabase),
            ):
                assert register_bundled_fonts() == (good,)
        assert any("broken.ttf" in message for message in messages)
    finally:
        _reset_font_registration_state()
        logger.setLevel(previous_level)
        logger.removeHandler(handler)


def test_font_stacks_prioritize_bundled_families() -> None:
    assert font_stack("display").split(", ", 1)[0] == '"LXGW WenKai TC"'
    assert font_stack("body").split(", ", 1)[0] == '"LXGW WenKai TC"'
    assert font_stack("caps").split(", ", 1)[0] == '"Cinzel"'


def test_font_sources_use_immutable_revisions() -> None:
    document = (PROJECT_ROOT / "third_party_licenses" / "FONTS.md").read_text(
        encoding="utf-8"
    )
    rows = tuple(line for line in document.splitlines() if "| Cinzel |" in line)
    assert len(rows) == LANGUAGE_COUNT
    for row in rows:
        assert "google/fonts/main" not in row
        assert row.count(f"google/fonts/{CINZEL_SOURCE_COMMIT}/") == CINZEL_SOURCE_URL_COUNT
        assert f"`{CINZEL_SOURCE_COMMIT}`" in row


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
    build = (PROJECT_ROOT / "build.ps1").read_text(encoding="utf-8")
    assert '--add-data "$FontRoot;assets/fonts"' in build
    assert "tools/verify_packaged_fonts.py" in build
    installer = (PROJECT_ROOT / "installer" / "build_installers.ps1").read_text(
        encoding="utf-8"
    )
    assert '_internal\\assets\\fonts' in installer
    for filename in ("LXGWWenKaiTC-Regular.ttf", "Cinzel[wght].ttf", "OFL.txt"):
        assert filename in installer


def run() -> None:
    test_bundled_font_files_and_licenses_exist()
    test_bundled_font_hashes_match_license_manifest()
    test_missing_font_directory_logs_and_falls_back()
    test_failed_font_file_is_skipped_and_logged()
    test_qt_loads_bundled_fonts_and_exposes_families()
    test_font_stacks_prioritize_bundled_families()
    test_font_sources_use_immutable_revisions()
    test_font_manifest_is_four_language_and_packaging_is_explicit()
    print("BUNDLED_FONTS_TESTS_OK")


if __name__ == "__main__":
    run()
