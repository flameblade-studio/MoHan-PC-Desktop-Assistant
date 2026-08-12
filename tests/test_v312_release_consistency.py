from __future__ import annotations

lazy import re
lazy import sys
lazy import tomllib
lazy from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

lazy from version_info import APP_VERSION, FALLBACK_VERSION

VERSION = "3.1.2"
TAG = f"v{VERSION}"
PYTHON_VERSION = "3.15.0-rc.1"
LANGUAGE_HEADINGS = (
    "## 繁體中文",
    "## 简体中文",
    "## English",
    "## 日本語",
)


def read(relative: str) -> str:
    path = ROOT / relative
    assert path.is_file(), f"missing v3.1.2 release input: {relative}"
    return path.read_text(encoding="utf-8")


def project_metadata(relative: str) -> dict[str, object]:
    document = tomllib.loads(
        (ROOT / relative).read_text(encoding="utf-8")
    )
    return document["project"]


def language_sections(document: str, source: str) -> tuple[str, ...]:
    matches = tuple(
        tuple(re.finditer(rf"(?m)^{re.escape(heading)}\s*$", document))
        for heading in LANGUAGE_HEADINGS
    )
    assert all(len(heading_matches) == 1 for heading_matches in matches), (
        f"{source} must contain exactly one of each four-language section"
    )
    positions = tuple(heading_matches[0].start() for heading_matches in matches)
    assert positions == tuple(sorted(positions)), (
        f"{source} language order must be Traditional Chinese, Simplified "
        "Chinese, English, then Japanese"
    )
    ends = (*positions[1:], len(document))
    return tuple(
        document[start:end]
        for start, end in zip(positions, ends, strict=True)
    )


def assert_no_premature_publication(
    document: str,
    source: str,
) -> None:
    publication_terms = (
        "已發布",
        "已发布",
        "has been published",
        "is published",
        "公開完了",
        "公開済み",
    )
    preparation_terms = (
        "尚未",
        "不代表",
        "並不代表",
        "并不代表",
        "not published",
        "does not mean",
        "未公開",
        "示しません",
    )
    for line in document.splitlines():
        if VERSION not in line:
            continue
        if not any(term in line for term in publication_terms):
            continue
        assert any(term in line for term in preparation_terms), (
            f"{source} prematurely describes {TAG} as published: {line}"
        )


def test_runtime_and_package_versions() -> None:
    assert APP_VERSION == VERSION
    assert FALLBACK_VERSION == VERSION

    for metadata_path in ("pyproject.toml", "sbom/preview.pyproject.toml"):
        metadata = project_metadata(metadata_path)
        assert metadata["version"] == VERSION, metadata_path
        assert metadata["requires-python"] == ">=3.15,<3.16", metadata_path

    citation = read("CITATION.cff")
    assert f'version: "{VERSION}"' in citation


def test_readme_uses_one_dynamic_release_badge_per_language() -> None:
    readme = read("README.md")
    sections = language_sections(readme, "README.md")
    prepared_descriptions = (
        "實際產物仍須通過本版最終發布門檻",
        "实际产物仍须通过本版本最终发布关卡",
        "actual artifacts must still pass this release's final publication gates",
        "実際の成果物は本版の最終公開ゲートに合格する必要があります",
    )

    for section, prepared_description in zip(
        sections,
        prepared_descriptions,
        strict=True,
    ):
        badge_block = section.split("</p>", maxsplit=1)[0]
        assert badge_block.count("img.shields.io/github/v/release/") == 1
        assert "label=published" in badge_block
        assert VERSION not in badge_block, (
            "the published-Release badge must stay dynamic rather than repeat "
            "the prepared source version"
        )

        creator_start = section.index("<strong>")
        creator_end = section.index("</p>", creator_start)
        creator_block = section[creator_start:creator_end]
        assert VERSION not in creator_block, (
            "the creator summary must link to Releases without repeating a "
            "version that may later be Stable or RC"
        )

        assert prepared_description in section

    assert_no_premature_publication(readme, "README.md")


