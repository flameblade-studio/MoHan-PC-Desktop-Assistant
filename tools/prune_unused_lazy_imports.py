from __future__ import annotations

lazy import argparse
lazy import ast
lazy from pathlib import Path


def _bound_name(alias: ast.alias, *, from_import: bool) -> str:
    if alias.asname:
        return alias.asname
    return alias.name if from_import else alias.name.partition(".")[0]


def _render_alias(alias: ast.alias) -> str:
    return alias.name if alias.asname is None else f"{alias.name} as {alias.asname}"


def _render_import(
    node: ast.Import | ast.ImportFrom,
    aliases: tuple[ast.alias, ...],
) -> str:
    prefix = "lazy " if getattr(node, "is_lazy", False) else ""
    names = ", ".join(_render_alias(alias) for alias in aliases)
    if isinstance(node, ast.Import):
        return f"{prefix}import {names}"
    module = "." * node.level + (node.module or "")
    return f"{prefix}from {module} import {names}"


def _public_exports(tree: ast.Module) -> frozenset[str]:
    exports: set[str] = set()
    for node in tree.body:
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else (node.target,)
        if not any(
            isinstance(target, ast.Name) and target.id == "__all__"
            for target in targets
        ):
            continue
        value = node.value
        if not isinstance(value, (ast.List, ast.Set, ast.Tuple)):
            continue
        exports.update(
            element.value
            for element in value.elts
            if isinstance(element, ast.Constant)
            and isinstance(element.value, str)
        )
    return frozenset(exports)


def prune_unused_lazy_imports(path: Path) -> int:
    """Remove unused generated lazy imports without touching eager side effects."""

    source_bytes = path.read_bytes()
    source = source_bytes.decode("utf-8")
    tree = ast.parse(source, filename=str(path))
    loaded_names = {
        node.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load)
    }
    loaded_names.update(_public_exports(tree))
    candidates = [
        node
        for node in tree.body
        if isinstance(node, (ast.Import, ast.ImportFrom))
        and getattr(node, "is_lazy", False)
    ]
    replacements: list[tuple[int, int, str]] = []
    removed = 0
    for node in candidates:
        from_import = isinstance(node, ast.ImportFrom)
        aliases = tuple(
            alias
            for alias in node.names
            if alias.name == "*"
            or _bound_name(alias, from_import=from_import) in loaded_names
        )
        if len(aliases) == len(node.names):
            continue
        removed += len(node.names) - len(aliases)
        replacement = _render_import(node, aliases) if aliases else ""
        replacements.append((node.lineno, node.end_lineno or node.lineno, replacement))

    if not replacements:
        return 0

    newline = "\r\n" if b"\r\n" in source_bytes else "\n"
    lines = source.splitlines(keepends=True)
    for start, end, replacement in reversed(replacements):
        replacement_lines = [replacement + newline] if replacement else []
        lines[start - 1 : end] = replacement_lines
    rewritten = "".join(lines)
    ast.parse(rewritten, filename=str(path))
    path.write_bytes(rewritten.encode("utf-8"))
    return removed


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", type=Path, nargs="+")
    arguments = parser.parse_args()
    for path in arguments.paths:
        removed = prune_unused_lazy_imports(path)
        print(f"{path}: removed {removed} unused lazy imports")


if __name__ == "__main__":
    main()
