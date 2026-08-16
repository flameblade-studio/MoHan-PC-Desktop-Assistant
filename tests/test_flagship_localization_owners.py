from __future__ import annotations

lazy import ast
lazy import importlib
lazy from pathlib import Path
lazy from string import Formatter

lazy import pytest

lazy from flagship_ui_localization import (
    FLAGSHIP_TRANSLATIONS,
    FlagshipTranslator,
    validate_flagship_translations,
)
lazy from presentation.flagship.localization_catalog import (
    merge_translation_catalogs,
)
lazy from presentation.flagship.localization_cloud_home import (
    CLOUD_HOME_TRANSLATIONS,
)
lazy from presentation.flagship.localization_interaction import (
    INTERACTION_TRANSLATIONS,
)
lazy from presentation.flagship.localization_remote_vision import (
    REMOTE_VISION_TRANSLATIONS,
)
lazy from presentation.flagship.localization_security_audit import (
    SECURITY_AUDIT_TRANSLATIONS,
)
lazy from presentation.flagship.localization_workflows import (
    WORKFLOW_TRANSLATIONS,
)

ROOT = Path(__file__).resolve().parents[1]
MAX_LOCALIZATION_OWNER_LINES = 1_200
CATALOGS = (
    INTERACTION_TRANSLATIONS,
    WORKFLOW_TRANSLATIONS,
    CLOUD_HOME_TRANSLATIONS,
    REMOTE_VISION_TRANSLATIONS,
    SECURITY_AUDIT_TRANSLATIONS,
)


def _format_fields(template: str) -> frozenset[str]:
    return frozenset(
        field_name
        for _literal, field_name, _format_spec, _conversion in Formatter().parse(
            template
        )
        if field_name is not None
    )


def test_localization_owners_are_bounded_and_single_purpose() -> None:
    owner = ROOT / "presentation" / "flagship_ui_localization.py"
    modules = (owner, *(ROOT / "presentation" / "flagship").glob("localization_*.py"))

    oversized = {
        path.relative_to(ROOT).as_posix(): len(
            path.read_text(encoding="utf-8").splitlines()
        )
        for path in modules
        if len(path.read_text(encoding="utf-8").splitlines())
        > MAX_LOCALIZATION_OWNER_LINES
    }

    assert oversized == {}


def test_internal_localization_owner_imports_are_lazy() -> None:
    owner = ROOT / "presentation" / "flagship_ui_localization.py"
    modules = (owner, *(ROOT / "presentation" / "flagship").glob("localization_*.py"))
    eager_imports: list[str] = []

    for path in modules:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in tree.body:
            if isinstance(node, ast.ImportFrom) and node.module == "__future__":
                continue
            if isinstance(node, (ast.Import, ast.ImportFrom)) and not getattr(
                node,
                "is_lazy",
                0,
            ):
                eager_imports.append(f"{path.relative_to(ROOT).as_posix()}:{node.lineno}")

    assert eager_imports == []


def test_responsibility_catalogs_are_disjoint_and_preserve_public_order() -> None:
    seen: set[str] = set()
    ordered_sources: list[str] = []

    for catalog in CATALOGS:
        assert catalog
        assert not seen.intersection(catalog)
        seen.update(catalog)
        ordered_sources.extend(catalog)

    assert tuple(FLAGSHIP_TRANSLATIONS) == tuple(ordered_sources)
    assert len(FLAGSHIP_TRANSLATIONS) == sum(len(catalog) for catalog in CATALOGS)


def test_catalog_merge_rejects_duplicate_sources() -> None:
    duplicate = "重複來源"

    with pytest.raises(ValueError, match="Duplicate flagship translation source"):
        merge_translation_catalogs(
            {duplicate: ("简体中文", "English", "日本語")},
            {duplicate: ("重复", "Duplicate", "重複")},
        )


def test_every_language_preserves_runtime_format_fields() -> None:
    validate_flagship_translations()

    for source, translations in FLAGSHIP_TRANSLATIONS.items():
        source_fields = _format_fields(source)
        assert len(translations) == 3
        assert all(value.strip() for value in translations)
        assert all(_format_fields(value) == source_fields for value in translations)


def test_compatibility_facade_reexports_exact_owner_objects() -> None:
    facade = importlib.import_module("flagship_ui_localization")
    owner = importlib.import_module("presentation.flagship_ui_localization")

    assert facade.FLAGSHIP_TRANSLATIONS is owner.FLAGSHIP_TRANSLATIONS
    assert facade.FlagshipTranslator is owner.FlagshipTranslator
    assert (
        facade.validate_flagship_translations
        is owner.validate_flagship_translations
    )
    assert FlagshipTranslator is owner.FlagshipTranslator
