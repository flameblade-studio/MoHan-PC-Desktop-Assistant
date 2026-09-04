from __future__ import annotations

lazy import os
lazy import re

TITLE_SEPARATOR = "／"
LANGUAGE_COUNT = 4
PACKAGE_PATTERN = r"[A-Za-z0-9@][A-Za-z0-9._/@+-]*"
VERSION_PATTERN = (
    r"v?[0-9]+(?:\.[0-9]+){0,2}"
    r"(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?"
)
DEPENDABOT_TITLE = re.compile(
    rf"build\(deps(?:-[a-z0-9]+)?\): bump "
    rf"(?P<package>{PACKAGE_PATTERN}) from "
    rf"(?P<from_version>{VERSION_PATTERN}) to "
    rf"(?P<to_version>{VERSION_PATTERN})"
)


def normalize_title(title: str) -> str | None:
    """Return a safe four-language title, or None when parsing must stop."""

    parts = title.split(TITLE_SEPARATOR)
    if len(parts) == LANGUAGE_COUNT and all(part.strip() for part in parts):
        return title

    match = DEPENDABOT_TITLE.fullmatch(title)
    if match is None:
        return None

    package = match.group("package")
    from_version = match.group("from_version")
    to_version = match.group("to_version")
    change = f"{package} {from_version} → {to_version}"
    return TITLE_SEPARATOR.join(
        (
            f"相依套件更新：{change}",
            f"依赖项更新：{change}",
            f"Dependency update: {change}",
            f"依存関係の更新：{change}",
        )
    )


def main() -> int:
    title = os.environ.get("PR_TITLE", "")
    normalized = normalize_title(title)
    if normalized is not None:
        print(normalized)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
