from __future__ import annotations

lazy import ast
lazy import re
lazy import tomllib
lazy from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEVELOPMENT_VERSION = "4.5.0"
VERSION_AUTHORITY = "domain/version_info.py"
LANGUAGE_HEADINGS = (
    "## 繁體中文",
    "## 简体中文",
    "## English",
    "## 日本語",
)


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def fallback_version() -> str:
    tree = ast.parse(read(VERSION_AUTHORITY))
    assignments = (
        node
        for node in tree.body
        if isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Name)
            and target.id == "FALLBACK_VERSION"
            for target in node.targets
        )
    )
    assignment = next(assignments)
    assert isinstance(assignment.value, ast.Constant)
    assert isinstance(assignment.value.value, str)
    return assignment.value.value


def project_version(relative: str) -> str:
    project = tomllib.loads(read(relative))["project"]
    version = project["version"]
    assert isinstance(version, str)
    return version


def project_metadata(relative: str) -> dict[str, object]:
    project = tomllib.loads(read(relative))["project"]
    assert isinstance(project, dict)
    return project


def language_sections(document: str) -> tuple[str, ...]:
    positions = tuple(document.index(heading) for heading in LANGUAGE_HEADINGS)
    assert positions == tuple(sorted(positions))
    ends = (*positions[1:], len(document))
    return tuple(
        document[start:end]
        for start, end in zip(positions, ends, strict=True)
    )


def test_current_development_version_authorities_are_synchronized() -> None:
    assert fallback_version() == DEVELOPMENT_VERSION
    assert project_version("pyproject.toml") == DEVELOPMENT_VERSION
    assert (
        project_version("sbom/preview.pyproject.toml")
        == DEVELOPMENT_VERSION
    )


def test_root_version_module_is_only_a_runtime_compatibility_facade() -> None:
    facade = read("version_info.py")
    assert "FALLBACK_VERSION" not in facade
    assert 'import_module("domain.version_info")' in facade


def test_development_tools_do_not_leak_into_runtime_metadata() -> None:
    windows = project_metadata("pyproject.toml")
    preview = project_metadata("sbom/preview.pyproject.toml")

    classifiers = windows.get("classifiers")
    assert isinstance(classifiers, list)
    assert "Development Status :: 3 - Alpha" in classifiers
    assert "Development Status :: 5 - Production/Stable" not in classifiers

    for source, metadata in (
        ("pyproject.toml", windows),
        ("sbom/preview.pyproject.toml", preview),
    ):
        dependencies = metadata.get("dependencies")
        assert isinstance(dependencies, list), source
        normalized = tuple(str(item).casefold() for item in dependencies)
        assert not any(item.startswith("pytest") for item in normalized), source
        assert not any(item.startswith("ruff") for item in normalized), source


def test_readme_distinguishes_development_from_published_versions() -> None:
    readme = read("README.md")
    sections = language_sections(readme)
    development_labels = (
        "**目前開發版本：**",
        "**当前开发版本：**",
        "**Current development version:**",
        "**現在の開発版：**",
    )
    unreleased_statements = (
        "尚未發布的開發草稿",
        "尚未发布的开发草稿",
        "unreleased development draft",
        "未公開の開発草案",
    )
    build_command = f'.\\build.ps1 -Version "{DEVELOPMENT_VERSION}"'

    for section, label, unreleased in zip(
        sections,
        development_labels,
        unreleased_statements,
        strict=True,
    ):
        assert section.count(label) == 1
        assert DEVELOPMENT_VERSION in section
        assert unreleased in section
        assert section.count(build_command) == 1


def test_v4_release_document_keeps_four_language_structure() -> None:
    # Audit ruling (2026-08-27): v4.0.0 has shipped, so this test no longer
    # forces the historical draft to claim it is unreleased.  The draft file
    # is kept as a historical artifact; only its existence and its ordered
    # four-language structure remain under test.  The former assertions on
    # "development draft" / "GitHub Releases remains authoritative" wording
    # were fossils contradicting reality and were removed.
    draft = read("docs/releases/v4.0.0-draft.md")
    assert draft.startswith(
        "# 墨寒桌面助理 v4.0.0 發布草稿／"
        "墨寒桌面助手 v4.0.0 发布草稿／"
        "MoHan Desktop Assistant v4.0.0 Release Draft／"
        "墨寒デスクトップアシスタント v4.0.0 公開草案\n"
    )
    sections = language_sections(draft)
    for section in sections:
        assert re.search(r"(?<![\d.])4\.0\.0(?![\d.])", section)


def main() -> None:
    test_current_development_version_authorities_are_synchronized()
    test_root_version_module_is_only_a_runtime_compatibility_facade()
    test_development_tools_do_not_leak_into_runtime_metadata()
    test_readme_distinguishes_development_from_published_versions()
    test_v4_release_document_keeps_four_language_structure()
    print("V4_DEVELOPMENT_VERSION_CONSISTENCY_OK")


if __name__ == "__main__":
    main()
