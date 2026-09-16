from __future__ import annotations

lazy import ast
lazy import importlib
lazy import os
lazy import re
lazy import shutil
lazy import subprocess
lazy import sys
lazy import tempfile
lazy from pathlib import Path
lazy import pytest
lazy from PIL import Image

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

lazy from PySide6.QtWidgets import QApplication, QLineEdit

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

lazy from application.preview_app import validate_preview_runtime
lazy from domain.version_info import APP_VERSION, FALLBACK_VERSION
lazy from presentation.preview_app import (
    _TEXT,
    SUPPORTED_LANGUAGES,
    PreviewRuntime,
    PreviewWindow,
    validate_preview_contract,
)

FAILURE_EXIT_CODE = 2
COMMIT_REFERENCE_COUNT = 5
POSE_ATLAS_FLAG_COUNT = 4

lazy from tools.build_preview_package import (
    APPIMAGETOOL_ASSET_ID,
    APPIMAGETOOL_SHA256,
    APPIMAGETOOL_SOURCE_COMMIT,
    APPIMAGETOOL_URL,
    DASHBOARD_ARTWORK_RELATIVE,
    _validate_version,
)
lazy from tools.check_layered_imports import inspect_layered_imports
lazy from domain.constants import POSE_ATLAS_ROOT_NAME
lazy from tools.smoke_preview_package import _require_pose_atlas


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
            version="2.3.0-rc.0",
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


def test_preview_owners_and_compatibility_identity() -> None:
    presentation = importlib.import_module("presentation.preview_app")
    application = importlib.import_module("application.preview_app")

    assert presentation.PreviewWindow.__module__ == "presentation.preview_app"
    assert presentation.PreviewRuntime is application.PreviewRuntime
    assert presentation.validate_preview_runtime is application.validate_preview_runtime
    runtime = presentation.PreviewRuntime(
        platform_id="linux",
        platform_name="Linux",
        version="4.0.0",
        architecture="x86_64",
    )
    assert type(runtime) is application.PreviewRuntime


def test_preview_runtime_rejects_unverified_capabilities() -> None:
    runtime = PreviewRuntime(
        platform_id="linux",
        platform_name="Linux",
        version="4.0.0",
        architecture="x86_64",
        enabled_product_capabilities=frozenset({"secure_secret_storage"}),
    )
    try:
        validate_preview_runtime(runtime)
    except RuntimeError as error:
        assert "secure_secret_storage" in str(error)
    else:
        raise AssertionError("Preview capability validation must fail closed")


def test_preview_and_service_status_have_real_layer_owners() -> None:
    report = inspect_layered_imports(ROOT)
    targets = {"preview_app", "service_status_localization"}
    target_issues = tuple(
        issue
        for issue in report.issues
        if issue.module.rpartition(".")[2] in targets
        or any(target in issue.message for target in targets)
    )
    assert not target_issues, target_issues

    preview_tree = ast.parse(read("presentation/preview_app.py"))
    assert any(
        isinstance(node, ast.ClassDef) and node.name == "PreviewWindow"
        for node in preview_tree.body
    )
    assert any(
        isinstance(node, ast.FunctionDef) and node.name == "main"
        for node in preview_tree.body
    )

    status_tree = ast.parse(read("domain/service_status_localization.py"))
    defined = {
        node.name
        for node in status_tree.body
        if isinstance(node, (ast.ClassDef, ast.FunctionDef))
    }
    assert {"ServiceStatus", "service_status", "append_service_status"} <= defined

    for relative in (
        "application/camera_presence.py",
        "integrations/ai_client.py",
        "integrations/speech.py",
    ):
        source = read(relative)
        assert "from domain.service_status_localization import" in source
        assert "from service_status_localization import" not in source


def test_preview_shell_is_isolated_from_full_application() -> None:
    source_path = "presentation/preview_app.py"
    tree = ast.parse(read(source_path))
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
    source = read(source_path).lower()
    assert "qlineedit" not in source
    assert "api_key" not in source
    assert "client_secret" not in source


