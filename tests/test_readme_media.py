from __future__ import annotations

lazy import re
lazy import struct
lazy from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MEDIA = ROOT / "docs" / "media"
MIN_IMAGE_WIDTH = 600
MIN_IMAGE_HEIGHT = 400
LANGUAGE_NAV_COUNT = 4
MIN_VIDEO_SIZE_BYTES = 100_000
SUPPORT_COLUMN_COUNT = 3
STRATEGIST_CARD_COUNT = 4
PNG_FILES = {
    "mohan-hero.png": (1600, 900),
    "first-run-wizard.png": None,
    "voice-modes.png": None,
    "expressions.png": None,
    "tasks-and-ideas.png": None,
    "long-term-memory.png": None,
    "security-permissions.png": None,
    "support-proud.png": (640, 640),
    "support-shy-aligned.png": (640, 640),
    "support-mock-hit.png": (640, 640),
}
README_BADGES = (
    (
        "Windows CI",
        ("https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/"
        "actions/workflows/windows-ci.yml/badge.svg"),
    ),
    (
        "Cross-platform core CI",
        ("https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/"
        "actions/workflows/cross-platform-core.yml/badge.svg"),
    ),
    (
        "CodeQL",
        ("https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/"
        "actions/workflows/codeql.yml/badge.svg"),
    ),
    (
        "Python Security Audit",
        ("https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/"
        "actions/workflows/security-audit.yml/badge.svg"),
    ),
    (
        "Extended Secret Defense / Gitleaks",
        ("https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/"
        "actions/workflows/secret-defense.yml/badge.svg"),
    ),
    (
        "Latest Published Release",
        ("https://img.shields.io/github/v/release/"
        "hitoshic1982/MoHan-PC-Desktop-Assistant?"
        "include_prereleases&label=published"),
    ),
    ("MIT License", "https://img.shields.io/badge/license-MIT-blue.svg"),
    (
        "Python 3.15",
        ("https://img.shields.io/badge/Python-3.15-3776AB.svg?"
        "logo=python&logoColor=white"),
    ),
    (
        "4 interface languages",
        "https://img.shields.io/badge/interface_languages-4-79648d.svg",
    ),
)
BADGE_WORKFLOWS = (
    "windows-ci.yml",
    "cross-platform-core.yml",
    "codeql.yml",
    "security-audit.yml",
    "secret-defense.yml",
)
TIME_SENSITIVE_CREATOR_AGE_PATTERNS = (
    re.compile(r"我是一位\s*(?:\d{1,3}|[零〇一二三四五六七八九十百兩两]+)\s*[歲岁]"),
    re.compile(
        r"\bI was an?\s+(?:\d{1,3}|[a-z]+(?:-[a-z]+)*)"
        r"(?:-year-old|\s+years?\s+old)\b",
        re.IGNORECASE,
    ),
    re.compile(r"私は\s*(?:\d{1,3}|[零〇一二三四五六七八九十百]+)\s*歳"),
    re.compile(r"[三四五六七八九]十(?:多)?[歲岁]的自己"),
    re.compile(r"\bmy\s+(?:\d+|[a-z]+)-something\s+self\b", re.IGNORECASE),
    re.compile(r"[三四五六七八九]十代の自分"),
)


def png_size(path: Path) -> tuple[int, int]:
    data = path.read_bytes()[:24]
    assert data[:8] == b"\x89PNG\r\n\x1a\n", f"invalid PNG: {path.name}"
    return struct.unpack(">II", data[16:24])


def _assert_readme_images(readme: str) -> None:
    for filename, expected_size in PNG_FILES.items():
        path = MEDIA / filename
        assert path.is_file(), f"missing README image: {filename}"
        width, height = png_size(path)
        assert width >= MIN_IMAGE_WIDTH and height >= MIN_IMAGE_HEIGHT, (
            f"README image is too small: {filename} ({width}x{height})"
        )
        if expected_size:
            assert (width, height) == expected_size, (
                f"unexpected {filename} size: {width}x{height}"
            )
        assert f"docs/media/{filename}" in readme, (
            f"README does not reference {filename}"
        )


def _assert_single_readme_entry_point(readme: str) -> None:
    language_navigation = (
        "[繁體中文](#繁體中文) · [簡體中文](#简体中文) · "
        "[English](#english) · [日本語](#日本語)"
    )
    assert readme.count(language_navigation) == LANGUAGE_NAV_COUNT
    for obsolete_readme in ("README.zh-CN.md", "README.ja.md"):
        assert not (ROOT / obsolete_readme).exists(), (
            f"duplicate README entry point returned: {obsolete_readme}"
        )
        assert obsolete_readme not in readme, (
            f"README links obsolete compatibility entry point: {obsolete_readme}"
        )


def _assert_certification_badges(readme: str) -> None:
    badge_match = re.search(
        r'<p align="center">\s*(.*?)\s*</p>', readme, re.DOTALL
    )
    assert badge_match, "README.md is missing its certification badge block"
    actual_badges = tuple(
        re.findall(r'<img alt="([^"]+)" src="([^"]+)">', badge_match.group(1))
    )
    assert actual_badges == README_BADGES, (
        "README.md certification badges are incomplete, out of order, or stale"
    )
    for filename in PNG_FILES:
        if filename.startswith("support-"):
            continue
        assert f"docs/media/{filename}" in readme, (
            f"README.md does not reference shared current media: {filename}"
        )


