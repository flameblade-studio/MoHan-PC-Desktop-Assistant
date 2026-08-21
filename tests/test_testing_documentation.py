from __future__ import annotations

lazy from pathlib import Path

DOCUMENT = Path(__file__).resolve().parents[1] / "docs" / "TESTING.md"
LANGUAGE_HEADINGS = (
    "## 繁體中文",
    "## 简体中文",
    "## English",
    "## 日本語",
)
REQUIRED_SECTION_HEADINGS = (
    ("### 完整回歸暫時狀態", "### 目前發布阻擋", "### 尚未封裝或發布"),
    ("### 完整回归暂时状态", "### 当前发布阻挡", "### 尚未打包或发布"),
    (
        "### Temporary complete-regression status",
        "### Current release blockers",
        "### Not yet packaged or released",
    ),
    ("### 完全回帰の暫定状況", "### 現在の公開阻害事項", "### 未パッケージ・未公開"),
)
MOJIBAKE_MARKERS = ("\ufffd", "銝", "嚗", "ã€", "縺", "譁")
SECTION_HEADING_COUNT = 6


def document_bytes() -> bytes:
    return DOCUMENT.read_bytes()


def document_text() -> str:
    return document_bytes().decode("utf-8", errors="strict")


def language_sections(text: str) -> tuple[str, ...]:
    offsets = tuple(text.index(heading) for heading in LANGUAGE_HEADINGS)
    return tuple(
        text[start:end]
        for start, end in zip(offsets, (*offsets[1:], len(text)), strict=True)
    )


def test_testing_document_is_bom_free_valid_utf8_without_mojibake() -> None:
    raw = document_bytes()
    assert not raw.startswith(b"\xef\xbb\xbf")
    text = raw.decode("utf-8", errors="strict")
    assert all(marker not in text for marker in MOJIBAKE_MARKERS)


def test_four_language_order_and_equivalent_section_structure() -> None:
    text = document_text()
    offsets = tuple(text.index(heading) for heading in LANGUAGE_HEADINGS)
    assert offsets == tuple(sorted(offsets))
    sections = language_sections(text)
    for section, required in zip(sections, REQUIRED_SECTION_HEADINGS, strict=True):
        positions = tuple(section.index(heading) for heading in required)
        assert positions == tuple(sorted(positions))
        assert section.count("### ") == SECTION_HEADING_COUNT


def test_each_language_records_current_release_truth() -> None:
    for section in language_sections(document_text()):
        assert "app.py" in section
        assert "13" in section
        assert "Python 3.15" in section
        assert "PySide6 6.11.1" in section
        assert "PoseAtlas" in section
        assert "66" in section
        assert "v4" in section
