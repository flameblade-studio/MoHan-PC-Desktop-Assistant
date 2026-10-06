"""Every literal ui_text key must exist in every supported language.

Presentation looks up _t(key, fallback), translate(key, fallback), and
ui_text(language, key, fallback). A Traditional Chinese fallback can conceal
an absent translation. This gate AST-scans presentation/**/*.py and verifies
that each collected key appears in every language table.
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
lazy from presentation.auxiliary_ui_localization import TRANSLATIONS
lazy from presentation.flagship_ui_localization import FLAGSHIP_TRANSLATIONS

PRESENTATION = ROOT / "presentation"

# ``self._t(key, fallback)`` / ``translate(key, fallback)`` carry the key as
# the first positional argument; ``ui_text(language, key, fallback)`` carries
# it as the second.  Flagship ``_t(source)`` and AuxiliaryText ``_t(key)``
# take a single positional argument and are excluded by the minimum below.
KEY_FALLBACK_MIN_ARGS = 2
UI_TEXT_KEY_INDEX = 1
PRODUCT_NAME = "MoHan Desktop Assistant"
NAME_BY_LANGUAGE = frozendict({
    "zh-TW": "墨寒",
    "zh-CN": "墨寒",
    "en": "MoHan",
    "ja-JP": "墨寒",
})
# About text must retain the immutable product name. User-owned assistant,
# wake-word, window-title, speech, and conversation values are runtime data,
# not fixed catalog text, so this catalog gate intentionally never rewrites them.
FIXED_NAME_EXCEPTIONS = frozendict({
    ("ui.zh-TW", "about_body"): (PRODUCT_NAME,),
    ("ui.zh-CN", "about_body"): (PRODUCT_NAME,),
    ("ui.ja-JP", "about_body"): (PRODUCT_NAME,),
})

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


def _collect_traditional_fixed_text() -> tuple[tuple[str, str], ...]:
    """Collect literal Traditional Chinese fallbacks from ui_text-backed calls."""

    entries: list[tuple[str, str]] = []
    for path in sorted(PRESENTATION.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            key_argument = _key_argument(node)
            if key_argument is None or not isinstance(key_argument, ast.Constant):
                continue
            if not isinstance(key_argument.value, str):
                continue
            function = node.func
            name = (
                function.attr
                if isinstance(function, ast.Attribute)
                else function.id
                if isinstance(function, ast.Name)
                else ""
            )
            fallback_index = 2 if name == "ui_text" else 1
            if len(node.args) <= fallback_index:
                continue
            fallback = node.args[fallback_index]
            if isinstance(fallback, ast.Constant) and isinstance(fallback.value, str):
                entries.append((key_argument.value, fallback.value))
    return tuple(entries)


def _catalogs_by_language() -> tuple[
    tuple[str, str, tuple[tuple[str, str], ...]], ...
]:
    flagship = tuple(FLAGSHIP_TRANSLATIONS.items())
    return (
        ("ui.zh-TW", "zh-TW", _collect_traditional_fixed_text()),
        ("ui.zh-CN", "zh-CN", tuple(_SIMPLIFIED_CHINESE.items())),
        ("ui.en", "en", tuple(_ENGLISH.items())),
        ("ui.ja-JP", "ja-JP", tuple(_JAPANESE.items())),
        ("flagship.zh-TW", "zh-TW", tuple((source, source) for source, _row in flagship)),
        ("flagship.zh-CN", "zh-CN", tuple((source, row[0]) for source, row in flagship)),
        ("flagship.en", "en", tuple((source, row[1]) for source, row in flagship)),
        ("flagship.ja-JP", "ja-JP", tuple((source, row[2]) for source, row in flagship)),
        (
            "auxiliary.zh-TW",
            "zh-TW",
            tuple((key.value, value) for key, value in TRANSLATIONS["zh-TW"].items()),
        ),
        (
            "auxiliary.zh-CN",
            "zh-CN",
            tuple((key.value, value) for key, value in TRANSLATIONS["zh-CN"].items()),
        ),
        (
            "auxiliary.en",
            "en",
            tuple((key.value, value) for key, value in TRANSLATIONS["en"].items()),
        ),
        (
            "auxiliary.ja-JP",
            "ja-JP",
            tuple((key.value, value) for key, value in TRANSLATIONS["ja-JP"].items()),
        ),
    )


def test_every_used_key_is_translated_in_all_languages() -> None:
    used_keys, _dynamic = _collect_used_keys()
    assert used_keys, 'AST scan requires UI text keys; inspect the scanner configuration'
    for name, table in (
        ("en", _ENGLISH),
        ("zh-CN", _SIMPLIFIED_CHINESE),
        ("ja-JP", _JAPANESE),
    ):
        missing = sorted(used_keys - frozenset(table))
        assert not missing, (
            f'provide ui_text keys in the {name} table (users of that language would silently see the Traditional Chinese fallback): {missing}'
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
        f'Align DYNAMIC_KEY_ALLOWLIST with existing code entries: {stale}'
    )


def test_fixed_ui_character_name_matches_each_catalog_language() -> None:
    issues: list[str] = []
    for catalog, language, entries in _catalogs_by_language():
        disallowed = "墨寒" if NAME_BY_LANGUAGE[language] == "MoHan" else "MoHan"
        for key, value in entries:
            checked = value
            for exception in FIXED_NAME_EXCEPTIONS.get((catalog, key), ()):
                checked = checked.replace(exception, "")
            if disallowed in checked:
                issues.append(f"{catalog}[{key!r}] contains {disallowed!r}: {value!r}")
    assert not issues, "Fixed UI character names must follow the interface language:\n" + "\n".join(issues)
