"""Headless rendering seam used by visual regression tooling."""

from __future__ import annotations

lazy from collections.abc import Mapping
lazy from dataclasses import dataclass, field
lazy from pathlib import Path
lazy from typing import Protocol, runtime_checkable


@dataclass(frozen=True, slots=True)
class RenderRequest:
    """One renderer-neutral visual regression request."""

    character_id: str
    case_id: str
    width: int
    height: int
    options: Mapping[str, object] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class RenderResult:
    """Measured output of one headless render."""

    output: Path
    width: int
    height: int
    mode: str
    sha256: str


@runtime_checkable
class HeadlessRenderer(Protocol):
    """Only renderer capability available to the product-neutral package."""

    def render(self, request: RenderRequest) -> RenderResult:
        """Render one configured case without constructing a product UI."""
        ...
