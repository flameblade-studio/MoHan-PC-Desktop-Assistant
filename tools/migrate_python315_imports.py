from __future__ import annotations

lazy import argparse
lazy import ast
lazy from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED_PARTS = frozenset({
    ".git",
    ".ruff_cache",
    ".venv",
    ".venv315",
    "__pycache__",
    "build",
    "build-temp",
    "dist",
    "release-artifacts",
})


class ImportInventory(ast.NodeVisitor):
    def __init__(self) -> None:
        self.eligible: list[int] = []
        self.restricted: list[tuple[int, str]] = []
        self._restriction: str | None = None

    def _visit_restricted(self, node: ast.AST, reason: str) -> None:
        previous = self._restriction
        self._restriction = reason
        self.generic_visit(node)
        self._restriction = previous

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._visit_restricted(node, "function")

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._visit_restricted(node, "function")

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self._visit_restricted(node, "class")

    def visit_Try(self, node: ast.Try) -> None:
        self._visit_restricted(node, "try")

    def visit_TryStar(self, node: ast.TryStar) -> None:
        self._visit_restricted(node, "try")

    def _record(self, node: ast.Import | ast.ImportFrom) -> None:
        if self._restriction is not None:
            self.restricted.append((node.lineno, self._restriction))
            return
        if getattr(node, "is_lazy", False):
            return
        self.eligible.append(node.lineno)

    def visit_Import(self, node: ast.Import) -> None:
        self._record(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.module == "__future__":
            return
        if any(alias.name == "*" for alias in node.names):
            self.restricted.append((node.lineno, "star"))
            return
        self._record(node)


def python_files(root: Path = ROOT) -> list[Path]:
    return sorted(
        path
        for path in root.rglob("*.py")
        if not any(part in EXCLUDED_PARTS for part in path.parts)
    )


def inventory(path: Path) -> ImportInventory:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    result = ImportInventory()
    result.visit(tree)
    return result


def migrate(path: Path) -> int:
    result = inventory(path)
    if not result.eligible:
        return 0
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    for line_number in result.eligible:
        line = lines[line_number - 1]
        indentation = line[: len(line) - len(line.lstrip())]
        lines[line_number - 1] = f"{indentation}lazy {line[len(indentation):]}"
    path.write_text("".join(lines), encoding="utf-8", newline="")
    return len(result.eligible)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Migrate every Python 3.15-eligible module import to PEP 810."
    )
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    files = python_files()
    pending: list[tuple[Path, int]] = []
    restricted: list[tuple[Path, int, str]] = []
    for path in files:
        result = inventory(path)
        pending.extend((path, line) for line in result.eligible)
        restricted.extend(
            (path, line, reason) for line, reason in result.restricted
        )

    if args.check:
        for path, line in pending:
            print(f"EAGER_ELIGIBLE {path.relative_to(ROOT)}:{line}")
        for path, line, reason in restricted:
            print(
                f"EAGER_RESTRICTED {path.relative_to(ROOT)}:{line} "
                f"reason={reason}"
            )
        print(
            f"PYTHON315_IMPORT_AUDIT files={len(files)} "
            f"pending={len(pending)} restricted={len(restricted)}"
        )
        return 1 if pending else 0

    migrated = sum(migrate(path) for path in files)
    print(
        f"PYTHON315_LAZY_IMPORTS_MIGRATED files={len(files)} "
        f"imports={migrated} restricted={len(restricted)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
