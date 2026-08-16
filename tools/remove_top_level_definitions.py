from __future__ import annotations

lazy import argparse
lazy import ast
lazy from pathlib import Path


def _defined_names(node: ast.AST) -> frozenset[str]:
    if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
        return frozenset({node.name})
    if isinstance(node, (ast.Assign, ast.AnnAssign)):
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        return frozenset(
            target.id for target in targets if isinstance(target, ast.Name)
        )
    return frozenset()


def _definition_scope(
    tree: ast.Module,
    class_name: str | None,
) -> tuple[list[ast.stmt], str]:
    if class_name is None:
        return tree.body, "Top-level"
    matches = [
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == class_name
    ]
    if len(matches) != 1:
        raise RuntimeError(
            f"Expected one top-level class {class_name!r}, found {len(matches)}"
        )
    return matches[0].body, f"Class {class_name!r}"


def class_definition_names(path: Path, class_name: str) -> frozenset[str]:
    """Return every method defined directly by one top-level class."""

    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    scope, _scope_label = _definition_scope(tree, class_name)
    return frozenset(
        node.name
        for node in scope
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    )


def remove_definitions(
    path: Path,
    names: frozenset[str],
    *,
    class_name: str | None = None,
) -> None:
    """Remove complete definitions without reformatting unaffected lines."""

    source_bytes = path.read_bytes()
    source = source_bytes.decode("utf-8")
    tree = ast.parse(source, filename=str(path))
    ranges: list[tuple[int, int]] = []
    found: set[str] = set()
    scope, scope_label = _definition_scope(tree, class_name)
    for node in scope:
        matches = _defined_names(node) & names
        if not matches:
            continue
        if not hasattr(node, "end_lineno") or node.end_lineno is None:
            raise RuntimeError(f"Missing end line for {sorted(matches)!r}")
        found.update(matches)
        decorator_lines = [
            decorator.lineno
            for decorator in getattr(node, "decorator_list", ())
        ]
        start_line = min((node.lineno, *decorator_lines))
        ranges.append((start_line, node.end_lineno))
    missing = names - found
    if missing:
        raise RuntimeError(
            f"{scope_label} definitions not found: {sorted(missing)!r}"
        )

    lines = source.splitlines(keepends=True)
    removed = {*range(start, end + 1) for start, end in ranges}
    rewritten = "".join(
        line
        for line_number, line in enumerate(lines, start=1)
        if line_number not in removed
    )
    ast.parse(rewritten, filename=str(path))
    newline = "\r\n" if b"\r\n" in source_bytes else "\n"
    if newline == "\r\n":
        rewritten = rewritten.replace("\r\n", "\n").replace("\n", "\r\n")
    path.write_bytes(rewritten.encode("utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--class-name")
    parser.add_argument(
        "--names-from-class",
        nargs=2,
        metavar=("PATH", "CLASS_NAME"),
    )
    parser.add_argument("path", type=Path)
    parser.add_argument("names", nargs="*")
    arguments = parser.parse_args()
    names = frozenset(arguments.names)
    if arguments.names_from_class is not None:
        source_path, source_class = arguments.names_from_class
        names |= class_definition_names(Path(source_path), source_class)
    if not names:
        parser.error("provide names or --names-from-class")
    remove_definitions(
        arguments.path,
        names,
        class_name=arguments.class_name,
    )


if __name__ == "__main__":
    main()
