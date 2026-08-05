from __future__ import annotations

import ast
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QLineEdit


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from preview_app import (
    SUPPORTED_LANGUAGES,
    PreviewRuntime,
    PreviewWindow,
    _TEXT,
    validate_preview_contract,
)
from tools.build_preview_package import (
    APPIMAGETOOL_ASSET_ID,
    APPIMAGETOOL_SHA256,
    APPIMAGETOOL_SOURCE_COMMIT,
    APPIMAGETOOL_URL,
    _validate_version,
)
from version_info import APP_VERSION, FALLBACK_VERSION


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_preview_ui_contract() -> None:
    application = QApplication.instance() or QApplication(["preview-test"])
    assert application is not None
    expected_keys = frozenset(_TEXT["zh-TW"])
    assert SUPPORTED_LANGUAGES == ("zh-TW", "zh-CN", "en", "ja-JP")
    for language in SUPPORTED_LANGUAGES:
        assert frozenset(_TEXT[language]) == expected_keys
        assert all(str(value).strip() for value in _TEXT[language].values())

    for platform_id, display_name in (("macos", "macOS"), ("linux", "Linux")):
        runtime = PreviewRuntime(
            platform_id=platform_id,
            platform_name=display_name,
            version="2.2.0-rc.0",
            architecture="test-architecture",
        )
        window = PreviewWindow(runtime, language="zh-TW")
        validate_preview_contract(window)
        assert not window.windowIcon().isNull()
        assert not window.findChildren(QLineEdit)
        for language in SUPPORTED_LANGUAGES:
            window.apply_language(language)
            assert window.windowTitle() == _TEXT[language]["window_title"]
            assert window.close_button.text() == _TEXT[language]["close"]
            assert runtime.version in window.meta.text()
        window.close()


def test_preview_shell_is_isolated_from_full_application() -> None:
    tree = ast.parse(read("preview_app.py"))
    imported_roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_roots.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_roots.add(node.module.split(".", 1)[0])
    assert "app" not in imported_roots
    assert "assistant_core" not in imported_roots
    assert "azure_speech" not in imported_roots
    assert "cloud_connectors" not in imported_roots
    assert "oauth" not in imported_roots
    assert "realtime" not in imported_roots
    source = read("preview_app.py").lower()
    assert "qlineedit" not in source
    assert "api_key" not in source
    assert "client_secret" not in source


def test_source_smoke_rejects_wrong_embedded_version() -> None:
    with tempfile.TemporaryDirectory(prefix="mohan-preview-source-smoke-") as raw:
        marker = Path(raw) / "smoke.txt"
        command = [
            sys.executable,
            str(ROOT / "preview_app.py"),
            "--preview-platform=linux",
            f"--preview-smoke-output={marker}",
        ]
        valid = subprocess.run(
            command + [f"--preview-expected-version={APP_VERSION}"],
            check=False,
            env={**os.environ, "QT_QPA_PLATFORM": "offscreen"},
        )
        assert valid.returncode == 0
        assert marker.read_text(encoding="utf-8") == "PREVIEW_PACKAGE_SMOKE_OK"
        invalid = subprocess.run(
            command + ["--preview-expected-version=0.0.0-invalid"],
            check=False,
            env={**os.environ, "QT_QPA_PLATFORM": "offscreen"},
        )
        assert invalid.returncode == 2
        assert marker.read_text(encoding="utf-8") == "PREVIEW_PACKAGE_SMOKE_FAILED"


