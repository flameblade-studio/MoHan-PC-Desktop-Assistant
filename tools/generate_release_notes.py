"""Generate a four-language release-notes draft from ``CHANGELOG.md``.

Release Please writes one CHANGELOG section per release, and this repository
enforces four-language commit subjects (繁體中文／简体中文／English／日本語
separated by ``／``), so the changelog bullets already carry every language.
This tool turns the section for one version into a
``docs/releases/v<version>.md`` draft that follows the established
four-section layout (``## 繁體中文``, ``## 简体中文``, ``## English``,
``## 日本語``) and satisfies ``tools/check_four_language_docs.py``.

An existing notes file is never overwritten: human polish always wins, and the
tool exits successfully so the release workflow can call it unconditionally.

A bullet is only distributed across the four language sections when it splits
into exactly four non-empty parts whose inline-code tokens, link targets, and
raw URLs match; otherwise the full bullet is kept verbatim in every section so
the structural four-language audit still passes and a human can finish the
translation split.

The script follows the repository's PEP 810 lazy-import policy and therefore
requires the pinned Python 3.15 runtime; the release workflow provisions it
with ``actions/setup-python`` before invoking this tool.

Run from the repository root::

    python tools/generate_release_notes.py --version 4.5.0
"""

from __future__ import annotations

lazy import argparse
lazy import re
lazy import sys
lazy from collections import Counter
lazy from collections.abc import Sequence
lazy from pathlib import Path

LANGUAGE_COUNT = 4
LANGUAGE_HEADINGS = ("繁體中文", "简体中文", "English", "日本語")
LANGUAGE_SEPARATOR = "／"
HEADING_SEPARATOR = " / "

TITLE_TEMPLATES = (
    "墨寒桌面助理 v{version} 發行說明",
    "墨寒桌面助手 v{version} 发布说明",
    "MoHan Desktop Assistant v{version} Release Notes",
    "墨寒デスクトップアシスタント v{version} リリースノート",
)
PLATFORM_NOTES = (
    "> Windows 為正式支援平台；macOS 與 Linux 維持功能受限 Preview。",
    "> Windows 是正式支持平台；macOS 与 Linux 继续作为功能受限 Preview。",
    (
        "> Windows is the formally supported platform; "
        "macOS and Linux remain limited Previews."
    ),
    (
        "> Windows は正式サポートプラットフォームです。"
        "macOS と Linux は機能限定 Preview を継続します。"
    ),
)
DOWNLOAD_GUIDANCE = (
    (
        "> **一般使用者下載檔名結尾為 `Windows-x64-Setup.exe` 的安裝檔即可。**"
        "其餘資產為可攜 ZIP／MSI、macOS 與 Linux Preview，以及 SBOM、雜湊與"
        "效能證據等供應鏈驗證檔案，日常使用不需要下載。"
    ),
    (
        "> **一般用户下载文件名结尾为 `Windows-x64-Setup.exe` 的安装包即可。**"
        "其余资产为便携 ZIP／MSI、macOS 与 Linux Preview，以及 SBOM、哈希与"
        "性能证据等供应链验证文件，日常使用不需要下载。"
    ),
    (
        "> **Most people want the installer whose name ends in "
        "`Windows-x64-Setup.exe`.** The remaining assets are the portable ZIP "
        "and MSI, the macOS and Linux Previews, and supply-chain evidence such "
        "as SBOMs, checksums and performance records, none of which everyday "
        "use requires."
    ),
    (
        "> **通常のご利用では、ファイル名が `Windows-x64-Setup.exe` で終わる"
        "インストーラのみで十分です。** 残りの資産はポータブル ZIP と MSI、"
        "macOS と Linux の Preview、そして SBOM・ハッシュ・性能証跡といった"
        "サプライチェーン検証用のファイルであり、日常利用では不要です。"
    ),
)
DRAFT_NOTES = (
    "本檔案由 CHANGELOG 自動產生，作為四語發行說明初稿；正式發布前請人工潤飾。",
    "本文件由 CHANGELOG 自动生成，作为四语发布说明初稿；正式发布前请人工润饰。",
    (
        "This file was generated automatically from the CHANGELOG as a "
        "four-language release-notes draft; polish it manually before the "
        "release is published."
    ),
    (
        "本ファイルは CHANGELOG から自動生成された四言語リリースノートの"
        "草稿です。正式公開前に人手で推敲してください。"
    ),
)
EMPTY_NOTES = (
    "本版沒有可自動擷取的變更條目；詳細內容請參閱 CHANGELOG。",
    "本版本没有可自动提取的变更条目；详细内容请参阅 CHANGELOG。",
    (
        "No changelog entries could be extracted automatically for this "
        "version; see the CHANGELOG for details."
    ),
    "本バージョンでは自動抽出できる変更項目がありません。詳細は CHANGELOG を参照してください。",
)
GENERIC_SECTION = ("其他變更", "其他变更", "Other changes", "その他の変更")
# Release Please's default English changelog section names, mapped to the
# four-language headings this repository's config uses.
SECTION_TRANSLATIONS = {
    "Features": ("新功能", "新功能", "New features", "新機能"),
    "Bug Fixes": ("修正", "修复", "Fixes", "修正"),
    "Performance Improvements": ("效能", "性能", "Performance", "パフォーマンス"),
    "Code Refactoring": ("重構", "重构", "Refactor", "リファクタリング"),
    "Documentation": ("文件", "文档", "Documentation", "ドキュメント"),
    "Dependencies": ("相依套件", "依赖项", "Dependencies", "依存関係"),
    "Miscellaneous Chores": GENERIC_SECTION,
    "Reverts": ("還原變更", "还原变更", "Reverts", "変更の取り消し"),
    "Build System": ("建置系統", "构建系统", "Build system", "ビルドシステム"),
    "Continuous Integration": (
        "持續整合",
        "持续集成",
        "Continuous integration",
        "継続的インテグレーション",
    ),
    "Styles": ("程式風格", "代码风格", "Styles", "コードスタイル"),
    "Tests": ("測試", "测试", "Tests", "テスト"),
}