def test_four_language_release_sources_are_prepared_not_published() -> None:
    changelog = read("CHANGELOG.md")
    notes = read(f"docs/releases/{TAG}.md")

    language_sections(changelog, "CHANGELOG.md")
    language_sections(notes, f"docs/releases/{TAG}.md")
    assert changelog.count(f"### {TAG} — 2026-08-12") == 4
    assert notes.startswith(
        "# 墨寒桌面助理 v3.1.2／墨寒桌面助手 v3.1.2／"
        "MoHan Desktop Assistant v3.1.2／"
        "墨寒デスクトップアシスタント v3.1.2\n"
    )

    for marker in (
        "v3.1.2 尚未發布",
        "v3.1.2 尚未发布",
        "v3.1.2 is not published",
        "v3.1.2 は未公開",
    ):
        assert marker in changelog, marker
    for marker in (
        "不代表 CI 已全綠或 v3.1.2 已發布",
        "并不代表 CI 已全部通过或 v3.1.2 已发布",
        "does not mean CI is all green or v3.1.2 has been published",
        "CI の全成功や v3.1.2 の公開完了を示しません",
    ):
        assert marker in notes, marker

    assert_no_premature_publication(changelog, "CHANGELOG.md")
    assert_no_premature_publication(notes, f"docs/releases/{TAG}.md")


def test_release_workflow_derives_and_validates_the_exact_tag() -> None:
    workflow = read(".github/workflows/release.yml")
    assert re.fullmatch(r"v[0-9]+\.[0-9]+\.[0-9]+", TAG)
    for required in (
        'if [[ "$tag" =~ ^v[0-9]+\\.[0-9]+\\.[0-9]+-rc\\.[1-9][0-9]*$ ]]',
        'elif [[ "$tag" =~ ^v[0-9]+\\.[0-9]+\\.[0-9]+$ ]]',
        'echo "version=${tag#v}" >> "$GITHUB_OUTPUT"',
        "Expected exactly one literal FALLBACK_VERSION",
        'if [[ "$source_version" != "$RELEASE_VERSION" ]]',
        'notes="docs/releases/$RELEASE_TAG.md"',
        '--notes-file "docs/releases/$tag.md"',
    ):
        assert required in workflow, required
    assert (ROOT / "docs" / "releases" / f"{TAG}.md").is_file()


def test_python315_node24_and_jit_release_contract() -> None:
    release = read(".github/workflows/release.yml")
    windows = read(".github/workflows/windows-ci.yml")

    workflow_dir = ROOT / ".github" / "workflows"
    for workflow_path in sorted(workflow_dir.glob("*.yml")):
        workflow = workflow_path.read_text(encoding="utf-8")
        assert 'FORCE_JAVASCRIPT_ACTIONS_TO_NODE24: "true"' in workflow, (
            f"{workflow_path.name} must force the Node 24 action runtime"
        )
        assert "ACTIONS_ALLOW_USE_UNSECURE_NODE_VERSION" not in workflow

    windows_python_versions = set(
        re.findall(r'python-version:\s*"([^"]+)"', windows)
    )
    assert windows_python_versions == {PYTHON_VERSION}
    release_python_versions = re.findall(
        r'python-version:\s*"([^"]+)"',
        release,
    )
    assert PYTHON_VERSION in release_python_versions
    assert set(release_python_versions) == {PYTHON_VERSION, "3.14.7"}
    assert release_python_versions.count("3.14.7") == 1, (
        "Python 3.14 must remain isolated to third-party SBOM tooling"
    )

    for required in (
        'PYTHON_JIT = "0"',
        'PYTHON_JIT = "1"',
        "sys._jit.is_available()",
        "sys._jit.is_enabled()",
        "tools/benchmark_python315_hotpaths.py",
    ):
        assert required in windows, required
    for required in (
        "Build and verify JIT-default Python 3.15 runtime",
        "PACKAGED_JIT_DEFAULT_OK",
        "$env:PYTHON_JIT = $null",
        "$env:MOHAN_DISABLE_JIT = $null",
    ):
        assert required in release, required
    assert "--enable-experimental-jit=yes" in read(
        "tools/build_python315_jit_runtime.py"
    )

    readme = read("README.md")
    for statement in (
        "JIT 預設啟用",
        "JIT 默认启用",
        "JIT is on by default",
        "JIT は既定で有効",
    ):
        assert statement in readme, statement


def main() -> None:
    test_runtime_and_package_versions()
    test_readme_uses_one_dynamic_release_badge_per_language()
    test_four_language_release_sources_are_prepared_not_published()
    test_release_workflow_derives_and_validates_the_exact_tag()
    test_python315_node24_and_jit_release_contract()
    print("V312_RELEASE_CONSISTENCY_OK")


if __name__ == "__main__":
    main()
