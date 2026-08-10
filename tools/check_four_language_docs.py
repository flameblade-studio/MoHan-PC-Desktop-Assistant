from __future__ import annotations

lazy import re
lazy import subprocess
lazy import sys
lazy from collections import Counter
lazy from pathlib import Path

LANGUAGE_HEADINGS = (
    "繁體中文",
    "简体中文",
    "English",
    "日本語",
)
DOCUMENT_GLOBS = ("*.md", "*.mdx", "*.rst")
LANGUAGE_HEADING_PATTERN = re.compile(
    r"(?m)^## (繁體中文|简体中文|English|日本語)\s*$"
)
FENCED_CODE_PATTERN = re.compile(
    r"(?ms)^(```|~~~)[^\n]*\n.*?^\1\s*$"
)
INLINE_CODE_PATTERN = re.compile(r"(?<!`)`([^`\n]+)`(?!`)")
MARKDOWN_TARGET_PATTERN = re.compile(r"!?\[[^\]]*\]\(([^)\s]+)(?:\s+[^)]*)?\)")
HTML_TARGET_PATTERN = re.compile(r"\b(?:href|src)=['\"]([^'\"]+)['\"]")
ADJACENT_ENGLISH_WORD_PATTERN = re.compile(
    r"\b(?P<word>[A-Za-z][A-Za-z0-9-]{2,})"
    r"(?:[ \t]+|\r?\n[ \t]*)"
    r"(?P=word)\b",
    re.IGNORECASE,
)


