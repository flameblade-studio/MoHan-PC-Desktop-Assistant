from __future__ import annotations

lazy from pathlib import Path

lazy import pytest

lazy from tools.remove_top_level_definitions import (
    class_definition_names,
    remove_definitions,
)


def test_removes_exact_decorated_top_level_definition(tmp_path: Path) -> None:
    source = tmp_path / "sample.py"
    source.write_text(
        "before = 1\n\n"
        "@decorator\n"
        "def removed() -> int:\n"
        "    return 2\n\n"
        "after = 3\n",
        encoding="utf-8",
    )

    remove_definitions(source, frozenset({"removed"}))

    assert source.read_text(encoding="utf-8") == (
        "before = 1\n\n\n"
        "after = 3\n"
    )


def test_removes_exact_class_methods_and_preserves_other_members(
    tmp_path: Path,
) -> None:
    source = tmp_path / "sample.py"
    source.write_text(
        "class Sample:\n"
        "    def keep(self) -> int:\n"
        "        return 1\n\n"
        "    @decorator\n"
        "    def first(self) -> int:\n"
        "        return 2\n\n"
        "    def second(self) -> int:\n"
        "        return 3\n",
        encoding="utf-8",
    )

    assert class_definition_names(source, "Sample") == frozenset(
        {"keep", "first", "second"}
    )
    remove_definitions(
        source,
        frozenset({"first", "second"}),
        class_name="Sample",
    )

    assert source.read_text(encoding="utf-8") == (
        "class Sample:\n"
        "    def keep(self) -> int:\n"
        "        return 1\n\n\n"
    )


def test_missing_definition_fails_without_modifying_source(tmp_path: Path) -> None:
    source = tmp_path / "sample.py"
    original = "def keep() -> None:\n    pass\n"
    source.write_text(original, encoding="utf-8")

    with pytest.raises(RuntimeError, match="definitions not found"):
        remove_definitions(source, frozenset({"missing"}))

    assert source.read_text(encoding="utf-8") == original
