from __future__ import annotations

lazy import ast
lazy import subprocess
lazy import sys
lazy import unittest
lazy from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

lazy from domain.companion_animation_contract import (
    EXPRESSION_SPEECH_FRAMES,
    EXPRESSION_SPEECH_MOUTH_RECTS,
    GESTURE_SPEECH_ASSETS,
    GESTURE_SPEECH_EXPRESSIONS,
    GESTURE_SPEECH_FRAMES,
    GESTURE_SPEECH_MOUTH_RECTS,
)

CONTRACT_MODULE = "domain.companion_animation_contract"
CONSUMER_MODULES = (
    "presentation.companion_visual_dynamics",
    "presentation.companion_face_animation",
    "presentation.companion_speech_runtime",
)
ANIMATION_MODULES = (CONTRACT_MODULE, *CONSUMER_MODULES)
ANIMATION_CONSTANT_COUNT = 38
GESTURE_SPEECH_ASSET_COUNT = 12
ANIMATION_CONSTANTS = frozenset({
    "ATTENTION_FRAME_INTERVAL_MS",
    "BLUSH_PRESERVING_BLINK_EXPRESSIONS",
    "CHARACTER_BASE_Y",
    "CHARACTER_CANVAS_WIDTH",
    "CHARACTER_IMAGE_SIZE",
    "CHARACTER_SCALE_DEFAULT",
    "CHARACTER_SCALE_MAX",
    "CHARACTER_SCALE_MIN",
    "CHEEK_SPEECH_CLOSED_EXPRESSION",
    "EYES_CLOSED_EXPRESSIONS",
    "EXPRESSION_BLINK_ASSETS",
    "EXPRESSION_BLINK_FRAMES",
    "EXPRESSION_DERIVED_VISEME_FRAMES",
    "EXPRESSION_EYE_OFFSETS",
    "EXPRESSION_FACE_OFFSETS",
    "EXPRESSION_IMAGE_ASSETS",
    "EXPRESSION_MOUTH_OFFSETS",
    "EXPRESSION_POSES",
    "EXPRESSION_SPEECH_ASSETS",
    "EXPRESSION_SPEECH_EXPRESSIONS",
    "EXPRESSION_SPEECH_FRAMES",
    "EXPRESSION_SPEECH_MOUTH_RECTS",
    "EXPRESSION_VISEME_FRAMES",
    "GESTURE_SPEECH_ASSETS",
    "GESTURE_SPEECH_EXPRESSIONS",
    "GESTURE_SPEECH_FRAMES",
    "GESTURE_SPEECH_MOUTH_RECTS",
    "HAPPY_SPEECH_CLOSED_EXPRESSION",
    "IDLE_FRAME_INTERVAL_MS",
    "MOTION_FRAME_INTERVAL_MS",
    "MOUTH_CLOSE_DEADLINE_MS",
    "NEUTRAL_VISEME_ASSET_STEMS",
    "NEW_EXPRESSION_ASSETS",
    "PHYSICS_FRAME_INTERVAL_MS",
    "PHYSICS_POSE_SUFFIXES",
    "PHYSICS_SPEECH_FRAME_PREFIXES",
    "SPEAKING_BLINK_PREFIXES",
    "SPEECH_MOTION_RELEASE_LIMIT",
})


def module_path(module: str) -> Path:
    return PROJECT_ROOT.joinpath(*module.split(".")).with_suffix(".py")


def module_tree(module: str) -> ast.Module:
    path = module_path(module)
    assert path.is_file(), f"missing animation module: {path.name}"
    return ast.parse(
        path.read_text(encoding="utf-8-sig"),
        filename=str(path),
    )


def assigned_names(tree: ast.Module) -> set[str]:
    names: set[str] = set()
    for node in tree.body:
        targets: list[ast.expr] = []
        if isinstance(node, ast.Assign):
            targets.extend(node.targets)
        elif isinstance(node, ast.AnnAssign):
            targets.append(node.target)
        for target in targets:
            if isinstance(target, ast.Name):
                names.add(target.id)
    return names


def contract_imports(tree: ast.Module) -> set[str]:
    return {
        *(
            alias.name
            for alias in node.names
        )
        for node in tree.body
        if isinstance(node, ast.ImportFrom)
        and node.module == CONTRACT_MODULE
    }


def imported_modules(tree: ast.Module) -> set[str]:
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
    return imports