def _tracked_documents(root: Path) -> tuple[Path, ...]:
    result = subprocess.run(
        [
            "git",
            "-c",
            f"safe.directory={root.as_posix()}",
            "ls-files",
            "--cached",
            "--others",
            "--exclude-standard",
            "--",
            *DOCUMENT_GLOBS,
        ],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if result.returncode:
        detail = result.stderr.strip() or "git ls-files failed"
        raise RuntimeError(detail)
    relative_paths = sorted(set(result.stdout.splitlines()))
    return tuple(root / line for line in relative_paths if line)


def _prefix_errors(prefix: str, *, require_h1: bool) -> list[str]:
    visible = [line.strip() for line in prefix.splitlines() if line.strip()]
    if not visible:
        return ["a four-language H1 is required"] if require_h1 else []
    if len(visible) != 1 or not visible[0].startswith("# "):
        return ["only one four-language H1 may appear before the language sections"]
    title_parts = [part.strip() for part in visible[0][2:].split("／")]
    if len(title_parts) != 4 or any(not part for part in title_parts):
        return ["H1 must contain four non-empty titles separated by ／"]
    return []


def _extract_sections(
    text: str,
    *,
    require_h1: bool,
) -> tuple[str, tuple[str, ...], list[str]]:
    matches = tuple(LANGUAGE_HEADING_PATTERN.finditer(text))
    names = tuple(match.group(1) for match in matches)
    if names != LANGUAGE_HEADINGS:
        return "", (), [
            "language sections must appear exactly once in this order: "
            "繁體中文, 简体中文, English, 日本語"
        ]

    prefix = text[: matches[0].start()]
    sections: list[str] = []
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        section = text[start:end].strip()
        sections.append(section)
    errors = _prefix_errors(prefix, require_h1=require_h1)
    all_h2_headings = tuple(
        match.group(1).strip()
        for match in re.finditer(r"(?m)^##\s+(.+?)\s*$", text)
    )
    if all_h2_headings != LANGUAGE_HEADINGS:
        errors.append(
            "the only H2 headings must be the four language sections in "
            "the required order"
        )
    prefix_h1_count = len(re.findall(r"(?m)^#\s+\S", prefix))
    all_h1_count = len(re.findall(r"(?m)^#\s+\S", text))
    if all_h1_count != prefix_h1_count:
        errors.append("H1 may appear only before the four language sections")
    for name, section in zip(LANGUAGE_HEADINGS, sections, strict=True):
        if not section:
            errors.append(f"{name} section is empty")
    return prefix, tuple(sections), errors


def _paragraph_count(section: str) -> int:
    without_code = FENCED_CODE_PATTERN.sub("\n<CODE-BLOCK>\n", section)
    blocks = re.split(r"\n\s*\n", without_code.strip())
    return sum(1 for block in blocks if block.strip())


def _technical_inline_code(section: str) -> Counter[str]:
    tokens = INLINE_CODE_PATTERN.findall(section)
    return Counter(
        token
        for token in tokens
        if not re.search(r"\s", token)
        or re.search(r"[.=\\<>]", token)
        or token.startswith("-")
    )


def _structure(section: str) -> dict[str, object]:
    fenced_blocks = tuple(match.group(0).strip() for match in FENCED_CODE_PATTERN.finditer(section))
    markdown_targets = tuple(MARKDOWN_TARGET_PATTERN.findall(section))
    html_targets = tuple(HTML_TARGET_PATTERN.findall(section))
    return {
        "paragraphs": _paragraph_count(section),
        "subheadings": len(re.findall(r"(?m)^#{3,6}\s+\S", section)),
        "bullets": len(re.findall(r"(?m)^\s*[-*+]\s+", section)),
        "ordered_items": len(re.findall(r"(?m)^\s*\d+[.)]\s+", section)),
        "blockquotes": len(re.findall(r"(?m)^\s*>\s?", section)),
        "table_rows": len(re.findall(r"(?m)^\s*\|.*\|\s*$", section)),
        "checkboxes": len(re.findall(r"(?m)^\s*[-*+]\s+\[[ xX]\]\s+", section)),
        "fenced_blocks": fenced_blocks,
        "technical_inline_code": _technical_inline_code(section),
        "markdown_targets": Counter(markdown_targets),
        "html_targets": Counter(html_targets),
        "raw_urls": Counter(re.findall(r"https?://[^\s)>]+", section)),
    }


def _english_repetition_errors(section: str) -> list[str]:
    prose = FENCED_CODE_PATTERN.sub("", section)
    prose = INLINE_CODE_PATTERN.sub("<INLINE-CODE>", prose)
    return [
        f"English section repeats adjacent word {match.group('word')!r}"
        for match in ADJACENT_ENGLISH_WORD_PATTERN.finditer(prose)
    ]


def audit_text(text: str, *, require_h1: bool = False) -> list[str]:
    _, sections, errors = _extract_sections(text, require_h1=require_h1)
    if errors or not sections:
        return errors

    errors.extend(_english_repetition_errors(sections[2]))

    structures = tuple(_structure(section) for section in sections)
    keys = tuple(structures[0])
    for key in keys:
        values = tuple(structure[key] for structure in structures)
        if any(value != values[0] for value in values[1:]):
            errors.append(
                f"{key} differs across language sections: "
                + ", ".join(
                    f"{name}={value!r}"
                    for name, value in zip(LANGUAGE_HEADINGS, values, strict=True)
                )
            )

    section_lines = tuple(
        Counter(line.strip() for line in section.splitlines() if line.strip())
        for section in sections
    )
    for left_index, left_counter in enumerate(section_lines):
        for right_index in range(left_index + 1, len(section_lines)):
            if left_counter == section_lines[right_index]:
                errors.append(
                    f"{LANGUAGE_HEADINGS[right_index]} duplicates "
                    f"{LANGUAGE_HEADINGS[left_index]} instead of providing "
                    "a translation"
                )
    return errors


def audit_document(path: Path) -> list[str]:
    return audit_text(path.read_text(encoding="utf-8"), require_h1=True)


def audit_repository(root: Path) -> dict[Path, list[str]]:
    failures: dict[Path, list[str]] = {}
    for path in _tracked_documents(root):
        errors = audit_document(path)
        if errors:
            failures[path.relative_to(root)] = errors
    return failures


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    failures = audit_repository(root)
    if failures:
        for path, errors in failures.items():
            print(f"FAIL: {path}", file=sys.stderr)
            for error in errors:
                print(f"  - {error}", file=sys.stderr)
        return 1
    print("FOUR_LANGUAGE_DOCUMENTATION_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