def test_source_smoke_rejects_wrong_embedded_version() -> None:
    with tempfile.TemporaryDirectory(prefix="mohan-preview-source-smoke-") as raw:
        marker = Path(raw) / "smoke.txt"
        command = [
            sys.executable,
            "-m",
            "presentation.preview_app",
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
        assert invalid.returncode == FAILURE_EXIT_CODE
        assert marker.read_text(encoding="utf-8") == "PREVIEW_PACKAGE_SMOKE_FAILED"


def test_build_tool_is_pinned() -> None:
    assert re.fullmatch(r"[0-9a-f]{40}", APPIMAGETOOL_SOURCE_COMMIT)
    assert APPIMAGETOOL_ASSET_ID == "324406882"
    assert re.fullmatch(r"[0-9a-f]{64}", APPIMAGETOOL_SHA256)
    assert APPIMAGETOOL_URL.startswith(
        "https://github.com/AppImage/appimagetool/releases/download/"
    )
    build_source = read("tools/build_preview_package.py")
    assert 'ROOT / "presentation" / "preview_app.py"' in build_source
    assert '"--paths"' in build_source
    assert 'os.symlink("/Applications"' in build_source
    assert '"hdiutil",' in build_source
    assert "def _create_dmg" in build_source
    assert "DMG_CREATE_ATTEMPTS = 3" in build_source
    assert "DMG_CREATE_RETRY_SECONDS = 3" in build_source
    assert "APPIMAGETOOL_SHA256" in build_source
    assert '"arm64": "arm64"' in build_source
    assert '"x86_64": "x86_64"' in build_source
    assert "ROOT / 'LICENSE'" in build_source
    assert 'stage / "LICENSE.txt"' in build_source
    assert '"mohan-desktop-assistant"' in build_source
    assert "POSE_ATLAS_ROOT" in build_source
    assert "LAYERED_POSE_ATLAS_ROOT" in build_source
    assert "LAYERED_EXPRESSION_ROOT" in build_source
    assert "POSE_ATLAS_RELATIVE_ROOT" in build_source
    assert "POSE_ATLAS_LAYERED_RELATIVE_ROOT" in build_source
    assert "assets/pose-atlas/v4" not in build_source
    assert "assets/expressions" in build_source
    assert "expected_full_body_layers = VIEW_RING_COUNT * FULL_BODY_LAYER_COUNT" in build_source
    assert "expected_half_body_layers = HALF_BODY_POSE_COUNT * FULL_BODY_LAYER_COUNT" in build_source
    assert "--require-pose-atlas" in build_source
    _validate_version("2.3.0-rc.0")
    _validate_version("2.3.0-rc.1")
    _validate_version("2.3.0-rc.2")
    _validate_version("2.3.0-rc.3")
    _validate_version("2.3.0-rc.5")
    _validate_version("2.3.0")
    _validate_version("3.0.0")
    for invalid in ("2.3", "2.3.0-rc", "2.3.0-rc.01", "v3.0.0"):
        try:
            _validate_version(invalid)
        except ValueError:
            pass
        else:
            raise AssertionError(f'Preview versions must satisfy validation: {invalid}')


def test_release_gate_is_pinned() -> None:
    release = read(".github/workflows/release.yml")
    preview = read(".github/workflows/preview-packages.yml")
    assert '"v*.*.*"' in release
    assert "^v[0-9]+\\.[0-9]+\\.[0-9]+$" in release
    assert "^v[0-9]+\\.[0-9]+\\.[0-9]+-rc\\.[1-9][0-9]*$" in release
    assert "pull_request:" not in release
    assert "gh release create" in release
    assert "artifact-metadata: write" in release
    assert "--draft" in release
    assert 'gh release create "${release_args[@]}"' in release
    assert "release_args+=(--prerelease)" in release
    assert 'prerelease="$EXPECTED_PRERELEASE"' in release
    assert "/releases/tags/$tag" not in release
    assert "and .draft == true" in release
    assert "draft=false" in release
    assert "cleanup_failed_draft" in release
    assert "Release assets differ from the exact verified set" in release
    assert "needs: [resolve-release, windows, macos-preview, linux-preview]" in release
    assert "commit: ${{ steps.source.outputs.commit }}" in release
    assert release.count("ref: ${{ needs.resolve-release.outputs.commit }}") == COMMIT_REFERENCE_COUNT
    assert "Release tag changed after validation" in release
    assert "SHA256SUMS" in release
    assert "cyclonedx-bom==7.3.0" in release
    assert 'python-version: "3.14.7"' in release
    assert release.count('python-version: "3.14.7"') == 1
    assert "--spec-version 1.7" in release
    assert "--output-reproducible" in release
    assert "tools/validate_release_sboms.py" in release
    assert "SBOM-Validation.json" in release
    assert "Performance-Evidence.zip" in release
    assert "Performance-Summary.json" in release
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
    assert 'Contents" / "Resources" / "LICENSE' in read(
        "tools/smoke_preview_package.py"
    )
    assert "--expected-version 2.3.0-rc.0" in preview
    assert "--preview-expected-version" in read("application/preview_app.py")
    assert release.count("--require-pose-atlas") == POSE_ATLAS_FLAG_COUNT
    assert "Preview package omitted PoseAtlas {POSE_ATLAS_ROOT_NAME} assets" in read(
        "tools/smoke_preview_package.py"
    )

    action_pattern = re.compile(r"^[ \t-]*uses:\s*([^\s#]+)", re.MULTILINE)
    for workflow in sorted((ROOT / ".github" / "workflows").glob("*.yml")):
        for reference in action_pattern.findall(workflow.read_text(encoding="utf-8")):
            if reference.startswith("./"):
                continue
            assert re.fullmatch(r"[^@]+@[0-9a-f]{40}", reference), (
                f'GitHub Action must be pinned to a full commit: {workflow.name}: {reference}'
            )


def test_release_version_has_one_source_of_truth() -> None:
    assert re.fullmatch(
        r"[0-9]+\.[0-9]+\.[0-9]+(?:-rc\.[1-9][0-9]*)?",
        FALLBACK_VERSION,
    )
    tag = f"v{FALLBACK_VERSION}"
    assert (ROOT / "docs" / "releases" / f"{tag}.md").is_file()
    release = read(".github/workflows/release.yml")
    assert "from version_info import FALLBACK_VERSION" not in release
    assert "domain/version_info.py" in release
    assert 'source_version="${source_versions[0]}"' in release
    assert (
        "Expected exactly one literal FALLBACK_VERSION in domain/version_info.py"
        in release
    )
    for guide in ("QUICKSTART.md", "README.md"):
        text = read(guide)
        assert "MoHan-Desktop-Assistant-2.1.0-rc.1.exe" not in text
    assert (
        'FALLBACK_VERSION = "2.1.0-rc.1"'
        not in read("domain/version_info.py")
    )


def test_four_language_release_notes_and_boundaries() -> None:
    notes = read(f"docs/releases/v{FALLBACK_VERSION}.md")
    expected_headings = (
        "## 繁體中文",
        "## 简体中文",
        "## English",
        "## 日本語",
    )
    positions = [notes.index(heading) for heading in expected_headings]
    assert positions == sorted(positions)
    assert re.search(r"limited(?:\s+cross-platform)?\s+Preview", notes)
    for phrase in ("功能受限", "機能限定"):
        assert phrase in notes
    guide = read("docs/PREVIEW-PACKAGES.md")
    for heading in expected_headings:
        assert heading in guide
    for forbidden_claim in ("feature parity achieved", "完整支援 macOS"):
        assert forbidden_claim not in guide



def test_pose_atlas_smoke_accepts_complete_duplicate_bundle_roots(tmp_path: Path) -> None:
    for duplicate in ("Contents/Resources", "Contents/Frameworks"):
        atlas = tmp_path / duplicate / "assets" / "pose-atlas" / POSE_ATLAS_ROOT_NAME
        atlas.mkdir(parents=True)
        for index in range(24):
            stem = f"yaw{index:03}-pitch+00"
            (atlas / f"{stem}.png").write_bytes(b"png")
            (atlas / f"{stem}.landmarks.json").write_text("{}", encoding="utf-8")
            (atlas / f"{stem}.hands.json").write_text("{}", encoding="utf-8")

    _require_pose_atlas(tmp_path)

@pytest.mark.parametrize("include_atlas", [True, False])
def test_packaged_native_overrides_remain_loadable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, include_atlas: bool,
) -> None:
    from infrastructure.core_hand_regions import load_core_hand_regions
    from tools import build_preview_package as builder

    application = QApplication.instance() or QApplication([])
    assert application is not None

    project = tmp_path / "project"
    bundle = tmp_path / "bundle"
    view = "yaw+045-pitch+00"
    files = [
        f"v5-body-overlays/{view}.png",
        f"v5-hand-overlays/{view}_left.png",
        f"v5-hand-overlays/{view}_right.png",
        f"v5-appearance-silhouettes/mohan.official.blue-white-hanfu/{view}.png",
        f"v5-appearance-replacement-masks/mohan.official.blue-white-hanfu/{view}.png",
    ]
    for name in files:
        path = project / "assets/pose-atlas" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        pixels = Image.new("RGBA", (1024, 1536))
        pixels.putpixel((610, 800), (200, 150, 120, 255))
        pixels.save(path)

    def package(command: list[str]) -> None:
        for index, argument in enumerate(command[:-1]):
            if argument != "--add-data":
                continue
            source_text, destination = command[index + 1].rsplit(os.pathsep, 1)
            source = Path(source_text)
            if source.is_dir() and source.is_relative_to(project):
                shutil.copytree(source, bundle / destination, dirs_exist_ok=True)

    monkeypatch.setattr(builder, "ROOT", project)
    monkeypatch.setattr(builder, "_run", package)
    monkeypatch.setattr(builder, "_write_build_info", lambda *_args: None)
    monkeypatch.setattr(builder, "verify_policy", lambda *_args: [])
    monkeypatch.setattr(builder, "verify_environment", lambda *_args: [])
    builder._pyinstaller(
        name="MoHanPreview", version="1.0.0", target="linux",
        icon=project / "icon.png", temp_root=tmp_path,
        pose_atlas_root=project / "assets/pose-atlas/v5-base" if include_atlas else None,
    )
    if not include_atlas:
        assert not (bundle / "assets/pose-atlas").exists()
        return
    for name in files:
        relative = Path("assets/pose-atlas") / name
        assert (bundle / relative).read_bytes() == (project / relative).read_bytes()
    region_for_view = load_core_hand_regions(bundle)
    assert region_for_view is not None
    assert region_for_view(view).boundingRect().getRect() == (610, 800, 1, 1)


