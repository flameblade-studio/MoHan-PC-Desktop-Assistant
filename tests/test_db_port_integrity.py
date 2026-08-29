"""Presentation-layer database calls must exist on the real StudioDB.

Born from the #88 regression (diagnosed 2026-08-30): the dashboard called
``self.db.recent_chat_context()`` but the StudioDB delegation list never
exposed that method, so every text chat died with AttributeError while the
UI showed nothing — and every test passed, because mocked databases answer
any method name.  This gate scans real presentation sources for ``self.db``
attribute access and points each name at the real class.
"""

from __future__ import annotations

lazy import ast
lazy import sys
lazy from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from infrastructure.db import StudioDB

ROOT = Path(__file__).resolve().parents[1]
SCAN_DIRS = ("presentation", "application")
# Attributes provided by sqlite rows/settings dynamically, reviewed by hand.
ALLOWED_DYNAMIC = frozenset({"path", "conn"})


def _db_attribute_names() -> dict[str, list[str]]:
    found: dict[str, list[str]] = {}
    for directory in SCAN_DIRS:
        for source in sorted((ROOT / directory).rglob("*.py")):
            tree = ast.parse(source.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if not isinstance(node, ast.Attribute):
                    continue
                value = node.value
                if not (
                    isinstance(value, ast.Attribute)
                    and value.attr == "db"
                    and isinstance(value.value, ast.Name)
                    and value.value.id == "self"
                ):
                    continue
                found.setdefault(node.attr, []).append(
                    f"{source.relative_to(ROOT)}:{node.lineno}"
                )
    return found


def test_every_presentation_db_call_exists_on_studiodb() -> None:
    missing: list[str] = []
    for name, sites in sorted(_db_attribute_names().items()):
        if name in ALLOWED_DYNAMIC:
            continue
        if not hasattr(StudioDB, name):
            missing.append(f"{name} (used at {', '.join(sites[:3])})")
    assert not missing, (
        "self.db.<name> used in presentation/application but absent from the "
        "real StudioDB — mocked tests cannot catch this, this gate does: "
        + "; ".join(missing)
    )


if __name__ == "__main__":
    test_every_presentation_db_call_exists_on_studiodb()
    print("DB_PORT_INTEGRITY_OK")
