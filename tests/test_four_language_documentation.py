from __future__ import annotations

lazy import re
lazy import subprocess
lazy import sys
lazy import tempfile
lazy from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

lazy from check_four_language_docs import audit_fragment, audit_repository, audit_text

DOCUMENT = """# 文件／文档／Document／文書
## 繁體中文

繁體說明。
## 简体中文
简体说明。
## English

English description.

## 日本語
日本語の説明。"""


def test_document_contract() -> None:
    assert audit_text(DOCUMENT, require_h1=True) == []


def test_document_requires_h1_and_only_language_h2_headings() -> None:
    errors = audit_text(DOCUMENT.split("\n", maxsplit=1)[1], require_h1=True)
    assert "a four-language H1 is required" in errors

    extra_h2 = DOCUMENT.replace("繁體說明。", "繁體說明。\n\n## 額外章節")
    errors = audit_text(extra_h2, require_h1=True)
    assert any("only H2 headings" in error for error in errors)


def test_document_rejects_untranslated_duplicate_section() -> None:
    duplicate = DOCUMENT.replace("简体说明。", "繁體說明。")
    errors = audit_text(duplicate, require_h1=True)
    assert any("duplicates 繁體中文" in error for error in errors)


def test_document_rejects_wrapped_english_word_repetition() -> None:
    duplicate = DOCUMENT.replace(
        "English description.",
        "English remains limited\nlimited Preview.",
    )
    errors = audit_text(duplicate, require_h1=True)
    assert "English section repeats adjacent word 'limited'" in errors


def test_repository_audit_ignores_deleted_tracked_documents() -> None:
    with tempfile.TemporaryDirectory(prefix="mohan-four-language-docs-") as raw:
        root = Path(raw)
        canonical = root / "README.md"
        obsolete = root / "README.ja.md"
        canonical.write_text(DOCUMENT, encoding="utf-8")
        obsolete.write_text(DOCUMENT, encoding="utf-8")
        subprocess.run(
            ["git", "init", "--quiet"],
            cwd=root,
            check=True,
        )
        subprocess.run(
            ["git", "add", "--", canonical.name, obsolete.name],
            cwd=root,
            check=True,
        )
        obsolete.unlink()

        assert audit_repository(root) == {}


def test_repository_audit_ignores_untracked_workspace_documents() -> None:
    with tempfile.TemporaryDirectory(prefix="mohan-four-language-docs-") as raw:
        root = Path(raw)
        canonical = root / "README.md"
        workspace_note = root / "handoff" / "owner-note.md"
        canonical.write_text(DOCUMENT, encoding="utf-8")
        workspace_note.parent.mkdir()
        workspace_note.write_text("# 暫存筆記\n", encoding="utf-8")
        subprocess.run(
            ["git", "init", "--quiet"],
            cwd=root,
            check=True,
        )
        subprocess.run(
            ["git", "add", "--", canonical.name],
            cwd=root,
            check=True,
        )

        assert audit_repository(root) == {}


def test_repository_audit_exempts_task_scoped_quality_report() -> None:
    with tempfile.TemporaryDirectory(prefix="mohan-quality-report-") as raw:
        root = Path(raw)
        report = root / "QUALITY-GATES-REPORT.md"
        report.write_text("# 單語暫存工程報告\n", encoding="utf-8")
        subprocess.run(["git", "init", "--quiet"], cwd=root, check=True)

        assert audit_repository(root) == {}


LANGUAGE_HEADINGS = (
    "繁體中文",
    "简体中文",
    "English",
    "日本語",
)


def _language_sections(text: str) -> dict[str, str]:
    headings = list(
        re.finditer(
            r"(?m)^## (繁體中文|简体中文|English|日本語)\s*$",
            text,
        )
    )
    assert [match.group(1) for match in headings] == list(LANGUAGE_HEADINGS)
    return {
        match.group(1): text[
            match.end() : (
                headings[index + 1].start()
                if index + 1 < len(headings)
                else len(text)
            )
        ]
        for index, match in enumerate(headings)
    }


def test_current_release_four_language_bullet_parity() -> None:
    release_text = (ROOT / "docs/releases/v3.1.0.md").read_text(
        encoding="utf-8"
    )
    release_sections = _language_sections(release_text)
    release_bullet_counts = {
        language: len(re.findall(r"(?m)^- ", section))
        for language, section in release_sections.items()
    }
    assert len(set(release_bullet_counts.values())) == 1
    assert next(iter(release_bullet_counts.values())) > 0

    changelog_text = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    changelog_sections = _language_sections(changelog_text)
    changelog_bullet_counts: dict[str, int] = {}
    for language, section in changelog_sections.items():
        match = re.search(
            r"(?ms)^### v3\.1\.0.*?\n(.*?)(?=^### |\Z)",
            section,
        )
        assert match is not None, language
        changelog_bullet_counts[language] = len(
            re.findall(r"(?m)^- ", match.group(1))
        )
    assert len(set(changelog_bullet_counts.values())) == 1
    assert next(iter(changelog_bullet_counts.values())) > 0

    for text in (release_text, changelog_text):
        assert "。、" not in text
        assert "。," not in text
        assert ".," not in text


FRAGMENT = """### 文件修復／文档修复／Document repair／文書の修復

- 還原文字／还原文字／Restore text／文字を復元。
"""


