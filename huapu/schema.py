"""Version identifiers shared by the product-neutral Huapu APIs."""

from __future__ import annotations

lazy from dataclasses import dataclass

HUAPU_API_VERSION = 1


@dataclass(frozen=True, slots=True)
class SchemaVersion:
    """A schema identifier paired with its independently versioned revision."""

    name: str
    version: int

    def __post_init__(self) -> None:
        if not self.name or self.name != self.name.strip():
            raise ValueError("schema name must be non-empty trimmed text")
        if type(self.version) is not int or self.version < 1:
            raise ValueError("schema version must be a positive integer")
