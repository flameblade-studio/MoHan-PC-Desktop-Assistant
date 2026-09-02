"""Structural gate: every literal ui_text key must exist in all languages.

The dashboard/presentation layer looks strings up with ``_t(key, fallback)``,
``translate(key, fallback)`` or ``ui_text(language, key, fallback)``; the
Traditional Chinese fallback silently masks a missing table entry, so English,
Simplified Chinese, and Japanese users would see untranslated text without any
test failing.  This module AST-scans ``presentation/**/*.py`` for those call
shapes and asserts that the collected key set is a subset of every language
table, closing the regression class instead of chasing single keys.
"""

from __future__ import annotations

lazy import ast
lazy import sys
lazy from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

lazy from presentation.ui_localization import (
    _ENGLISH,
    _JAPANESE,
    _SIMPLIFIED_CHINESE,
)

PRESENTATION = ROOT / "presentation"

# ``self._t(key, fallback)`` / ``translate(key, fallback)`` carry the key as
# the first positional argument; ``ui_text(language, key, fallback)`` carries
# it as the second.  Flagship ``_t(source)`` and AuxiliaryText ``_t(key)``
# take a single positional argument and are excluded by the minimum below.
KEY_FALLBACK_MIN_ARGS = 2
UI_TEXT_KEY_INDEX = 1

# Reviewed call sites whose key argument is a runtime expression.  Every
# entry names one (file, key expression) pair that resolves to keys already
# covered by literal call sites or by dedicated tests.  A new dynamic key
# must either become a literal or be reviewed and added here.
DYNAMIC_KEY_ALLOWLIST = frozenset({
    ("presentation/companion_speech_runtime.py", "message_key"),
    ("presentation/dashboard_dialogs.py", "category_key"),
    ("presentation/dashboard_platforms.py", "key"),
    ("presentation/dashboard_settings.py", "key"),
    ("presentation/dashboard_shell.py", "key"),
    ("presentation/dashboard_shell.py", "translation_key"),
    ("presentation/dashboard_today_memory.py", "key"),
    ("presentation/dashboard_wardrobe_preview.py", "key"),
    ("presentation/dashboard_voice_runtime.py", "policy.error_key"),
    ("presentation/dashboard_voice_runtime.py", "policy.saved_key"),
    ("presentation/dashboard_voice_runtime.py", "policy.title_key"),
    ("presentation/first_run_wizard.py", "key"),
    ("presentation/theme_pack_ui.py", "key"),
    ("presentation/theme_pack_ui.py", "source_key"),
})


def _literal_keys(node: ast.expr) -> list[str]:
    """Return the string keys a key-argument expression can evaluate to."""

    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return [node.value]
    if isinstance(node, ast.IfExp):
        return _literal_keys(node.body) + _literal_keys(node.orelse)
    return []


def _key_argument(node: ast.Call) -> ast.expr | None:
    """Return the key argument of a ui_text-backed call, if any."""

    func = node.func
    if len(node.args) < KEY_FALLBACK_MIN_ARGS:
        return None
    if isinstance(func, ast.Attribute) and func.attr == "_t":
        return node.args[0]
    if isinstance(func, ast.Name) and func.id in {"_t", "translate"}:
        return node.args[0]
    if isinstance(func, ast.Name) and func.id == "ui_text":
        return node.args[UI_TEXT_KEY_INDEX]
    return None


def _collect_used_keys() -> tuple[frozenset[str], frozenset[tuple[str, str]]]:
    keys: set[str] = set()
    dynamic: set[tuple[str, str]] = set()
    for path in sorted(PRESENTATION.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        relative = path.relative_to(ROOT).as_posix()
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            key_argument = _key_argument(node)
            if key_argument is None:
                continue
            found = _literal_keys(key_argument)
            if found:
                keys.update(found)
            else:
                dynamic.add((relative, ast.unparse(key_argument)))
    return frozenset(keys), frozenset(dynamic)


def test_every_used_key_is_translated_in_all_languages() -> None:
    used_keys, _dynamic = _collect_used_keys()
    assert used_keys, "AST scan found no ui_text keys; the scanner is broken"
    for name, table in (
        ("en", _ENGLISH),
        ("zh-CN", _SIMPLIFIED_CHINESE),
        ("ja-JP", _JAPANESE),
    ):
        missing = sorted(used_keys - frozenset(table))
        assert not missing, (
            f"ui_text keys missing from the {name} table (users of that "
            f"language would silently see the Traditional Chinese fallback): "
            f"{missing}"
        )


def test_dynamic_key_call_sites_are_reviewed() -> None:
    _used_keys, dynamic = _collect_used_keys()
    unreviewed = sorted(dynamic - DYNAMIC_KEY_ALLOWLIST)
    assert not unreviewed, (
        "New dynamic ui_text key expressions found; use a literal key or "
        f"review and extend DYNAMIC_KEY_ALLOWLIST: {unreviewed}"
    )
    stale = sorted(DYNAMIC_KEY_ALLOWLIST - dynamic)
    assert not stale, (
        f"DYNAMIC_KEY_ALLOWLIST entries no longer exist in the code: {stale}"
    )
