from __future__ import annotations

lazy import argparse
lazy import ast
lazy from pathlib import Path


def _defined_names(node: ast.stmt) -> frozenset[str]:
    if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
        return frozenset({node.name})
    if isinstance(node, (ast.Assign, ast.AnnAssign)):
        targets = node.targets if isinstance(node, ast.Assign) else (node.target,)
        return frozenset(
            target.id for target in targets if isinstance(target, ast.Name)
        )
    return frozenset()


def _span(source: str, node: ast.AST) -> str:
    end_line = getattr(node, "end_lineno", None)
    if end_line is None:
        raise RuntimeError("Definition has no end line")
    starts = [node.lineno]
    starts.extend(item.lineno for item in getattr(node, "decorator_list", ()))
    lines = source.splitlines(keepends=True)
    return "".join(lines[min(starts) - 1 : end_line]).rstrip()


def extract_definitions(
    source_path: Path,
    output_path: Path,
    names: frozenset[str],
) -> None:
    if output_path.exists():
        raise FileExistsError(output_path)
    source_bytes = source_path.read_bytes()
    source = source_bytes.decode("utf-8")
    tree = ast.parse(source, filename=str(source_path))
    selected = [
        node for node in tree.body if _defined_names(node).intersection(names)
    ]
    found = frozenset().union(*(_defined_names(node) for node in selected))
    missing = names - found
    if missing:
        raise RuntimeError(f"Top-level definitions not found: {sorted(missing)!r}")
    if found != names:
        raise RuntimeError("A selected assignment defines unrequested names")
    imports = [
        _span(source, node)
        for node in tree.body
        if isinstance(node, (ast.Import, ast.ImportFrom))
        and not (
            isinstance(node, ast.ImportFrom)
            and node.module == "__future__"
        )
    ]
    output = (
        "from __future__ import annotations\n\n"
        + "\n".join(imports)
        + "\n\n"
        + "\n\n".join(_span(source, node) for node in selected)
        + "\n"
    )
    ast.parse(output, filename=str(output_path))
    removed: set[int] = set()
    for node in selected:
        starts = [node.lineno]
        starts.extend(item.lineno for item in getattr(node, "decorator_list", ()))
        if node.end_lineno is None:
            raise RuntimeError("Definition has no end line")
        removed.update(range(min(starts), node.end_lineno + 1))
    lines = source.splitlines(keepends=True)
    rewritten = "".join(
        line
        for line_number, line in enumerate(lines, start=1)
        if line_number not in removed
    )
    ast.parse(rewritten, filename=str(source_path))
    newline = "\r\n" if b"\r\n" in source_bytes else "\n"
    output_path.write_bytes(output.replace("\n", newline).encode("utf-8"))
    source_path.write_bytes(rewritten.encode("utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("names", nargs="+")
    arguments = parser.parse_args()
    extract_definitions(
        arguments.source,
        arguments.output,
        frozenset(arguments.names),
    )


if __name__ == "__main__":
    main()
