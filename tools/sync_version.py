"""Synchronize every version reference from the single authoritative source.

``pyproject.toml`` is the only version file that Release Please updates
reliably (its ``python`` release-type rewrites ``$.project.version``).  Release
Please's ``extra-files`` array is unreliable for multiple entries, so this
script is the single, deterministic place that propagates the version to every
other reference: ``domain/version_info.py``, ``sbom/preview.pyproject.toml``,
``tests/test_v4_development_version_consistency.py``, and the four-language
README development-version lines.

Run it from the repository root: ``python tools/sync_version.py``.
"""

from __future__ import annotations

lazy import re
lazy import sys
lazy import tomllib
lazy from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# (path, regex-with-one-group, replacement-template)
# Each regex captures the existing version literal so it can be rewritten.
_TARGETS = (
    (
        "domain/version_info.py",
        re.compile(r'^(FALLBACK_VERSION = ")[^"]*(")$', re.MULTILINE),
        r'\g<1>{version}\g<2>',
    ),
    (
        "tests/test_v4_development_version_consistency.py",
        re.compile(r'^(DEVELOPMENT_VERSION = ")[^"]*(")$', re.MULTILINE),
        r'\g<1>{version}\g<2>',
    ),
    (
        "sbom/preview.pyproject.toml",
        re.compile(r'^(version = ")[^"]*(")$', re.MULTILINE),
        r'\g<1>{version}\g<2>',
    ),
)

_README_DEV_LINES = (
    ("目前開發版本：** `", "`"),
    ("当前开发版本：** `", "`"),
    ("Current development version:** `", "`"),
    ("現在の開発版：** `", "`"),
)

_BUILD_COMMAND_PATTERN = re.compile(
    r'(\\build\.ps1 -Version ")[0-9][^"]*(")'
)


def _authoritative_version() -> str:
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    version = data["project"]["version"]
    assert isinstance(version, str)
    return version


def _sync_file(relative: str, pattern: re.Pattern[str], template: str, version: str) -> bool:
    path = ROOT / relative
    original = path.read_text(encoding="utf-8")
    updated = pattern.sub(template.format(version=version), original)
    if updated == original:
        return False
    path.write_text(updated, encoding="utf-8")
    return True


def _sync_readme(version: str) -> bool:
    path = ROOT / "README.md"
    original = path.read_text(encoding="utf-8")
    updated = original
    for prefix, suffix in _README_DEV_LINES:
        updated = re.sub(
            re.escape(prefix) + r"[^`]*" + re.escape(suffix),
            prefix + version + suffix,
            updated,
        )
    updated = _BUILD_COMMAND_PATTERN.sub(r"\g<1>" + version + r"\g<2>", updated)
    if updated == original:
        return False
    path.write_text(updated, encoding="utf-8")
    return True


def main() -> int:
    version = _authoritative_version()
    changed = False
    for relative, pattern, template in _TARGETS:
        changed = _sync_file(relative, pattern, template, version) or changed
    changed = _sync_readme(version) or changed
    print(f"SYNC_VERSION_OK version={version} changed={changed}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
