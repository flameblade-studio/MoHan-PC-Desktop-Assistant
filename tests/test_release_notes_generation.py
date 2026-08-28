from __future__ import annotations

lazy import re
lazy import sys
lazy import tempfile
lazy from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

lazy from tools.check_four_language_docs import audit_text
lazy from tools.generate_release_notes import (
    LANGUAGE_COUNT,
    changelog_section,
    compose,
    main as generate_notes,
)

VERSION = "9.9.9"
FOUR_LANGUAGE_BULLET_PARTS = (
    "修復發版自動化",
    "修复发版自动化",
    "Fix the release automation",
    "リリース自動化を修正",
)
REFERENCE_SUFFIX = (
    "([#1](https://github.com/example/repo/issues/1)) "
    "([abc1234](https://github.com/example/repo/commit/abc1234))"
)
ASYMMETRIC_BULLET = "修正半身／全身疊影／修复叠影／Fix double images／二重表示を修正"
SAMPLE_CHANGELOG = f"""# 變更紀錄

## [{VERSION}](https://github.com/example/repo/compare/v9.9.8...v{VERSION}) (2026-08-27)


### Features

* {"／".join(FOUR_LANGUAGE_BULLET_PARTS)} {REFERENCE_SUFFIX}


### 🐛 修正 / 修复 / Fixes / 修正

* {ASYMMETRIC_BULLET}

## [9.9.8](https://github.com/example/repo/compare/v9.9.7...v9.9.8) (2026-08-20)


### Bug Fixes

* 舊版條目不應被擷取／旧版条目不应被提取／Old entries must not leak／旧項目は抽出されない
"""
LANGUAGE_HEADINGS = (
    "## 繁體中文",
    "## 简体中文",
    "## English",
    "## 日本語",
)


def build_sample_document() -> str:
    return compose(VERSION, changelog_section(SAMPLE_CHANGELOG, VERSION))


def test_draft_passes_the_four_language_audit() -> None:
    document = build_sample_document()
    assert audit_text(document, require_h1=True) == []
    positions = [document.index(heading) for heading in LANGUAGE_HEADINGS]
    assert positions == sorted(positions)
    assert "功能受限" in document
    assert "機能限定" in document
    assert re.search(r"limited(?:\s+cross-platform)?\s+Preview", document)


def test_four_language_bullets_split_per_language_section() -> None:
    document = build_sample_document()
    for part in FOUR_LANGUAGE_BULLET_PARTS:
        assert document.count(part) == 1
    assert document.count(REFERENCE_SUFFIX) == LANGUAGE_COUNT
    assert document.count("### 🐛 修正") == 1
    assert document.count("### Fixes") == 1


def test_asymmetric_bullets_stay_verbatim_in_every_section() -> None:
    document = build_sample_document()
    assert document.count(ASYMMETRIC_BULLET) == LANGUAGE_COUNT
    assert "舊版條目不應被擷取" not in document


def test_repository_changelog_produces_an_auditable_draft() -> None:
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    section = changelog_section(changelog, "4.4.2")
    assert section.strip()
    document = compose("4.4.2", section)
    assert audit_text(document, require_h1=True) == []


def test_existing_notes_are_never_overwritten() -> None:
    with tempfile.TemporaryDirectory() as temp:
        changelog_path = Path(temp) / "CHANGELOG.md"
        changelog_path.write_text(SAMPLE_CHANGELOG, encoding="utf-8")
        output_path = Path(temp) / f"v{VERSION}.md"
        sentinel = "人工潤飾後的正式說明"
        output_path.write_text(sentinel, encoding="utf-8")
        assert generate_notes(
            (
                "--version",
                VERSION,
                "--changelog",
                str(changelog_path),
                "--output",
                str(output_path),
            )
        ) == 0
        assert output_path.read_text(encoding="utf-8") == sentinel

        output_path.unlink()
        assert generate_notes(
            (
                "--version",
                VERSION,
                "--changelog",
                str(changelog_path),
                "--output",
                str(output_path),
            )
        ) == 0
        generated = output_path.read_text(encoding="utf-8")
        assert generated.startswith(f"# 墨寒桌面助理 v{VERSION} 發行說明／")
        assert audit_text(generated, require_h1=True) == []


def main() -> None:
    test_draft_passes_the_four_language_audit()
    test_four_language_bullets_split_per_language_section()
    test_asymmetric_bullets_stay_verbatim_in_every_section()
    test_repository_changelog_produces_an_auditable_draft()
    test_existing_notes_are_never_overwritten()
    print("RELEASE_NOTES_GENERATION_OK")


if __name__ == "__main__":
    main()