def test_packaged_dashboard_artwork_is_loadable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    from tools import build_preview_package as builder

    project = tmp_path / "project"
    bundle = tmp_path / "bundle"
    relative = DASHBOARD_ARTWORK_RELATIVE
    source = project / relative
    source.parent.mkdir(parents=True)
    source.write_bytes((ROOT / relative).read_bytes())
    observed: list[tuple[Path, str]] = []

    def package(command: list[str]) -> None:
        for index, argument in enumerate(command[:-1]):
            if argument != "--add-data":
                continue
            source_text, destination = command[index + 1].rsplit(os.pathsep, 1)
            packaged_source = Path(source_text)
            observed.append((packaged_source, destination))
            if packaged_source != source:
                continue
            target = bundle / destination / packaged_source.name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(packaged_source, target)

    monkeypatch.setattr(builder, "ROOT", project)
    monkeypatch.setattr(builder, "_run", package)
    monkeypatch.setattr(builder, "_write_build_info", lambda *_args: None)
    monkeypatch.setattr(builder, "verify_policy", lambda *_args: [])
    monkeypatch.setattr(builder, "verify_environment", lambda *_args: [])
    builder._pyinstaller(
        name="MoHanPreview", version="1.0.0", target="linux",
        icon=project / "icon.png", temp_root=tmp_path, pose_atlas_root=None,
    )

    assert (source, relative.parent.as_posix()) in observed
    packaged = bundle / relative
    assert packaged.read_bytes() == source.read_bytes()
    with Image.open(packaged) as image, Image.open(source) as expected:
        assert image.size == expected.size
        assert image.mode == expected.mode


