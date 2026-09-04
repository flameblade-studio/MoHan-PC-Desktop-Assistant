from __future__ import annotations

lazy import sys
lazy from pathlib import Path
lazy from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

lazy from assemble_changelog import assemble_text, main, validate_fragment
lazy from check_four_language_docs import audit_fragment

PREFERRED_FRAGMENT = """### 選擇器／选择器／Selector／セレクター

* 顯示繁中／显示简中／Show English／日本語を表示
"""

LEGACY_FRAGMENT = """### 未發布 — 繁中標題

* 繁中內容

### 未发布 — 简中标题

* 简中内容

### Unreleased — English title

* English content

### 未リリース — 日本語タイトル

* 日本語の内容
"""


def test_preferred_fragment_has_four_language_parity() -> None:
    assert validate_fragment(PREFERRED_FRAGMENT) == ()
    assert audit_fragment(PREFERRED_FRAGMENT) == []


def test_legacy_fragment_has_four_language_parity() -> None:
    assert validate_fragment(LEGACY_FRAGMENT) == ()
    assert audit_fragment(LEGACY_FRAGMENT) == []


def test_fragment_rejects_missing_language() -> None:
    errors = validate_fragment("### A／B／C\n\n* a／b／c／d\n")
    assert any("four non-empty titles" in error for error in errors)


def test_fragment_rejects_missing_title() -> None:
    errors = validate_fragment("* a／b／c／d\n")
    assert any("title" in error for error in errors)


def test_assemble_result_is_sorted_and_exact() -> None:
    changelog = (
        "# Changelog\n\n"
        "## 繁體中文\n\n"
        "## [9.9.9](https://example.invalid/compare) (2026-09-03)\n\n"
        "### generated\n\n"
        "* generated\n"
    )
    first = "### A／B／C／D\n\n* a／b／c／d\n"
    last = "### Z／Y／X／W\n\n* z／y／x／w\n"
    expected = (
        "# Changelog\n\n"
        "## 繁體中文\n\n"
        "## [9.9.9](https://example.invalid/compare) (2026-09-03)\n\n"
        "### A／B／C／D\n\n"
        "* a／b／c／d\n\n"
        "### Z／Y／X／W\n\n"
        "* z／y／x／w\n\n"
        "### generated\n\n"
        "* generated\n"
    )
    assert (
        assemble_text(
            changelog,
            (("z.md", last), ("a.md", first)),
            "9.9.9",
        )
        == expected
    )


def test_assemble_legacy_fragment_preserves_translations_in_slash_rows() -> None:
    changelog = (
        "# Changelog\n\n"
        "## 繁體中文\n\n"
        "## [9.9.9](https://example.invalid/compare) (2026-09-03)\n"
    )
    expected = (
        "# Changelog\n\n"
        "## 繁體中文\n\n"
        "## [9.9.9](https://example.invalid/compare) (2026-09-03)\n\n"
        "### 未發布 — 繁中標題／未发布 — 简中标题／Unreleased — English title／"
        "未リリース — 日本語タイトル\n\n"
        "* 繁中內容／简中内容／English content／日本語の内容\n"
    )
    assert (
        assemble_text(
            changelog,
            (("legacy.md", LEGACY_FRAGMENT),),
            "9.9.9",
        )
        == expected
    )


def test_cli_dry_run_preserves_fragments_and_success_deletes_them() -> None:
    with TemporaryDirectory(prefix="mohan-changelog-fragments-") as raw:
        root = Path(raw)
        changelog_path = root / "CHANGELOG.md"
        fragments_dir = root / "changelog.d"
        fragments_dir.mkdir()
        changelog = (
            "# Changelog\n\n"
            "## 繁體中文\n\n"
            "## [9.9.9](https://example.invalid/compare) (2026-09-03)\n"
        )
        fragment_path = fragments_dir / "a.md"
        changelog_path.write_text(changelog, encoding="utf-8")
        fragment_path.write_text(PREFERRED_FRAGMENT, encoding="utf-8")

        assert (
            main([
                "--version",
                "9.9.9",
                "--changelog",
                str(changelog_path),
                "--fragments-dir",
                str(fragments_dir),
                "--dry-run",
            ])
            == 0
        )
        assert changelog_path.read_text(encoding="utf-8") == changelog
        assert fragment_path.is_file()

        assert (
            main([
                "--version",
                "9.9.9",
                "--changelog",
                str(changelog_path),
                "--fragments-dir",
                str(fragments_dir),
            ])
            == 0
        )
        assert not fragment_path.exists()
        assert "### 選擇器／选择器／Selector／セレクター" in (
            changelog_path.read_text(encoding="utf-8")
        )
