"""Validate and assemble per-change changelog fragments.

Release Please owns the versioned history in ``CHANGELOG.md``.  This tool is
run on the Release Please pull-request branch after Release Please has created
the next version heading.  It inserts sorted fragments below that heading and
removes them only after the changelog has been written successfully.
"""

from __future__ import annotations

lazy import argparse
lazy import re
lazy import sys
lazy from collections.abc import Sequence
lazy from dataclasses import dataclass
lazy from pathlib import Path
lazy from typing import Final, Literal

ROOT: Final = Path(__file__).resolve().parents[1]
FRAGMENT_DIR_NAME: Final = "changelog.d"
LANGUAGE_SEPARATOR: Final = "／"
LANGUAGE_HEADINGS: Final = (
    "繁體中文",
    "简体中文",
    "English",
    "日本語",
)
LEGACY_LANGUAGE_PREFIXES: Final = (
    "未發布",
    "未发布",
    "Unreleased",
    "未リリース",
)
TITLE_PATTERN: Final = re.compile(r"(?m)^### (?P<title>\S.*?)\s*$")
LOWER_HEADING_PATTERN: Final = re.compile(r"(?m)^#{1,2}\s+")
BULLET_PATTERN: Final = re.compile(r"^[*+-] (.+)$")


class ChangelogAssemblyError(ValueError):
    """Raised when a changelog or fragment violates the assembly contract."""


class FragmentFormatError(ChangelogAssemblyError):
    """Raised when a fragment is not a supported four-language format."""


@dataclass(frozen=True, slots=True)
class ParsedFragment:
    kind: Literal["slash", "legacy"]
    titles: tuple[str, ...]
    sections: tuple[str, ...]
    bullet_rows: tuple[tuple[str, ...], ...]


def _language_parts(value: str) -> tuple[str, ...]:
    return tuple(part.strip() for part in value.split(LANGUAGE_SEPARATOR))


def _non_empty_language_parts(value: str) -> tuple[str, ...] | None:
    parts = _language_parts(value)
    return parts if len(parts) == len(LANGUAGE_HEADINGS) and all(parts) else None


def _visible_lines(value: str) -> tuple[str, ...]:
    return tuple(line for line in value.splitlines() if line.strip())


def _fragment_headings(text: str) -> tuple[re.Match[str], ...]:
    return tuple(TITLE_PATTERN.finditer(text))


def _validate_preferred_fragment(
    text: str,
    heading: re.Match[str],
) -> tuple[tuple[str, ...], tuple[tuple[str, ...], ...], list[str]]:
    errors: list[str] = []
    title_parts = _non_empty_language_parts(heading.group("title"))
    if title_parts is None:
        errors.append(
            "fragment title must contain four non-empty titles separated by ／"
        )
        title_parts = (heading.group("title"),) * len(LANGUAGE_HEADINGS)

    body_lines = _visible_lines(text[heading.end() :])
    bullet_rows: list[tuple[str, ...]] = []
    for line in body_lines:
        match = BULLET_PATTERN.fullmatch(line)
        if match is None:
            errors.append("fragment body must contain bullets only")
            continue
        parts = _non_empty_language_parts(match.group(1))
        if parts is None:
            errors.append(
                "every fragment bullet must contain four non-empty language "
                "entries separated by ／"
            )
            continue
        bullet_rows.append(parts)
    if not bullet_rows:
        errors.append("fragment must contain at least one bullet")
    return title_parts, tuple(bullet_rows), errors