_INLINE_CODE_PATTERN = re.compile(r"`[^`\n]+`")
_LINK_TARGET_PATTERN = re.compile(r"!?\[[^\]]*\]\(([^)\s]+)")
_RAW_URL_PATTERN = re.compile(r"https?://[^\s)>]+")
_TRAILING_REFERENCE_PATTERN = re.compile(r"\s*\(\[[^\]]*\]\([^()\s]*\)\)$")


def _structural_tokens(text: str) -> tuple[Counter[str], ...]:
    return (
        Counter(_INLINE_CODE_PATTERN.findall(text)),
        Counter(_LINK_TARGET_PATTERN.findall(text)),
        Counter(_RAW_URL_PATTERN.findall(text)),
    )


def _split_trailing_references(bullet: str) -> tuple[str, str]:
    """Split ``text ([#88](url)) ([sha](url))`` into text and reference tail."""
    references: list[str] = []
    remaining = bullet.rstrip()
    while True:
        match = _TRAILING_REFERENCE_PATTERN.search(remaining)
        if match is None:
            break
        references.append(match.group(0).strip())
        remaining = remaining[: match.start()].rstrip()
    references.reverse()
    suffix = " " + " ".join(references) if references else ""
    return remaining, suffix


def localize_text(text: str) -> tuple[str, ...]:
    parts = tuple(part.strip() for part in text.split(LANGUAGE_SEPARATOR))
    if len(parts) == LANGUAGE_COUNT and all(parts):
        tokens = tuple(_structural_tokens(part) for part in parts)
        if all(part_tokens == tokens[0] for part_tokens in tokens[1:]):
            return parts
    return (text,) * LANGUAGE_COUNT


def localize_heading(title: str) -> tuple[str, ...]:
    parts = tuple(part.strip() for part in title.split(HEADING_SEPARATOR))
    if len(parts) == LANGUAGE_COUNT and all(parts):
        return parts
    return SECTION_TRANSLATIONS.get(title, (title,) * LANGUAGE_COUNT)


def changelog_section(changelog: str, version: str) -> str:
    heading = re.compile(rf"(?m)^## \[?v?{re.escape(version)}[\]) ].*$")
    match = heading.search(changelog)
    if match is None:
        return ""
    start = match.end()
    following = re.compile(r"(?m)^## ").search(changelog, start)
    end = following.start() if following else len(changelog)
    return changelog[start:end]


def parse_entries(section: str) -> list[tuple[str, list[str]]]:
    """Collect ``(type heading, bullets)`` groups in changelog order."""
    groups: list[tuple[str, list[str]]] = []
    for line in section.splitlines():
        if line.startswith("### "):
            groups.append((line[len("### ") :].strip(), []))
        elif line.startswith("* "):
            if not groups:
                groups.append(("", []))
            groups[-1][1].append(line[len("* ") :].strip())
        elif line.strip() and groups and groups[-1][1]:
            groups[-1][1][-1] += " " + line.strip()
    return [(title, bullets) for title, bullets in groups if bullets]


def compose(version: str, section: str) -> str:
    localized_groups: list[tuple[tuple[str, ...], list[tuple[str, ...]]]] = []
    for title, bullets in parse_entries(section):
        title_parts = localize_heading(title) if title else GENERIC_SECTION
        bullet_rows: list[tuple[str, ...]] = []
        for bullet in bullets:
            core, references = _split_trailing_references(bullet)
            parts = localize_text(core)
            bullet_rows.append(
                tuple(f"- {part}{references}" for part in parts)
            )
        localized_groups.append((title_parts, bullet_rows))

    title = LANGUAGE_SEPARATOR.join(
        template.format(version=version) for template in TITLE_TEMPLATES
    )
    lines: list[str] = [f"# {title}", ""]
    for index, language in enumerate(LANGUAGE_HEADINGS):
        lines.extend(
            (
                f"## {language}",
                "",
                PLATFORM_NOTES[index],
                "",
                DOWNLOAD_GUIDANCE[index],
                "",
                DRAFT_NOTES[index],
                "",
            )
        )
        if not localized_groups:
            lines.extend((EMPTY_NOTES[index], ""))
        for title_parts, bullet_rows in localized_groups:
            lines.extend((f"### {title_parts[index]}", ""))
            lines.extend(row[index] for row in bullet_rows)
            lines.append("")
    return "\n".join(lines).rstrip("\n") + "\n"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Generate a four-language docs/releases draft from CHANGELOG.md; "
            "an existing notes file is never overwritten."
        )
    )
    parser.add_argument("--version", required=True, help="Release version, e.g. 4.5.0")
    parser.add_argument("--changelog", default=None, help="Changelog path override")
    parser.add_argument("--output", default=None, help="Output notes path override")
    arguments = parser.parse_args(argv)

    root = Path(__file__).resolve().parents[1]
    changelog_path = (
        Path(arguments.changelog) if arguments.changelog else root / "CHANGELOG.md"
    )
    output_path = (
        Path(arguments.output)
        if arguments.output
        else root / "docs" / "releases" / f"v{arguments.version}.md"
    )
    if output_path.exists():
        print(f"RELEASE_NOTES_PRESERVED path={output_path}")
        return 0
    section = changelog_section(
        changelog_path.read_text(encoding="utf-8"), arguments.version
    )
    document = compose(arguments.version, section)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(document, encoding="utf-8", newline="\n")
    print(f"RELEASE_NOTES_GENERATED path={output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
