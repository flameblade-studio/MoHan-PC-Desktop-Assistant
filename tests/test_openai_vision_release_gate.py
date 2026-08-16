from __future__ import annotations

lazy import sys
lazy from pathlib import Path
lazy from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

lazy from tools.check_openai_vision_release import evaluate

PROVIDER = '''\
lazy from urllib.request import Request, urlopen
ENDPOINT = "https://api.openai.com/v1/responses"
store=False
'''
BUILD = 'Write-Host "stdlib transport"\n'
LANGUAGE_HEADINGS = (
    "## 繁體中文",
    "## 简体中文",
    "## English",
    "## 日本語",
)
POLICY_MARKERS = (
    "`openai` Python SDK 執行期相依",
    "`openai` Python SDK 运行时依赖",
    "`openai` Python SDK runtime dependency",
    "`openai` Python SDK の実行時依存",
)
POLICY_DOCUMENTS = (
    "README.md",
    "ARCHITECTURE.md",
    "THIRD_PARTY_NOTICES.md",
    "docs/releases/v4.0.0-draft.md",
    "docs/releases/v4.0.0.md",
)
FORBIDDEN_SDK_REQUIREMENTS = (
    "加入正式環境使用的 OpenAI Python SDK",
    "添加生产环境使用的 OpenAI Python SDK",
    "Pin the official OpenAI Python SDK",
    "公式 OpenAI Python SDK を実行時依存として固定",
)


def _workspace(root: Path, *, include_openai: bool = False) -> None:
    (root / "sbom").mkdir()
    openai_requirement = "openai==1.2.3\n" if include_openai else ""
    requirements = f"opencv-python==5.0.0.93\n{openai_requirement}"
    (root / "requirements.txt").write_text(requirements, encoding="utf-8")
    (root / "requirements-runtime.txt").write_text(requirements, encoding="utf-8")
    dependencies = [
        '  "opencv-python==5.0.0.93",',
        *(['  "openai==1.2.3",'] if include_openai else []),
    ]
    (root / "pyproject.toml").write_text(
        "[project]\nname = \"fixture\"\nversion = \"4.0.0\"\n"
        "dependencies = [\n" + "\n".join(dependencies) + "\n]\n",
        encoding="utf-8",
    )
    components = '''\
schema = 1
[[component]]
name = "opencv-python"
version = "5.0.0.93"
license = "Apache-2.0"
scope = "runtime"
profiles = ["windows"]
'''
    if include_openai:
        components += '''\
[[component]]
name = "openai"
version = "1.2.3"
license = "LicenseRef-Test-Only"
scope = "runtime"
profiles = ["windows"]
'''
    (root / "sbom" / "components.toml").write_text(components, encoding="utf-8")
    (root / "requirements-preview.txt").write_text("PySide6==6.11.1\n", encoding="utf-8")
    (root / "requirements-preview-runtime.txt").write_text(
        "PySide6==6.11.1\n", encoding="utf-8"
    )
    (root / "sbom" / "preview.pyproject.toml").write_text(
        '[project]\nname = "preview"\nversion = "4.0.0"\ndependencies = []\n',
        encoding="utf-8",
    )
    provider = root / "integrations" / "openai_vision_provider.py"
    provider.parent.mkdir()
    provider.write_text(PROVIDER, encoding="utf-8")
    (root / "build.ps1").write_text(BUILD, encoding="utf-8")


def test_v3_bypasses_future_vision_inventory() -> None:
    with TemporaryDirectory() as raw:
        result = evaluate(Path(raw), "3.1.2")
    assert result.passed and not result.required and not result.issues


def test_v4_requires_real_transport_evidence() -> None:
    with TemporaryDirectory() as raw:
        root = Path(raw)
        _workspace(root)
        (root / "integrations" / "openai_vision_provider.py").write_text(
            "store=False\n", encoding="utf-8"
        )
        result = evaluate(root, "4.0.0")
    assert not result.passed and result.required
    assert "openai:stdlib-responses-contract-missing" in result.issues


def test_v4_accepts_stdlib_transport_and_consistent_inventory() -> None:
    with TemporaryDirectory() as raw:
        root = Path(raw)
        _workspace(root)
        result = evaluate(root, "v4.0.0-rc.1")
    assert result.passed and result.required and not result.issues


def test_v4_rejects_sdk_dependency_and_preview_leak() -> None:
    with TemporaryDirectory() as raw:
        root = Path(raw)
        _workspace(root)
        (root / "requirements-runtime.txt").write_text(
            "opencv-python==5.0.0.93\nopenai==3.0.0\n", encoding="utf-8"
        )
        (root / "requirements-preview.txt").write_text(
            "PySide6==6.11.1\nopenai==1.2.3\n", encoding="utf-8"
        )
        result = evaluate(root, "4.0.0")
    assert "openai:third-party-sdk-must-not-be-required" in result.issues
    assert "openai:preview-must-remain-limited" in result.issues


def test_current_tree_has_reproducible_v4_transport() -> None:
    result = evaluate(ROOT, "4.0.0")
    assert result.passed
    assert not result.issues


def test_windows_packaging_does_not_collect_an_unused_sdk() -> None:
    build = (ROOT / "build.ps1").read_text(encoding="utf-8")
    assert "collect-all\", \"openai" not in build
    assert "OpenAICollectArgs" not in build


def test_four_language_docs_record_the_no_sdk_runtime_policy() -> None:
    for relative_path in POLICY_DOCUMENTS:
        content = (ROOT / relative_path).read_text(encoding="utf-8")
        heading_positions = [content.index(heading) for heading in LANGUAGE_HEADINGS]
        assert heading_positions == sorted(heading_positions), relative_path
        for marker in POLICY_MARKERS:
            assert marker in content, f"{relative_path}: missing {marker}"
        for forbidden in FORBIDDEN_SDK_REQUIREMENTS:
            assert forbidden not in content, f"{relative_path}: stale {forbidden}"


def run() -> None:
    test_v3_bypasses_future_vision_inventory()
    test_v4_requires_real_transport_evidence()
    test_v4_accepts_stdlib_transport_and_consistent_inventory()
    test_v4_rejects_sdk_dependency_and_preview_leak()
    test_current_tree_has_reproducible_v4_transport()
    test_windows_packaging_does_not_collect_an_unused_sdk()
    test_four_language_docs_record_the_no_sdk_runtime_policy()
    print("OPENAI_VISION_RELEASE_GATE_OK")


if __name__ == "__main__":
    run()