def _validate_legacy_fragment(
    text: str,
    headings: tuple[re.Match[str], ...],
) -> tuple[
    tuple[str, ...],
    tuple[str, ...],
    tuple[tuple[str, ...], ...],
    list[str],
]:
    errors: list[str] = []
    titles = tuple(match.group("title") for match in headings)
    for index, (title, language, prefix) in enumerate(
        zip(titles, LANGUAGE_HEADINGS, LEGACY_LANGUAGE_PREFIXES, strict=True),
        start=1,
    ):
        if not title.startswith(prefix):
            errors.append(
                f"legacy fragment heading {index} must be the {language} "
                f"unreleased title"
            )

    sections = tuple(
        text[
            heading.start() : (
                headings[index + 1].start() if index + 1 < len(headings) else len(text)
            )
        ].rstrip("\r\n")
        for index, heading in enumerate(headings)
    )
    language_bullets: list[tuple[str, ...]] = []
    for index, heading in enumerate(headings):
        end = headings[index + 1].start() if index + 1 < len(headings) else len(text)
        bullets: list[str] = []
        for line in _visible_lines(text[heading.end() : end]):
            match = BULLET_PATTERN.fullmatch(line)
            if match is None:
                errors.append("legacy fragment body must contain bullets only")
                continue
            bullets.append(match.group(1).strip())
        language_bullets.append(tuple(bullets))

    bullet_counts = tuple(len(bullets) for bullets in language_bullets)
    if not all(bullet_counts):
        errors.append("each legacy language section must contain a bullet")
    if len(set(bullet_counts)) != 1:
        errors.append(
            "legacy language sections must contain the same number of bullets"
        )
    bullet_rows = (
        tuple(zip(*language_bullets, strict=True))
        if language_bullets and len(set(bullet_counts)) == 1 and all(bullet_counts)
        else ()
    )
    return titles, sections, bullet_rows, errors


def parse_fragment(text: str) -> ParsedFragment:
    """Parse one fragment, raising a descriptive error on invalid content."""

    normalized = text.replace("\r\n", "\n")
    headings = _fragment_headings(normalized)
    errors: list[str] = []
    if not headings:
        errors.append("fragment requires a ### title heading")
    if headings:
        if normalized[: headings[0].start()].strip():
            errors.append("fragment must begin with its title heading")
    elif normalized.strip():
        errors.append("fragment must begin with its title heading")
    if LOWER_HEADING_PATTERN.search(normalized):
        errors.append("fragment may not contain H1 or H2 headings")

    if len(headings) == 1:
        titles, bullet_rows, preferred_errors = _validate_preferred_fragment(
            normalized,
            headings[0],
        )
        errors.extend(preferred_errors)
        sections = ()
        kind: Literal["slash", "legacy"] = "slash"
    elif len(headings) == len(LANGUAGE_HEADINGS):
        titles, sections, bullet_rows, legacy_errors = _validate_legacy_fragment(
            normalized,
            headings,
        )
        errors.extend(legacy_errors)
        kind = "legacy"
    else:
        errors.append(
            "fragment must contain one four-language title or four legacy "
            "language titles"
        )
        titles = tuple(
            match.group("title") for match in headings[: len(LANGUAGE_HEADINGS)]
        )
        titles = (titles + ("",) * len(LANGUAGE_HEADINGS))[: len(LANGUAGE_HEADINGS)]
        sections = ()
        bullet_rows = ()
        kind = "slash"

    if errors:
        raise FragmentFormatError("; ".join(errors))
    return ParsedFragment(kind, tuple(titles), tuple(sections), tuple(bullet_rows))


def validate_fragment(text: str) -> tuple[str, ...]:
    """Return all format errors without mutating or raising for bad input."""

    try:
        parse_fragment(text)
    except FragmentFormatError as error:
        return tuple(str(error).split("; "))
    return ()


def fragment_document(text: str) -> str:
    """Render a fragment as a synthetic four-language document for auditing."""

    fragment = parse_fragment(text)
    lines = [f"# {LANGUAGE_SEPARATOR.join(fragment.titles)}", ""]
    if fragment.kind == "slash":
        language_sections = tuple(
            "\n".join([
                f"### {fragment.titles[index]}",
                "",
                *(f"* {row[index]}" for row in fragment.bullet_rows),
            ])
            for index in range(len(LANGUAGE_HEADINGS))
        )
    else:
        language_sections = fragment.sections

    for language, section in zip(
        LANGUAGE_HEADINGS,
        language_sections,
        strict=True,
    ):
        lines.extend((f"## {language}", "", section.rstrip("\r\n"), ""))
    return "\n".join(lines).rstrip("\n") + "\n"


def _assembly_payload(fragment: ParsedFragment, original: str) -> str:
    """Render a validated fragment in the format used by CHANGELOG.md."""

    if fragment.kind == "slash":
        return original.replace("\r\n", "\n").rstrip("\n")

    title = LANGUAGE_SEPARATOR.join(fragment.titles)
    lines = [f"### {title}", ""]
    lines.extend(f"* {LANGUAGE_SEPARATOR.join(row)}" for row in fragment.bullet_rows)
    return "\n".join(lines)


