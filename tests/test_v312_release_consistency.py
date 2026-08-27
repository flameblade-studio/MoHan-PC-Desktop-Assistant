from __future__ import annotations

lazy import re
lazy from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

VERSION = "3.1.2"
TAG = f"v{VERSION}"
RELEASE_DATE = "2026-08-13"
PYTHON_VERSION = "3.15.0-rc.1"
LANGUAGE_HEADINGS = (
    "## 繁體中文",
    "## 简体中文",
    "## English",
    "## 日本語",
)

LANGUAGE_COUNT = 4


def read(relative: str) -> str:
    path = ROOT / relative
    assert path.is_file(), f"missing v3.1.2 release input: {relative}"
    return path.read_text(encoding="utf-8")


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


def test_citation_metadata_tracks_the_current_release() -> None:
    citation = read("CITATION.cff")
    fallback = re.search(
        r'(?m)^FALLBACK_VERSION = "([^"]+)"$',
        read("domain/version_info.py"),
    )
    assert fallback is not None
    assert f'version: "{fallback.group(1)}"' in citation
    assert re.search(r'(?m)^date-released: "\d{4}-\d{2}-\d{2}"$', citation)


def test_readme_uses_one_dynamic_release_badge_per_language() -> None:
    readme = read("README.md")
    sections = language_sections(readme, "README.md")
    release_gate_descriptions = (
        "實際產物仍須通過本版最終發布門檻",
        "实际产物仍须通过本版本最终发布关卡",
        "actual artifacts must still pass this release's final publication gates",
        "実際の成果物は本版の最終公開ゲートに合格する必要があります",
    )

    for section, release_gate_description in zip(
        sections,
        release_gate_descriptions,
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

        assert release_gate_description in section


def assert_no_stale_release_status(document: str, source: str) -> None:
    stale_status_patterns = (
        r"v3\.1\.2[^\n]*(?:尚未發布|預定)",
        r"v3\.1\.2[^\n]*(?:尚未发布|计划)",
        r"v3\.1\.2[^\n]*(?:not published|is planned)",
        r"v3\.1\.2[^\n]*(?:未公開|予定)",
    )
    for pattern in stale_status_patterns:
        assert re.search(pattern, document, flags=re.IGNORECASE) is None, (
            f"{source} contains stale v3.1.2 publication wording: {pattern}"
        )


def test_four_language_release_sources_are_complete_and_permanent() -> None:
    readme = read("README.md")
    changelog = read("CHANGELOG.md")
    notes = read(f"docs/releases/{TAG}.md")

    language_sections(readme, "README.md")
    language_sections(changelog, "CHANGELOG.md")
    note_sections = language_sections(notes, f"docs/releases/{TAG}.md")
    assert changelog.count(f"### {TAG} — {RELEASE_DATE}") == LANGUAGE_COUNT
    assert notes.startswith(
        "# 墨寒桌面助理 v3.1.2／墨寒桌面助手 v3.1.2／"
        "MoHan Desktop Assistant v3.1.2／"
        "墨寒デスクトップアシスタント v3.1.2\n"
    )

    permanent_descriptions = (
        "本版完整提供繁體中文、簡體中文、英文與日文介面",
        "本版本完整提供繁体中文、简体中文、英文与日文界面",
        (
            "This release provides complete Traditional Chinese, Simplified "
            + "Chinese, English, and Japanese interfaces"
        ),
        "本版は繁体字中国語、簡体字中国語、英語、日本語の完全な画面を提供します",
    )
    for section, description in zip(
        note_sections,
        permanent_descriptions,
        strict=True,
    ):
        assert description in section, description

    for source, document in (
        ("README.md", readme),
        ("CHANGELOG.md", changelog),
        (f"docs/releases/{TAG}.md", notes),
    ):
        assert_no_stale_release_status(document, source)


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
    assert windows_python_versions == {PYTHON_VERSION, "3.14.7"}
    assert windows.count('python-version: "3.14.7"') == 1, (
        "Python 3.14 must remain isolated to third-party SBOM tooling"
    )
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
        "Windows 安裝封裝版使用工作室維護的 Python",
        "Windows 安装包使用工作室维护的 Python",
        "The Windows installer uses the studio-maintained Python",
        "Windows インストーラーは、スタジオ管理の Python",
    ):
        assert statement in readme, statement


def main() -> None:
    test_citation_metadata_tracks_the_current_release()
    test_readme_uses_one_dynamic_release_badge_per_language()
    test_four_language_release_sources_are_complete_and_permanent()
    test_release_workflow_derives_and_validates_the_exact_tag()
    test_python315_node24_and_jit_release_contract()
    print("V312_RELEASE_CONSISTENCY_OK")


if __name__ == "__main__":
    main()
