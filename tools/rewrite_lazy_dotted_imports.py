from __future__ import annotations

lazy from pathlib import Path

lazy from migrate_python315_imports import python_files

ALIASES = frozendict({
    "urllib.error": "urllib_error",
    "urllib.parse": "urllib_parse",
    "urllib.request": "urllib_request",
    "importlib.metadata": "importlib_metadata",
})


def main() -> int:
    changed = 0
    for path in python_files():
        if path.name in {
            Path(__file__).name,
            "rewrite_lazy_module_members.py",
        }:
            continue
        original = path.read_text(encoding="utf-8")
        lines: list[str] = []
        for line in original.splitlines(keepends=True):
            updated_line = line
            for dotted, alias in ALIASES.items():
                if line.strip() == f"lazy import {dotted}":
                    indent = line[: len(line) - len(line.lstrip())]
                    ending = "\n" if line.endswith("\n") else ""
                    updated_line = f"{indent}lazy import {dotted} as {alias}{ending}"
                elif not line.lstrip().startswith(("lazy from ", "from ")):
                    updated_line = updated_line.replace(dotted, alias)
            lines.append(updated_line)
        updated = "".join(lines)
        if updated != original:
            path.write_text(updated, encoding="utf-8", newline="")
            changed += 1
    print(f"PYTHON315_DOTTED_LAZY_IMPORTS_REWRITTEN files={changed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
