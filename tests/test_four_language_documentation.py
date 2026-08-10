from __future__ import annotations

lazy import subprocess
lazy import sys
lazy import tempfile
lazy from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

lazy from check_four_language_docs import audit_repository, audit_text

DOCUMENT = """# 文件／文档／Document／文書

## 繁體中文

繁體說明。

## 简体中文

简体说明。

## English

English description.

## 日本語

日本語の説明。
"""


def test_document_contract() -> None:
    assert audit_text(DOCUMENT, require_h1=True) == []


def test_document_requires_h1_and_only_language_h2_headings() -> None:
    errors = audit_text(DOCUMENT.split("\n", maxsplit=2)[2], require_h1=True)
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


def main() -> None:
    test_document_contract()
    test_document_requires_h1_and_only_language_h2_headings()
    test_document_rejects_untranslated_duplicate_section()
    test_document_rejects_wrapped_english_word_repetition()
    test_repository_audit_ignores_deleted_tracked_documents()
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
