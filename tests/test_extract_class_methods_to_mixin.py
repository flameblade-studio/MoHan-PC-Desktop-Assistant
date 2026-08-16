from __future__ import annotations

lazy import ast
lazy from pathlib import Path

lazy import pytest

lazy from tools.extract_class_methods_to_mixin import extract_methods_to_mixin

SOURCE = """from __future__ import annotations

lazy import math


class Owner:
    @staticmethod
    def retained() -> int:
        return 1

    @classmethod
    def moved(cls, value: int) -> int:
        return math.ceil(value)
"""


def test_extracts_complete_decorated_method_and_keeps_source_parseable(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source.py"
    output = tmp_path / "mixin.py"
    source.write_text(SOURCE, encoding="utf-8")

    extract_methods_to_mixin(
        source,
        output,
        class_name="Owner",
        mixin_name="OwnerMixin",
        method_names=frozenset({"moved"}),
    )

    source_tree = ast.parse(source.read_text(encoding="utf-8"))
    output_tree = ast.parse(output.read_text(encoding="utf-8"))
    source_owner = next(
        node for node in source_tree.body if isinstance(node, ast.ClassDef)
    )
    output_owner = next(
        node for node in output_tree.body if isinstance(node, ast.ClassDef)
    )
    assert [node.name for node in source_owner.body if isinstance(node, ast.FunctionDef)] == [
        "retained"
    ]
    moved = next(
        node for node in output_owner.body if isinstance(node, ast.FunctionDef)
    )
    assert moved.name == "moved"
    assert [ast.unparse(item) for item in moved.decorator_list] == ["classmethod"]


def test_missing_method_fails_before_writing_either_file(tmp_path: Path) -> None:
    source = tmp_path / "source.py"
    output = tmp_path / "mixin.py"
    source.write_text(SOURCE, encoding="utf-8")

    with pytest.raises(RuntimeError, match="Class methods not found"):
        extract_methods_to_mixin(
            source,
            output,
            class_name="Owner",
            mixin_name="OwnerMixin",
            method_names=frozenset({"missing"}),
        )

    assert source.read_text(encoding="utf-8") == SOURCE
    assert not output.exists()
