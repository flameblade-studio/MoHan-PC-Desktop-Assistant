from __future__ import annotations

lazy import ast
lazy from pathlib import Path

if __package__:
    lazy from .migrate_python315_imports import python_files
else:
    lazy from migrate_python315_imports import python_files

ALIASES = frozendict({
    "urllib.error": "urllib_error",
    "urllib.parse": "urllib_parse",
    "urllib.request": "urllib_request",
    "importlib.metadata": "importlib_metadata",
})


def _binding_names(node: ast.AST, candidates: dict[ast.alias, ast.Import]) -> set[str]:
    if isinstance(node, (ast.Import, ast.ImportFrom)):
        return {
            alias.asname or (
                alias.name if isinstance(node, ast.ImportFrom)
                else alias.name.partition(".")[0]
            )
            for alias in node.names
            if alias not in candidates
        }
    if isinstance(node, ast.Name) and not isinstance(node.ctx, ast.Load):
        return {node.id}
    if isinstance(node, (ast.Global, ast.Nonlocal)):
        return set(node.names)
    if isinstance(node, ast.alias):
        return set()
    return {
        value for field in ("name", "arg", "rest")
        if isinstance(value := getattr(node, field, None), str)
    }


def _validate_bindings(
    tree: ast.Module,
    candidates: dict[ast.alias, ast.Import],
    targets: dict[str, str],
    filename: str,
) -> None:
    roots = {name.partition(".")[0] for name in targets}
    aliases = set(targets.values())
    parents: dict[ast.AST, ast.AST] = {}
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            parents[child] = node

    for alias, node in candidates.items():
        if parents[node] is not tree:
            raise RuntimeError(f"Ambiguous lazy import binding at {filename}:{alias.lineno}")
    for node in ast.walk(tree):
        names = _binding_names(node, candidates)
        if names & (roots | aliases) or "*" in names:
            raise RuntimeError(f"Ambiguous name binding at {filename}:{node.lineno}")
        if isinstance(node, ast.Name):
            if node.id in aliases:
                raise RuntimeError(f"Existing alias binding at {filename}:{node.lineno}")
            if node.id in roots:
                parent = parents[node]
                dotted = (
                    f"{node.id}.{parent.attr}"
                    if isinstance(parent, ast.Attribute) and parent.value is node
                    else ""
                )
                if dotted not in targets or not isinstance(parent.ctx, ast.Load):
                    raise RuntimeError(f"Unsupported root binding at {filename}:{node.lineno}")


def rewrite_source(source: str, *, filename: str = "<source>") -> str:
    """Rewrite statically unambiguous top-level lazy imports and their uses."""
    tree = ast.parse(source, filename=filename)
    candidates: dict[ast.alias, ast.Import] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import) and getattr(node, "is_lazy", False):
            candidates.update({
                alias: node for alias in node.names
                if alias.name in ALIASES and alias.asname is None
            })
    if not candidates:
        return source
    targets = {alias.name: ALIASES[alias.name] for alias in candidates}
    _validate_bindings(tree, candidates, targets, filename)

    encoded = source.encode("utf-8")
    offsets = [0]
    for line in encoded.splitlines(keepends=True):
        offsets.append(offsets[-1] + len(line))
    replacements: list[tuple[int, int, bytes]] = []
    for alias in candidates:
        end = offsets[alias.end_lineno - 1] + alias.end_col_offset
        replacements.append((end, end, f" as {targets[alias.name]}".encode()))
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
            dotted = f"{node.value.id}.{node.attr}"
            if dotted in targets:
                start = offsets[node.lineno - 1] + node.col_offset
                end = offsets[node.end_lineno - 1] + node.end_col_offset
                replacements.append((start, end, targets[dotted].encode("utf-8")))
    for start, end, replacement in sorted(replacements, reverse=True):
        encoded = encoded[:start] + replacement + encoded[end:]
    rewritten = encoded.decode("utf-8")
    ast.parse(rewritten, filename=filename)
    return rewritten


def main() -> int:
    changed = 0
    for path in python_files():
        if path.name in {
            Path(__file__).name,
            "rewrite_lazy_module_members.py",
        }:
            continue
        original = path.read_bytes().decode("utf-8")
        updated = rewrite_source(original, filename=str(path))
        if updated != original:
            path.write_text(updated, encoding="utf-8", newline="")
            changed += 1
    print(f"PYTHON315_DOTTED_LAZY_IMPORTS_REWRITTEN files={changed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