def test_build_tool_and_release_gate_are_pinned() -> None:
    assert re.fullmatch(r"[0-9a-f]{40}", APPIMAGETOOL_SOURCE_COMMIT)
    assert APPIMAGETOOL_ASSET_ID == "324406882"
    assert re.fullmatch(r"[0-9a-f]{64}", APPIMAGETOOL_SHA256)
    assert APPIMAGETOOL_URL.startswith(
        "https://github.com/AppImage/appimagetool/releases/download/"
    )
    build_source = read("tools/build_preview_package.py")
    assert 'os.symlink("/Applications"' in build_source
    assert '"hdiutil",' in build_source
    assert "APPIMAGETOOL_SHA256" in build_source
    assert '"arm64": "arm64"' in build_source
    assert '"x86_64": "x86_64"' in build_source
    assert "ROOT / 'LICENSE'" in build_source
    assert 'stage / "LICENSE.txt"' in build_source
    assert '"mohan-desktop-assistant"' in build_source
    _validate_version("2.2.0-rc.0")
    _validate_version("2.2.0-rc.1")
    for invalid in ("2.2.0", "2.2.0-rc", "2.2.0-rc.01", "2.1.0-rc.2"):
        try:
            _validate_version(invalid)
        except ValueError:
            pass
        else:
            raise AssertionError(f"invalid Preview version was accepted: {invalid}")

    release = read(".github/workflows/release.yml")
    preview = read(".github/workflows/preview-packages.yml")
    assert '"v2.2.0-rc.*"' in release
    assert "^v2\\.2\\.0-rc\\.[1-9][0-9]*$" in release
    assert "pull_request:" not in release
    assert "gh release create" in release
    assert "artifact-metadata: write" in release
    assert "--draft" in release
    assert 'gh release create "$tag" "${assets[@]}"' in release
    assert "/releases/tags/$tag" not in release
    assert "and .draft == true" in release
    assert "draft=false" in release
    assert "cleanup_failed_draft" in release
    assert "Draft Release assets differ from the exact verified set" in release
    assert "needs: [resolve-release, windows, macos-preview, linux-preview]" in release
    assert "commit: ${{ steps.source.outputs.commit }}" in release
    assert release.count("ref: ${{ needs.resolve-release.outputs.commit }}") == 5
    assert "Release tag changed after validation" in release
    assert "SHA256SUMS" in release
    assert "cyclonedx-bom==7.3.0" in release
    assert "actions/attest@" in release
    assert "pull_request:" in preview
    assert "gh release create" not in preview
    assert "retention-days: 14" in preview
    assert "runner: macos-15" in preview
    assert "runner: macos-15-intel" in preview
    assert "name: Cross-platform Preview package gate" in preview
    assert "if: ${{ always() }}" in preview
    assert "APPIMAGE_EXTRACT_AND_RUN" in read("tools/smoke_preview_package.py")
    assert "--appimage-extract" in read("tools/smoke_preview_package.py")
    assert "Contents\" / \"Resources\" / \"LICENSE" in read(
        "tools/smoke_preview_package.py"
    )
    assert "--expected-version 2.2.0-rc.0" in preview
    assert "--preview-expected-version" in read("preview_app.py")

    action_pattern = re.compile(r"^[ \t-]*uses:\s*([^\s#]+)", re.MULTILINE)
    for workflow in sorted((ROOT / ".github" / "workflows").glob("*.yml")):
        for reference in action_pattern.findall(workflow.read_text(encoding="utf-8")):
            if reference.startswith("./"):
                continue
            assert re.fullmatch(
                r"[^@]+@[0-9a-f]{40}", reference
            ), f"GitHub Action is not pinned to a full commit: {workflow.name}: {reference}"


def test_release_version_has_one_source_of_truth() -> None:
    assert FALLBACK_VERSION == "2.2.0-rc.1"
    tag = f"v{FALLBACK_VERSION}"
    assert (ROOT / "docs" / "releases" / f"{tag}.md").is_file()
    release = read(".github/workflows/release.yml")
    assert "from version_info import FALLBACK_VERSION" in release
    for guide in ("QUICKSTART.md", "README.md", "README.zh-CN.md", "README.ja.md"):
        text = read(guide)
        assert "MoHan-Desktop-Assistant-2.1.0-rc.1.exe" not in text
    assert 'FALLBACK_VERSION = "2.1.0-rc.1"' not in read("version_info.py")


def test_four_language_release_notes_and_boundaries() -> None:
    notes = read("docs/releases/v2.2.0-rc.1.md")
    expected_headings = (
        "## 繁體中文",
        "## 简体中文",
        "## English",
        "## 日本語",
    )
    positions = [notes.index(heading) for heading in expected_headings]
    assert positions == sorted(positions)
    for phrase in ("limited Preview", "功能受限", "機能限定"):
        assert phrase in notes
    guide = read("docs/PREVIEW-PACKAGES.md")
    for heading in expected_headings:
        assert heading in guide
    for forbidden_claim in ("feature parity achieved", "完整支援 macOS"):
        assert forbidden_claim not in guide


def main() -> None:
    test_preview_ui_contract()
    test_preview_shell_is_isolated_from_full_application()
    test_source_smoke_rejects_wrong_embedded_version()
    test_build_tool_and_release_gate_are_pinned()
    test_release_version_has_one_source_of_truth()
    test_four_language_release_notes_and_boundaries()
    print("PREVIEW_PACKAGING_OK")


if __name__ == "__main__":
    main()
