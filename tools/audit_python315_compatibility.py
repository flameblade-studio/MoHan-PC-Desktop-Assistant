from __future__ import annotations

lazy import ast
lazy from pathlib import Path

lazy from migrate_python315_imports import ROOT, python_files

REMOVED_CALLS = frozenset({
    "threading.activeCount",
    "threading.currentThread",
    "threading.enumerateThreads",
})
REMOVED_METHODS = frozenset({
    "getName",
    "isAlive",
    "isSet",
    "notifyAll",
    "setDaemon",
    "setName",
})
REMOVED_MODULES = frozenset({
    "aifc",
    "audioop",
    "cgi",
    "cgitb",
    "chunk",
    "crypt",
    "imghdr",
    "mailcap",
    "msilib",
    "nis",
    "nntplib",
    "ossaudiodev",
    "pipes",
    "sndhdr",
    "spwd",
    "sunau",
    "telnetlib",
    "uu",
    "xdrlib",
})


def call_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = call_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    return None


def keyword_present(node: ast.Call, name: str) -> bool:
    return any(keyword.arg == name for keyword in node.keywords)


def literal_mode(node: ast.Call) -> str | None:
    if keyword_present(node, "mode"):
        value = next(
            keyword.value for keyword in node.keywords if keyword.arg == "mode"
        )
    elif len(node.args) >= 2:
        value = node.args[1]
    else:
        return "r"
    return value.value if isinstance(value, ast.Constant) and isinstance(value.value, str) else None


class CompatibilityAudit(ast.NodeVisitor):
    def __init__(self, path: Path) -> None:
        self.path = path
        self.issues: list[str] = []

    def issue(self, node: ast.AST, code: str) -> None:
        self.issues.append(
            f"{code} {self.path.relative_to(ROOT)}:{getattr(node, 'lineno', 0)}"
        )

    def visit_Module(self, node: ast.Module) -> None:
        relative = self.path.relative_to(ROOT)
        audit_product_constants = relative.parts[0] not in {"tests", "tools"}
        if audit_product_constants:
            for statement in node.body:
                target: ast.expr | None = None
                value: ast.expr | None = None
                if isinstance(statement, ast.Assign) and len(statement.targets) == 1:
                    target, value = statement.targets[0], statement.value
                elif isinstance(statement, ast.AnnAssign):
                    target, value = statement.target, statement.value
                if (
                    isinstance(target, ast.Name)
                    and target.id[:1].isupper()
                    and isinstance(value, (ast.Dict, ast.DictComp))
                ):
                    self.issue(statement, f"MUTABLE_GLOBAL_CONFIG {target.id}")
        self.generic_visit(node)

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            if alias.name.partition(".")[0] in REMOVED_MODULES:
                self.issue(node, f"REMOVED_MODULE {alias.name}")

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.module and node.module.partition(".")[0] in REMOVED_MODULES:
            self.issue(node, f"REMOVED_MODULE {node.module}")

    def visit_Call(self, node: ast.Call) -> None:
        name = call_name(node.func)
        if name in REMOVED_CALLS or (
            isinstance(node.func, ast.Attribute)
            and node.func.attr in REMOVED_METHODS
        ):
            self.issue(node, f"REMOVED_API {name}")

        if name in {"open", "builtins.open", "io.open"}:
            mode = literal_mode(node)
            if (
                (mode is None or "b" not in mode)
                and not keyword_present(node, "encoding")
            ):
                self.issue(node, "TEXT_ENCODING")
        elif isinstance(node.func, ast.Attribute) and node.func.attr in {
            "read_text",
            "write_text",
        }:
            # Distribution.read_text() reads installed
            # metadata and has no encoding parameter; it is not pathlib I/O.
            if (
                name != "distribution.read_text"
                and not keyword_present(node, "encoding")
            ):
                self.issue(node, "TEXT_ENCODING")
        elif name in {"NamedTemporaryFile", "tempfile.NamedTemporaryFile"}:
            # NamedTemporaryFile defaults to binary ``w+b`` rather than the
            # text ``r`` default used by open().  Audit it only when callers
            # explicitly request a text mode.
            mode = (
                next(
                    (
                        keyword.value.value
                        for keyword in node.keywords
                        if keyword.arg == "mode"
                        and isinstance(keyword.value, ast.Constant)
                        and isinstance(keyword.value.value, str)
                    ),
                    None,
                )
                if keyword_present(node, "mode")
                else None
            )
            if (
                mode is not None
                and "b" not in mode
                and not keyword_present(node, "encoding")
            ):
                self.issue(node, "TEXT_ENCODING")
        self.generic_visit(node)


def main() -> int:
    issues: list[str] = []
    files = python_files()
    for path in files:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        audit = CompatibilityAudit(path)
        audit.visit(tree)
        issues.extend(audit.issues)
    print("\n".join(issues))
    print(f"PYTHON315_COMPATIBILITY_AUDIT files={len(files)} issues={len(issues)}")
    return 1 if issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