def test_contract_is_the_unique_owner_of_all_35_animation_constants() -> None:
    assert len(ANIMATION_CONSTANTS) == ANIMATION_CONSTANT_COUNT
    assert assigned_names(module_tree(CONTRACT_MODULE)) & ANIMATION_CONSTANTS == (
        ANIMATION_CONSTANTS
    )

    for module in CONSUMER_MODULES:
        tree = module_tree(module)
        assert not assigned_names(tree) & ANIMATION_CONSTANTS
        assert contract_imports(tree) <= ANIMATION_CONSTANTS


def test_gesture_speech_contract_preserves_the_four_expression_behavior() -> None:
    expected_expressions = frozenset({
        "mock_scold",
        "mock_hit_front",
        "exasperated_front",
        "eureka_front",
    })
    expected_rects = {
        "mock_scold": (202, 196, 53, 44),
        "mock_hit_front": (201, 190, 56, 50),
        "exasperated_front": (199, 201, 58, 47),
        "eureka_front": (197, 190, 58, 48),
    }

    assert expected_expressions == GESTURE_SPEECH_EXPRESSIONS
    assert frozenset(GESTURE_SPEECH_FRAMES) == expected_expressions
    assert frozenset(GESTURE_SPEECH_MOUTH_RECTS) == expected_expressions

    expected_assets: set[str] = set()
    for expression in expected_expressions:
        expected_frames = {
            frame: f"{expression}_speech_{frame}"
            for frame in ("mid", "open", "round")
        }
        assert dict(GESTURE_SPEECH_FRAMES[expression]) == expected_frames
        assert (
            GESTURE_SPEECH_FRAMES[expression]
            is EXPRESSION_SPEECH_FRAMES[expression]
        )
        expected_assets.update(expected_frames.values())
        assert GESTURE_SPEECH_MOUTH_RECTS[expression].getRect() == (
            expected_rects[expression]
        )
        assert (
            GESTURE_SPEECH_MOUTH_RECTS[expression]
            is EXPRESSION_SPEECH_MOUTH_RECTS[expression]
        )

    assert len(GESTURE_SPEECH_ASSETS) == GESTURE_SPEECH_ASSET_COUNT
    assert set(GESTURE_SPEECH_ASSETS) == expected_assets
    assert tuple(
        asset
        for frames in GESTURE_SPEECH_FRAMES.values()
        for asset in frames.values()
    ) == GESTURE_SPEECH_ASSETS


def test_animation_modules_never_import_app() -> None:
    for module in ANIMATION_MODULES:
        imports = imported_modules(module_tree(module))
        assert not any(
            imported == "app" or imported.startswith("app.")
            for imported in imports
        ), module


def test_physics_pose_suffixes_preserve_cheek_lean_front_behavior() -> None:
    tree = module_tree(CONTRACT_MODULE)
    assignment = next(
        node
        for node in tree.body
        if isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Name)
            and target.id == "PHYSICS_POSE_SUFFIXES"
            for target in node.targets
        )
    )

    assert ast.literal_eval(assignment.value) == (
        ("", "cheek"),
        ("_lean", "lean"),
        ("_front", "front"),
    )


def test_module_import_does_not_load_app() -> None:
    for module in ANIMATION_MODULES:
        script = (
            "import importlib, sys\n"
            "assert 'app' not in sys.modules\n"
            f"importlib.import_module({module!r})\n"
            "assert 'app' not in sys.modules\n"
        )
        completed = subprocess.run(
            [sys.executable, "-c", script],
            cwd=PROJECT_ROOT,
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert completed.returncode == 0, (
            f"standalone import failed for {module}: {completed.stderr}"
        )


class CompanionAnimationContractTests(unittest.TestCase):
    def test_contract_is_unique_owner(self) -> None:
        test_contract_is_the_unique_owner_of_all_35_animation_constants()

    def test_gesture_speech_behavior(self) -> None:
        test_gesture_speech_contract_preserves_the_four_expression_behavior()

    def test_modules_do_not_import_app(self) -> None:
        test_animation_modules_never_import_app()

    def test_physics_pose_suffixes(self) -> None:
        test_physics_pose_suffixes_preserve_cheek_lean_front_behavior()

    def test_standalone_imports(self) -> None:
        test_module_import_does_not_load_app()


if __name__ == "__main__":
    unittest.main()