def test_fragment_rejects_mojibake_title() -> None:
    errors = audit_fragment(FRAGMENT.replace("文件修復", "README ???? V5 ???"))
    assert any(error.startswith("1:") and "encoding loss" in error for error in errors)
    assert any(error.startswith("1:") and "繁體中文" in error for error in errors)
    assert all("／" in error and ("翻訳" in error or "復元" in error) for error in errors)


def test_fragment_rejects_mojibake_bullet() -> None:
    errors = audit_fragment(FRAGMENT.replace("文字を復元。", "????"))
    assert any(error.startswith("3:") and "encoding loss" in error for error in errors)
    assert any(error.startswith("3:") and "日本語" in error for error in errors)


def test_fragment_requires_native_characters_in_each_translation() -> None:
    for native in ("文件修復", "文档修复", "文書の修復", "還原文字", "还原文字", "文字を復元。"):
        errors = audit_fragment(FRAGMENT.replace(native, "README ? V5 ?"))
        assert any("lacks Chinese or Japanese characters" in error for error in errors)


def test_fullwidth_question_marks_and_normal_four_language_text_pass() -> None:
    assert audit_fragment(FRAGMENT) == []
    assert audit_fragment(FRAGMENT.replace("文字", "文字？？？")) == []
    assert audit_text(DOCUMENT.replace("說明", "說明？？？"), require_h1=True) == []


def test_section_technical_slashes_are_not_translation_separators() -> None:
    texts = ("授權（MIT／Apache 2.0／CC0／CC BY）。",
             "授权（MIT／Apache 2.0／CC0／CC BY）。",
             "Licenses (MIT / Apache 2.0 / CC0 / CC BY).",
             "ライセンス（MIT／Apache 2.0／CC0／CC BY）。")
    document = DOCUMENT
    for original, replacement in zip(
        ("繁體說明。", "简体说明。", "English description.", "日本語の説明。"),
        texts,
        strict=True,
    ):
        document = document.replace(original, "- " + replacement)
    assert audit_text(document, require_h1=True) == []


def test_document_rejects_mojibake_in_original_lines() -> None:
    for original in ("文件", "繁體說明。", "English description."):
        corrupted = DOCUMENT.replace(original, "???")
        number = next(
            index for index, line in enumerate(corrupted.splitlines(), start=1) if "???" in line
        )
        errors = audit_text(corrupted, require_h1=True)
        assert any(error.startswith(f"{number}:") and "encoding loss" in error for error in errors)
    errors = audit_text(DOCUMENT.replace("文件", "README ?"), require_h1=True)
    assert any(error.startswith("1:") and "lacks Chinese" in error for error in errors)


def test_repository_audit_checks_untracked_fragments_with_line_numbers() -> None:
    with tempfile.TemporaryDirectory(prefix="mohan-mojibake-") as raw:
        root = Path(raw)
        subprocess.run(["git", "init", "--quiet"], cwd=root, check=True)
        fragment = root / "changelog.d" / "encoding.md"
        fragment.parent.mkdir()
        fragment.write_text(FRAGMENT.replace("还原文字", "??"), encoding="utf-8", newline="\n")
        failures = audit_repository(root)
        assert tuple(failures) == (Path("changelog.d/encoding.md"),)
        assert any(error.startswith("3:") and "简体中文" in error for error in failures[next(iter(failures))])


def main() -> None:
    test_fragment_rejects_mojibake_title()
    test_fragment_rejects_mojibake_bullet()
    test_fragment_requires_native_characters_in_each_translation()
    test_fullwidth_question_marks_and_normal_four_language_text_pass()
    test_section_technical_slashes_are_not_translation_separators()
    test_document_rejects_mojibake_in_original_lines()
    test_repository_audit_checks_untracked_fragments_with_line_numbers()
    test_document_contract()
    test_document_requires_h1_and_only_language_h2_headings()
    test_document_rejects_untranslated_duplicate_section()
    test_document_rejects_wrapped_english_word_repetition()
    test_repository_audit_ignores_deleted_tracked_documents()
    test_repository_audit_ignores_untracked_workspace_documents()
    test_repository_audit_exempts_task_scoped_quality_report()
    test_current_release_four_language_bullet_parity()
    result = subprocess.run(
        [sys.executable, "tools/check_four_language_docs.py"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert result.returncode == 0, result.stderr
    assert "FOUR_LANGUAGE_DOCUMENTATION_OK" in result.stdout
    print("FOUR_LANGUAGE_DOCUMENTATION_OK")


if __name__ == "__main__":
    main()


LEGACY_FRAGMENT = """### 未發布 — 文件修復

* 修復說明文字。

### 未发布 — 文件修复

* 修复说明文字。

### Unreleased — Documentation repair

* Repair the description text.

### 未リリース — 文書修復

* 説明文を修復。
"""


def test_legacy_fragment_passes_and_rejects_short_or_ascii_damage() -> None:
    assert audit_fragment(LEGACY_FRAGMENT) == []
    for native, damaged in (("説明文を修復。", "??"), ("修复说明文字。", "fix text")):
        errors = audit_fragment(LEGACY_FRAGMENT.replace(native, damaged))
        assert any("中日文字" in error for error in errors), errors