def main() -> None:
    test_preview_ui_contract()
    test_preview_owners_and_compatibility_identity()
    test_preview_runtime_rejects_unverified_capabilities()
    test_preview_and_service_status_have_real_layer_owners()
    test_preview_shell_is_isolated_from_full_application()
    test_source_smoke_rejects_wrong_embedded_version()
    test_build_tool_is_pinned()
    test_release_gate_is_pinned()
    test_release_version_has_one_source_of_truth()
    test_four_language_release_notes_and_boundaries()
    print("PREVIEW_PACKAGING_OK")


if __name__ == "__main__":
    main()


def test_packaged_makeup_state_masks_remain_verifiable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    from domain.outfit_pack_makeup import load_makeup_safe_regions, verify_makeup_layers
    from tools import build_preview_package as builder

    bundle = tmp_path / "bundle"

    def package(command: list[str]) -> None:
        for index, argument in enumerate(command[:-1]):
            if argument != "--add-data":
                continue
            source_text, destination = command[index + 1].rsplit(os.pathsep, 1)
            source = Path(source_text)
            if not source.is_relative_to(ROOT / "assets"):
                continue
            if source.name not in {
                "makeup-safe-regions.json", "makeup-foundation-safe-regions",
                "makeup-eye-apertures", "official-packs",
            }:
                continue
            target = bundle / destination
            if source.is_dir():
                shutil.copytree(source, target)
            else:
                target.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target / source.name)

    monkeypatch.setattr(builder, "_run", package)
    monkeypatch.setattr(builder, "_write_build_info", lambda *_args: None)
    monkeypatch.setattr(builder, "verify_policy", lambda *_args: [])
    monkeypatch.setattr(builder, "verify_environment", lambda *_args: [])
    builder._pyinstaller(
        name="MoHanPreview", version="1.0.0", target="linux",
        icon=tmp_path / "icon.png", temp_root=tmp_path,
        pose_atlas_root=None,
    )
    regions = load_makeup_safe_regions(bundle / "assets/makeup-safe-regions.json")
    front = regions["yaw+000-pitch+00"]
    assert set(front.foundation_masks) == {"rest", "half", "closed"}
    assert set(front.eye_aperture_masks) == {"rest", "half", "closed"}
    verify_makeup_layers(
        bundle / "assets/official-packs/mohan.makeup.builtin.mohan-outfit", regions,
    )
