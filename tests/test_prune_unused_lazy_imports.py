from __future__ import annotations

lazy import ast
lazy from pathlib import Path

lazy from tools.prune_unused_lazy_imports import prune_unused_lazy_imports

EXPECTED_PRUNED_COUNT = 2


def test_prunes_only_unused_lazy_aliases(tmp_path: Path) -> None:
    source = tmp_path / "owner.py"
    source.write_text(
        "from __future__ import annotations\n\n"
        "lazy import json, math\n"
        "lazy from pathlib import Path, PurePath\n"
        "import side_effect\n\n"
        "def encode(path: Path) -> str:\n"
        "    return json.dumps(str(path))\n",
        encoding="utf-8",
    )

    assert prune_unused_lazy_imports(source) == EXPECTED_PRUNED_COUNT

    rewritten = source.read_text(encoding="utf-8")
    ast.parse(rewritten)
    assert "lazy import json" in rewritten
    assert "math" not in rewritten
    assert "lazy from pathlib import Path" in rewritten
    assert "PurePath" not in rewritten
    assert "import side_effect" in rewritten


def test_second_prune_is_idempotent(tmp_path: Path) -> None:
    source = tmp_path / "owner.py"
    source.write_text(
        "from __future__ import annotations\n\n"
        "lazy import json\n\n"
        "def encode(value: object) -> str:\n"
        "    return json.dumps(value)\n",
        encoding="utf-8",
    )

    assert prune_unused_lazy_imports(source) == 0
    assert prune_unused_lazy_imports(source) == 0


def test_preserves_lazy_imports_published_through_dunder_all(tmp_path: Path) -> None:
    source = tmp_path / "compatibility.py"
    source.write_text(
        "from __future__ import annotations\n\n"
        "lazy from owner import PublicValue, PrivateValue\n\n"
        "__all__ = (\"PublicValue\",)\n",
        encoding="utf-8",
    )

    assert prune_unused_lazy_imports(source) == 1

    rewritten = source.read_text(encoding="utf-8")
    assert "lazy from owner import PublicValue" in rewritten
    assert "PrivateValue" not in rewritten
