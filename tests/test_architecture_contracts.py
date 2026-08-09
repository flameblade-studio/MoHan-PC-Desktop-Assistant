from __future__ import annotations

lazy import ast
lazy import os
lazy import sys
lazy from pathlib import Path
lazy from tempfile import TemporaryDirectory

os.environ["QT_QPA_PLATFORM"] = "offscreen"
PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))

lazy from PySide6.QtWidgets import QApplication, QLabel, QTabWidget

lazy from feature_registry import DashboardFeatureRegistry


def local_import_graph() -> dict[str, set[str]]:
    modules = {
        path.stem: path
        for path in PROJECT.glob("*.py")
        if path.stem != "__init__"
    }
    graph = {name: set() for name in modules}
    for name, path in modules.items():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    root = alias.name.split(".", 1)[0]
                    if root in modules:
                        graph[name].add(root)
            elif isinstance(node, ast.ImportFrom) and node.module:
                root = node.module.split(".", 1)[0]
                if root in modules:
                    graph[name].add(root)
    return graph


def assert_acyclic(graph: dict[str, set[str]]) -> None:
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str, trail: tuple[str, ...]) -> None:
        if node in visiting:
            raise AssertionError(
                "local import cycle: " + " -> ".join(trail + (node,))
            )
        if node in visited:
            return
        visiting.add(node)
        for dependency in sorted(graph[node]):
            visit(dependency, trail + (node,))
        visiting.remove(node)
        visited.add(node)

    for module in sorted(graph):
        visit(module, ())


def companion_private_dashboard_accesses() -> list[str]:
    tree = ast.parse(
        (PROJECT / "app.py").read_text(encoding="utf-8"),
        filename="app.py",
    )
    companion = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef)
        and node.name == "CompanionWindow"
    )
    violations: list[str] = []
    for node in ast.walk(companion):
        if not isinstance(node, ast.Attribute):
            continue
        owner = node.value
        if (
            node.attr.startswith("_")
            and isinstance(owner, ast.Attribute)
            and owner.attr == "dashboard"
            and isinstance(owner.value, ast.Name)
            and owner.value.id == "self"
        ):
            violations.append(node.attr)
    return sorted(set(violations))


def run() -> None:
    graph = local_import_graph()
    assert_acyclic(graph)

    core_modules = {
        "ai_client",
        "backup_manager",
        "cloud_connectors",
        "command_parser",
        "contracts",
        "db",
        "expression_system",
        "flagship_core",
        "home_assistant",
        "lip_sync",
        "platform_contracts",
        "platform_linux",
        "platform_macos",
        "platform_services",
        "platform_windows",
        "profile_transfer",
        "realtime_voice",
        "remote_control",
        "secret_store",
        "service_container",
        "speech",
        "text_normalizer",
        "windows_tools",
        "workflow_engine",
    }
    forbidden_upward = {"app", "flagship_ui", "profile_transfer_ui"}
    for module in core_modules:
        assert not (
            graph.get(module, set()) & forbidden_upward
        ), f"{module} imports a UI/composition module"

    assert companion_private_dashboard_accesses() == []
    assert "profile_transfer" not in graph["app"]
    assert "profile_transfer_ui" in graph["app"]
    assert "service_container" in graph["app"]
    assert "app" not in graph["service_container"]

    with TemporaryDirectory() as _temp:
        app = QApplication.instance() or QApplication([])
        tabs = QTabWidget()
        registry = DashboardFeatureRegistry()
        registry.register("alpha", "Alpha", lambda: QLabel("A"))
        registry.register("beta", "Beta", lambda: QLabel("B"))
        registry.mount(tabs)
        assert tabs.count() == 2
        assert tabs.widget(0).property("mohanFeatureId") == "alpha"
        assert tabs.widget(1).property("mohanFeatureId") == "beta"
        try:
            registry.register("alpha", "Again", lambda: QLabel("X"))
        except ValueError:
            pass
        else:
            raise AssertionError("duplicate feature IDs must be rejected")
        tabs.close()
        app.processEvents()
    print("ARCHITECTURE_CONTRACTS_OK")


if __name__ == "__main__":
    run()
