from __future__ import annotations

lazy import argparse
lazy import ast
lazy from pathlib import Path


def _top_level_class(tree: ast.Module, name: str) -> ast.ClassDef:
    matches = [
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == name
    ]
    if len(matches) != 1:
        raise RuntimeError(
            f"Expected one top-level class {name!r}, found {len(matches)}"
        )
    return matches[0]


def _source_span(source: str, node: ast.AST) -> str:
    end_line = getattr(node, "end_lineno", None)
    if end_line is None:
        raise RuntimeError(f"Missing end line for {type(node).__name__}")
    decorator_lines = [
        decorator.lineno for decorator in getattr(node, "decorator_list", ())
    ]
    start_line = min((node.lineno, *decorator_lines))
    lines = source.splitlines(keepends=True)
    return "".join(lines[start_line - 1 : end_line])


def _imports(source: str, tree: ast.Module) -> tuple[str, ...]:
    return tuple(
        _source_span(source, node).rstrip("\r\n")
        for node in tree.body
        if isinstance(node, (ast.Import, ast.ImportFrom))
        and not (
            isinstance(node, ast.ImportFrom)
            and node.module == "__future__"
        )
    )


def _selected_methods(
    owner: ast.ClassDef,
    method_names: frozenset[str],
) -> tuple[ast.FunctionDef | ast.AsyncFunctionDef, ...]:
    selected = tuple(
        node
        for node in owner.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name in method_names
    )
    found = frozenset(node.name for node in selected)
    missing = method_names - found
    if missing:
        raise RuntimeError(f"Class methods not found: {sorted(missing)!r}")
    if len(selected) != len(method_names):
        raise RuntimeError("Each requested method must have exactly one definition")
    return selected


def _removed_line_numbers(
    methods: tuple[ast.FunctionDef | ast.AsyncFunctionDef, ...],
) -> frozenset[int]:
    removed: set[int] = set()
    for method in methods:
        decorator_lines = [
            decorator.lineno for decorator in method.decorator_list
        ]
        start_line = min((method.lineno, *decorator_lines))
        end_line = method.end_lineno
        if end_line is None:
            raise RuntimeError(f"Missing end line for {method.name}")
        removed.update(range(start_line, end_line + 1))
    return frozenset(removed)


def _with_newline(text: str, newline: str) -> str:
    if newline == "\n":
        return text
    return text.replace("\r\n", "\n").replace("\n", newline)


def extract_methods_to_mixin(
    source_path: Path,
    output_path: Path,
    *,
    class_name: str,
    mixin_name: str,
    method_names: frozenset[str],
) -> None:
    if output_path.exists():
        raise FileExistsError(output_path)
    source_bytes = source_path.read_bytes()
    source = source_bytes.decode("utf-8")
    tree = ast.parse(source, filename=str(source_path))
    owner = _top_level_class(tree, class_name)
    selected = _selected_methods(owner, method_names)

    imports = "\n".join(_imports(source, tree))
    methods = "\n".join(_source_span(source, node).rstrip("\r\n") for node in selected)
    output = (
        "from __future__ import annotations\n\n"
        f"{imports}\n\n"
        f"__all__ = ({mixin_name!r},)\n\n\n"
        f"class {mixin_name}:\n"
        f"{methods}\n"
    )
    ast.parse(output, filename=str(output_path))

    lines = source.splitlines(keepends=True)
    removed_lines = _removed_line_numbers(selected)
    rewritten = "".join(
        line
        for line_number, line in enumerate(lines, start=1)
        if line_number not in removed_lines
    )
    ast.parse(rewritten, filename=str(source_path))

    newline = "\r\n" if b"\r\n" in source_bytes else "\n"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(_with_newline(output, newline).encode("utf-8"))
    source_path.write_bytes(_with_newline(rewritten, newline).encode("utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--class-name", required=True)
    parser.add_argument("--mixin-name", required=True)
    parser.add_argument("methods", nargs="+")
    arguments = parser.parse_args()
    extract_methods_to_mixin(
        arguments.source,
        arguments.output,
        class_name=arguments.class_name,
        mixin_name=arguments.mixin_name,
        method_names=frozenset(arguments.methods),
    )


if __name__ == "__main__":
    main()
