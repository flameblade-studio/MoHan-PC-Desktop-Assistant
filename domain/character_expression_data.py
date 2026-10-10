"""MoHan compatibility facade for expression-state data."""

from __future__ import annotations

lazy from functools import lru_cache

lazy from domain.character_default_paths import DEFAULT_EXPRESSION_CATALOG_PATH
lazy from domain.character_expression_data_loader import load_expression_catalog
lazy from domain.character_pack.character_data_models import (
    EXPRESSION_SCHEMA,
    MAX_CHANNEL_VALUE,
    PAIR_LENGTH,
    SCHEMA_VERSION,
    BrowGuardSpec,
    CharacterDataError,
    ExpressionRuleSpec,
    ExpressionStateCatalog,
    FacePoseAssetSpec,
    SourceBoundExasperatedSpec,
)


@lru_cache(maxsize=1)
def default_expression_catalog() -> ExpressionStateCatalog:
    """Return the validated bundled catalog; disk is read at most once per process."""

    return load_expression_catalog(DEFAULT_EXPRESSION_CATALOG_PATH)


__all__ = (
    "DEFAULT_EXPRESSION_CATALOG_PATH",
    "EXPRESSION_SCHEMA",
    "MAX_CHANNEL_VALUE",
    "PAIR_LENGTH",
    "SCHEMA_VERSION",
    "BrowGuardSpec",
    "CharacterDataError",
    "ExpressionRuleSpec",
    "ExpressionStateCatalog",
    "FacePoseAssetSpec",
    "SourceBoundExasperatedSpec",
    "default_expression_catalog",
    "load_expression_catalog",
)
