from __future__ import annotations

lazy import ast
lazy import importlib
lazy import os
lazy from pathlib import Path

lazy from tools.check_layered_imports import PHYSICALLY_LAYERED_ROOTS

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MIGRATED_LAYERS = frozenset({"application", "domain"})


def _owner_modules() -> dict[str, str]:
    return {
        **{
            path.stem: f"{layer}.{path.stem}"
            for path in (PROJECT_ROOT / layer).glob("*.py")
            if path.name != "__init__.py"
        }
        for layer in MIGRATED_LAYERS
    }


def test_domain_and_application_have_physical_owners_and_no_root_detours() -> None:
    owners = _owner_modules()
    required = {
        module
        for module, layer in PHYSICALLY_LAYERED_ROOTS.items()
        if layer in MIGRATED_LAYERS
    }
    assert required <= owners.keys()
    assert (PROJECT_ROOT / "application" / "app.py").is_file()

    detours: list[str] = []
    for layer in MIGRATED_LAYERS:
        for path in sorted((PROJECT_ROOT / layer).glob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
            for node in ast.walk(tree):
                if (
                    isinstance(node, ast.ImportFrom)
                    and node.level == 0
                    and node.module in owners
                ):
                    detours.append(f"{path.name}:{node.lineno}:{node.module}")
                if isinstance(node, ast.Import):
                    detours.extend(
                        f"{path.name}:{node.lineno}:{alias.name}"
                        for alias in node.names
                        if alias.name in owners
                    )
    assert detours == []


def test_root_app_remains_the_thin_composition_entrypoint() -> None:
    source = (PROJECT_ROOT / "app.py").read_text(encoding="utf-8")
    tree = ast.parse(source, filename="app.py")
    assert len(source.splitlines()) <= 50
    assert any(
        isinstance(node, ast.ImportFrom)
        and node.module == "application.application_bootstrap"
        and any(alias.name == "run_application" for alias in node.names)
        for node in tree.body
    )


def test_compatibility_aliases_preserve_module_identity() -> None:
    examples = {
        "language_support": "domain.language_support",
        "local_visual_intelligence": "application.local_visual_intelligence",
        "vision_runtime": "application.vision_runtime",
    }
    for facade_name, owner_name in examples.items():
        assert importlib.import_module(facade_name) is importlib.import_module(owner_name)


def test_silence_gesture_detector_is_a_callable_owner_export() -> None:
    intent = importlib.import_module("domain.gesture_intent")
    visual = importlib.import_module("application.local_visual_intelligence")
    detector = visual.LocalVisualIntelligencePipeline()._new_gesture_detector()

    assert callable(intent.SilenceGestureDetector)
    assert isinstance(detector, intent.SilenceGestureDetector)