def _version_heading_pattern(selector: str) -> re.Pattern[str]:
    value = selector.strip()
    if value.startswith("## "):
        return re.compile(rf"(?m)^{re.escape(value)}[ \t]*\r?$")
    version = value.removeprefix("v")
    return re.compile(rf"(?m)^## \[v?{re.escape(version)}\]\([^\n]+\).*$")


def _version_heading(changelog: str, selector: str) -> re.Match[str]:
    matches = tuple(_version_heading_pattern(selector).finditer(changelog))
    if not matches:
        raise ChangelogAssemblyError(f"version heading not found: {selector!r}")
    if len(matches) != 1:
        raise ChangelogAssemblyError(f"version heading is ambiguous: {selector!r}")
    return matches[0]


def assemble_text(
    changelog: str,
    fragments: Sequence[tuple[str | Path, str]],
    version: str,
) -> str:
    """Return ``changelog`` with sorted, validated fragments inserted."""

    ordered = tuple(
        sorted(
            fragments,
            key=lambda item: (
                Path(item[0]).name.casefold(),
                Path(item[0]).name,
            ),
        )
    )
    if not ordered:
        return changelog

    payloads: list[str] = []
    for name, fragment_text in ordered:
        try:
            fragment = parse_fragment(fragment_text)
        except FragmentFormatError as error:
            raise FragmentFormatError(f"{Path(name).name}: {error}") from error
        payloads.append(_assembly_payload(fragment, fragment_text))

    heading = _version_heading(changelog, version)
    newline = "\r\n" if "\r\n" in changelog else "\n"
    suffix = re.sub(r"^(?:\r?\n)+", "", changelog[heading.end() :])
    payload = (newline * 2).join(payloads).replace("\n", newline)
    separator = newline * 2 if suffix else newline
    return changelog[: heading.end()] + newline * 2 + payload + separator + suffix


def load_fragments(directory: Path) -> tuple[tuple[Path, str], ...]:
    """Load direct Markdown fragments, excluding the directory README."""

    if not directory.is_dir():
        return ()
    paths = tuple(
        sorted(
            (
                path
                for path in directory.glob("*.md")
                if path.name.casefold() != "readme.md"
            ),
            key=lambda path: (path.name.casefold(), path.name),
        )
    )
    fragments: list[tuple[Path, str]] = []
    for path in paths:
        with path.open(encoding="utf-8", newline="") as handle:
            fragments.append((path, handle.read()))
    return tuple(fragments)


def _arguments(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Assemble changelog.d fragments below a Release Please version heading."
        )
    )
    parser.add_argument(
        "--version",
        required=True,
        help="Version number (for example 4.7.0) or an exact ## heading.",
    )
    parser.add_argument(
        "--changelog",
        type=Path,
        default=ROOT / "CHANGELOG.md",
        help="Changelog path override.",
    )
    parser.add_argument(
        "--fragments-dir",
        "--fragments",
        dest="fragments_dir",
        type=Path,
        default=ROOT / FRAGMENT_DIR_NAME,
        help="Fragment directory override.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the assembled changelog without writing or deleting files.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    arguments = _arguments(argv)
    changelog_path = arguments.changelog.resolve()
    fragments_dir = arguments.fragments_dir.resolve()
    try:
        fragments = load_fragments(fragments_dir)
        if not fragments:
            print("CHANGELOG_ASSEMBLY_NOOP fragments=0")
            return 0
        with changelog_path.open(encoding="utf-8", newline="") as handle:
            changelog = handle.read()
        assembled = assemble_text(changelog, fragments, arguments.version)
        if arguments.dry_run:
            print(
                f"CHANGELOG_ASSEMBLY_DRY_RUN fragments={len(fragments)} "
                f"version={arguments.version}"
            )
            print(assembled, end="")
            return 0
        changelog_path.write_text(assembled, encoding="utf-8", newline="")
        for path, _ in fragments:
            path.unlink()
    except (ChangelogAssemblyError, OSError) as error:
        print(f"CHANGELOG_ASSEMBLY_FAILED: {error}", file=sys.stderr)
        return 2
    print(
        f"CHANGELOG_ASSEMBLED fragments={len(fragments)} "
        f"version={arguments.version} path={changelog_path}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
