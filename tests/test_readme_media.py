from __future__ import annotations

lazy import re
lazy import struct
lazy from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MEDIA = ROOT / "docs" / "media"
VERSION_MATCH = re.search(
    r'^FALLBACK_VERSION = "([^"]+)"$',
    (ROOT / "version_info.py").read_text(encoding="utf-8"),
    re.MULTILINE,
)
assert VERSION_MATCH, "version_info.py must define one literal FALLBACK_VERSION"
SOURCE_VERSION = VERSION_MATCH.group(1)
SHIELD_VERSION = SOURCE_VERSION.replace("-", "--")
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
        f"Development Version v{SOURCE_VERSION}",
        (
            "https://img.shields.io/badge/development_version-"
            f"v{SHIELD_VERSION}-5c6ac4.svg"
        ),
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
        assert width >= 600 and height >= 400, (
            f"README image is too small: {filename} ({width}x{height})"
        )
        if expected_size:
            assert (width, height) == expected_size, (
                f"unexpected {filename} size: {width}x{height}"
            )
        assert f"docs/media/{filename}" in readme, (
            f"README does not reference {filename}"
        )


def _localized_readmes() -> dict[str, str]:
    return {
        name: (ROOT / name).read_text(encoding="utf-8")
        for name in ("README.md", "README.zh-CN.md", "README.ja.md")
    }


def _assert_certification_badges(localized_readmes: dict[str, str]) -> None:
    assert len(set(localized_readmes.values())) == 1, (
        "all three README entry points must remain byte-for-byte identical"
    )
    badge_blocks: dict[str, str] = {}
    for name, content in localized_readmes.items():
        badge_match = re.search(
            r'<p align="center">\s*(.*?)\s*</p>', content, re.DOTALL
        )
        assert badge_match, f"{name} is missing its certification badge block"
        badge_blocks[name] = badge_match.group(1)
        actual_badges = tuple(
            re.findall(r'<img alt="([^"]+)" src="([^"]+)">', badge_match.group(1))
        )
        assert actual_badges == README_BADGES, (
            f"{name} certification badges are incomplete, out of order, or stale"
        )
        for filename in PNG_FILES:
            if filename.startswith("support-"):
                continue
            assert f"docs/media/{filename}" in content, (
                f"{name} does not reference shared current media: {filename}"
            )
    assert len(set(badge_blocks.values())) == 1, (
        "all three localized README files must share the exact same badge block"
    )


def _assert_quality_standard(localized_readmes: dict[str, str]) -> None:
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
    for name, content in localized_readmes.items():
        assert "(PUBLISHING.md)" in content, (
            f"{name} does not link to the shared Flameblade quality standard"
        )
    for workflow in BADGE_WORKFLOWS:
        assert (ROOT / ".github" / "workflows" / workflow).is_file(), (
            f"README badge points to missing workflow: {workflow}"
        )


def _assert_timeless_creator_narrative(
    localized_readmes: dict[str, str],
) -> None:
    for name, content in localized_readmes.items():
        for pattern in TIME_SENSITIVE_CREATOR_AGE_PATTERNS:
            assert not pattern.search(content), (
                f"{name} hard-codes the creator's changing age: {pattern.pattern}"
            )


def _assert_demo_video(readme: str) -> None:
    video = MEDIA / "mohan-demo.mp4"
    assert video.is_file(), "missing 30–60 second demonstration video"
    size = video.stat().st_size
    assert 100_000 <= size <= 20 * 1024 * 1024, (
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
        "Ko-fi 一次性贊助",
        "Ko-fi 一次性赞助",
        "One-time support on Ko-fi",
        "Ko-fi で一回限りの支援",
        "https://ko-fi.com/flamebladestudio",
    )
    for requirement in support_requirements:
        assert requirement in readme, f"missing project support content: {requirement}"
    assert readme.count("https://ko-fi.com/flamebladestudio") == 4
    for retired_support in (
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
    assert readme.count('width="33%" align="center" valign="top"') == 3, (
        "support columns must be top-aligned so shorter captions cannot push "
        "the complete image-and-text column downward on GitHub"
    )
    assert readme.count('width="25%" align="center" valign="top"') == 4, (
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
    localized_readmes = _localized_readmes()
    _assert_readme_images(readme)
    _assert_certification_badges(localized_readmes)
    _assert_quality_standard(localized_readmes)
    _assert_timeless_creator_narrative(localized_readmes)
    _assert_demo_video(readme)
    _assert_support_section(readme)
    _assert_github_links(readme)
    _assert_security_and_community_files()
    print("README_MEDIA_AND_COMMUNITY_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
