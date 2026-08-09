from __future__ import annotations

lazy import ast
lazy from pathlib import Path

lazy from migrate_python315_imports import ROOT, python_files


def call_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = call_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    return None


class IdiomAudit(ast.NodeVisitor):
    def __init__(self, path: Path) -> None:
        self.path = path
        self.findings: list[str] = []

    def finding(self, node: ast.AST, code: str) -> None:
        self.findings.append(
            f"{code} {self.path.relative_to(ROOT)}:{getattr(node, 'lineno', 0)}"
        )

    def visit_Assign(self, node: ast.Assign) -> None:
        if (
            any(isinstance(target, ast.Name) for target in node.targets)
            and isinstance(node.value, ast.Call)
            and call_name(node.value.func) == "object"
        ):
            self.finding(node, "LEGACY_OBJECT_SENTINEL")
        self.generic_visit(node)

    def visit_Import(self, node: ast.Import) -> None:
        if getattr(node, "is_lazy", 0):
            for alias in node.names:
                if "." in alias.name:
                    self.finding(node, f"LAZY_DOTTED_MODULE_PROXY {alias.name}")
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        if isinstance(node.value, ast.Call) and call_name(node.value.func) == "object":
            self.finding(node, "LEGACY_OBJECT_SENTINEL")
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        if call_name(node.func) in {
            "chain.from_iterable",
            "itertools.chain.from_iterable",
        }:
            self.finding(node, "LEGACY_FLATTEN_CHAIN")
        self.generic_visit(node)

    def visit_ListComp(self, node: ast.ListComp) -> None:
        if len(node.generators) > 1:
            self.finding(node, "LEGACY_NESTED_LIST_COMPREHENSION")
        self.generic_visit(node)

    def visit_SetComp(self, node: ast.SetComp) -> None:
        if len(node.generators) > 1:
            self.finding(node, "LEGACY_NESTED_SET_COMPREHENSION")
        self.generic_visit(node)

    def visit_DictComp(self, node: ast.DictComp) -> None:
        if len(node.generators) > 1:
            self.finding(node, "LEGACY_NESTED_DICT_COMPREHENSION")
        self.generic_visit(node)


def main() -> int:
    findings: list[str] = []
    files = python_files()
    for path in files:
        audit = IdiomAudit(path)
        audit.visit(ast.parse(path.read_text(encoding="utf-8"), filename=str(path)))
        findings.extend(audit.findings)
    for finding in findings:
        print(finding)
    print(f"PYTHON315_IDIOM_AUDIT files={len(files)} findings={len(findings)}")
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
