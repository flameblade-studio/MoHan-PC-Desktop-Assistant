from __future__ import annotations

lazy import re
lazy from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LANGUAGE_HEADINGS = (
    "繁體中文",
    "简体中文",
    "English",
    "日本語",
)
DOCUMENTS = (
    "docs/release-evidence/V4-RELEASE-READINESS.md",
    "docs/release-evidence/V4-PYTHON315-QT-COMPATIBILITY.md",
    "docs/release-evidence/V4-PYTHON315-QT-BLOCKER.md",
    "docs/release-evidence/V4-POSE-ATLAS-BLOCKER.md",
    "docs/releases/v4.0.0-draft.md",
    "docs/releases/v4.0.0.md",
    "README.md",
    "THIRD_PARTY_NOTICES.md",
)
LANGUAGE_HEADING_PATTERN = re.compile(
    r"(?m)^## (繁體中文|简体中文|English|日本語)\s*$"
)
MOJIBAKE_MARKERS = (
    "\ufffd",
    "ï»¿",
    "â€™",
    "â€œ",
    "â€",
    "???",
    "锟斤拷",
)


def read_utf8(relative: str) -> str:
    raw = (ROOT / relative).read_bytes()
    assert not raw.startswith(b"\xef\xbb\xbf"), relative
    text = raw.decode("utf-8", errors="strict")
    assert "\x00" not in text, relative
    assert not any(marker in text for marker in MOJIBAKE_MARKERS), relative
    return text


def language_sections(text: str, source: str) -> tuple[str, ...]:
    headings = tuple(LANGUAGE_HEADING_PATTERN.finditer(text))
    assert tuple(match.group(1) for match in headings) == LANGUAGE_HEADINGS, source
    return tuple(
        text[
            match.end() : (
                headings[index + 1].start() if index + 1 < len(headings) else len(text)
            )
        ]
        for index, match in enumerate(headings)
    )


def structure(section: str) -> tuple[int, int, int, int, int]:
    return (
        len(re.findall(r"(?m)^#{3,6}\s+", section)),
        len(re.findall(r"(?m)^-\s+", section)),
        len(re.findall(r"(?m)^\d+[.)]\s+", section)),
        len(re.findall(r"(?m)^\|.*\|\s*$", section)),
        len(re.findall(r"(?m)^>\s?", section)),
    )


def test_target_release_documents_are_strict_utf8_and_structurally_complete() -> None:
    for relative in DOCUMENTS:
        sections = language_sections(read_utf8(relative), relative)
        assert all(section.strip() for section in sections), relative
        structures = tuple(structure(section) for section in sections)
        assert len(set(structures)) == 1, (relative, structures)


def test_release_status_is_unambiguously_ready_in_all_languages() -> None:
    readiness = language_sections(
        read_utf8("docs/release-evidence/V4-RELEASE-READINESS.md"),
        "V4-RELEASE-READINESS.md",
    )
    status = language_sections(
        read_utf8("docs/releases/v4.0.0.md"),
        "v4.0.0.md",
    )
    draft = language_sections(
        read_utf8("docs/releases/v4.0.0-draft.md"),
        "v4.0.0-draft.md",
    )
    blockers = (
        ("RELEASE-READY／可發布", "RELEASE-READY／可发布", "RELEASE-READY", "RELEASE-READY／公開準備完了"),
        ("正式 Release 說明", "正式 Release 说明", "formal v4.0.0 Release Notes", "正式 Release 説明"),
        ("開發草稿", "开发草稿", "development draft", "開発草案"),
    )
    for sections, markers in zip(
        (readiness, status, draft),
        blockers,
        strict=True,
    ):
        assert all(
            marker in section for section, marker in zip(sections, markers, strict=True)
        )


def test_rust_contract_is_complete_and_equal_in_all_four_languages() -> None:
    for relative in (
        "README.md",
        "THIRD_PARTY_NOTICES.md",
        "docs/releases/v4.0.0-draft.md",
        "docs/releases/v4.0.0.md",
    ):
        sections = language_sections(read_utf8(relative), relative)
        for section in sections:
            for required in (
                "Rust",
                "1.97.1",
                "Maturin",
                "1.14.1",
                "PyO3",
                "0.29.2",
                "Rayon",
                "1.12.0",
                "262,144",
                "PyBackedBytes",
                "SIMD",
            ):
                assert required in section, (relative, required)


def test_rust_status_never_implies_that_formal_packaging_is_complete() -> None:
    readiness = language_sections(
        read_utf8("docs/release-evidence/V4-RELEASE-READINESS.md"),
        "V4-RELEASE-READINESS.md",
    )
    readme = language_sections(read_utf8("README.md"), "README.md")
    notices = language_sections(
        read_utf8("THIRD_PARTY_NOTICES.md"),
        "THIRD_PARTY_NOTICES.md",
    )
    readiness_markers = (
        "Qt 相容層：READY",
        "Qt 兼容层：READY",
        "Qt compatibility layer: READY",
        "Qt 互換レイヤー：READY",
    )
    readme_markers = (
        "以 Rust 1.97.1、Maturin 1.14.1 與 PyO3 0.29.2",
        "使用 Rust 1.97.1、Maturin 1.14.1 与 PyO3 0.29.2",
        "with Rust 1.97.1, Maturin 1.14.1, and PyO3 0.29.2",
        "Rust 1.97.1、Maturin 1.14.1、PyO3 0.29.2",
    )
    notice_markers = (
        "Windows 正式封裝規格要求",
        "Windows 正式打包规范要求",
        "The formal Windows packaging contract",
        "Windows 正式パッケージ化の契約",
    )
    for sections, markers in (
        (readiness, readiness_markers),
        (readme, readme_markers),
        (notices, notice_markers),
    ):
        assert all(
            marker in section for section, marker in zip(sections, markers, strict=True)
        )


def main() -> None:
    test_target_release_documents_are_strict_utf8_and_structurally_complete()
    test_release_status_is_unambiguously_ready_in_all_languages()
    test_rust_contract_is_complete_and_equal_in_all_four_languages()
    test_rust_status_never_implies_that_formal_packaging_is_complete()
    print("V4_RELEASE_DOCUMENT_INTEGRITY_OK")


if __name__ == "__main__":
    main()