def _assert_quality_standard(readme: str) -> None:
    quality_standard = (ROOT / "PUBLISHING.md").read_text(encoding="utf-8")
    for heading in (
        "炎劍開源軟體家族品質標準",
        "炎剑开源软件家族质量标准",
        "Flameblade Open Source Software Family Quality Standard",
        "炎剣オープンソース・ソフトウェア・ファミリー品質基準",
    ):
        assert heading in quality_standard, (
            f"missing shared quality-standard heading: {heading}"
        )
    for declaration in (
        "劍，我已鍛成；餘下的路，就交給你們了。",
        "剑，我已锻成；余下的路，就交给你们了。",
        "I have forged this sword. What comes next is up to you.",
        "この剣は、私が鍛え上げました。あとは皆さんに託します。",
    ):
        assert declaration in quality_standard, (
            f"missing open-source declaration: {declaration}"
        )
    assert "(PUBLISHING.md)" in readme, (
        "README.md does not link to the shared Flameblade quality standard"
    )
    for workflow in BADGE_WORKFLOWS:
        assert (ROOT / ".github" / "workflows" / workflow).is_file(), (
            f"README badge points to missing workflow: {workflow}"
        )


def _assert_timeless_creator_narrative(readme: str) -> None:
    for pattern in TIME_SENSITIVE_CREATOR_AGE_PATTERNS:
        assert not pattern.search(readme), (
            "README.md hard-codes the creator's changing age: "
            f"{pattern.pattern}"
        )


def _assert_demo_video(readme: str) -> None:
    video = MEDIA / "mohan-demo.mp4"
    assert video.is_file(), "missing 30–60 second demonstration video"
    size = video.stat().st_size
    assert MIN_VIDEO_SIZE_BYTES <= size <= 20 * 1024 * 1024, (
        f"unexpected demonstration video size: {size} bytes"
    )
    header = video.read_bytes()[:32]
    assert b"ftyp" in header, "demonstration video is not an MP4 container"
    assert "docs/media/mohan-demo.mp4" in readme


def _assert_support_section(readme: str) -> None:
    support_requirements = (
        "## 支持墨寒 / Support MoHan",
        "docs/media/support-proud.png",
        "docs/media/support-shy-aligned.png",
        "docs/media/support-mock-hit.png",
        "請使用儲存庫上方由 GitHub 顯示的 Sponsor 按鈕；目前正式收款選項為 Ko-fi，可選擇單次或每月贊助。",
        "请使用仓库上方由 GitHub 显示的 Sponsor 按钮；目前正式收款选项为 Ko-fi，可选择单次或每月赞助。",
        "Use the Sponsor button displayed by GitHub above this repository; Ko-fi is the current official funding option and supports one-time or monthly contributions.",
        "このリポジトリ上部に GitHub が表示する Sponsor ボタンをご利用ください。現在の正式な支援先は Ko-fi で、単発または毎月の支援を選べます。",
    )
    for requirement in support_requirements:
        assert requirement in readme, f"missing project support content: {requirement}"
    for retired_support in (
        "ko-fi.com/",
        "buymeacoffee.com",
        "paypal.com/paypalme",
    ):
        assert retired_support not in readme.lower(), (
            f"retired support link remains in README: {retired_support}"
        )
    for filename in (
        "support-proud.png",
        "support-shy-aligned.png",
        "support-mock-hit.png",
    ):
        assert f'src="docs/media/{filename}" width="220" height="220"' in readme, (
            f"support portrait lacks fixed aligned dimensions: {filename}"
        )
    assert readme.count('width="33%" align="center" valign="top"') == SUPPORT_COLUMN_COUNT, (
        "support columns must be top-aligned so shorter captions cannot push "
        "the complete image-and-text column downward on GitHub"
    )
    assert readme.count('width="25%" align="center" valign="top"') == STRATEGIST_CARD_COUNT, (
        "all four strategist-theatre cards must be top-aligned so shorter "
        "captions cannot push the first images and text downward on GitHub"
    )


def _assert_github_links(readme: str) -> None:
    github_requirements = (
        "actions/workflows/windows-ci.yml/badge.svg",
        "actions/workflows/codeql.yml/badge.svg",
        "ROADMAP.md",
        "/discussions",
    )
    for requirement in github_requirements:
        assert requirement in readme, f"missing GitHub project link: {requirement}"


def _assert_security_and_community_files() -> None:
    security = (ROOT / "SECURITY.md").read_text(encoding="utf-8").lower()
    assert "private vulnerability reporting" in security
    assert "api key" in security and "oauth" in security
    assert "請勿" in security and "公開" in security

    required_community_files = (
        ROOT / "CODE_OF_CONDUCT.md",
        ROOT / ".github" / "ISSUE_TEMPLATE" / "bug_report.yml",
        ROOT / ".github" / "ISSUE_TEMPLATE" / "feature_request.yml",
        ROOT / ".github" / "ISSUE_TEMPLATE" / "config.yml",
    )
    for path in required_community_files:
        assert path.is_file(), f"missing community file: {path.relative_to(ROOT)}"


def main() -> int:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    _assert_single_readme_entry_point(readme)
    _assert_readme_images(readme)
    _assert_certification_badges(readme)
    _assert_quality_standard(readme)
    _assert_timeless_creator_narrative(readme)
    _assert_demo_video(readme)
    _assert_support_section(readme)
    _assert_github_links(readme)
    _assert_security_and_community_files()
    print("README_MEDIA_AND_COMMUNITY_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
