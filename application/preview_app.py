"""Pure runtime policy and command arguments for the limited Preview shell."""

from __future__ import annotations

lazy import argparse
lazy import platform
lazy import sys
lazy from dataclasses import dataclass
lazy from pathlib import Path

lazy from domain.version_info import APP_VERSION

SUPPORTED_PREVIEW_PLATFORMS = frozendict({
    "macos": "macOS",
    "linux": "Linux",
})


def normalized_preview_platform(value: str | None = None) -> str:
    """Return a supported Preview platform without enabling product services."""

    candidate = str(value or sys.platform).strip().lower()
    if candidate.startswith("darwin") or candidate in {"mac", "macos"}:
        return "macos"
    if candidate.startswith("linux"):
        return "linux"
    raise RuntimeError(f"Unsupported Preview platform: {candidate}")


@dataclass(frozen=True, slots=True)
class PreviewRuntime:
    """Immutable display metadata for the deliberately restricted Preview."""

    platform_id: str
    platform_name: str
    version: str
    architecture: str
    enabled_product_capabilities: frozenset[str] = frozenset()

    @classmethod
    def current(cls, platform_id: str | None = None) -> PreviewRuntime:
        normalized = normalized_preview_platform(platform_id)
        return cls(
            platform_id=normalized,
            platform_name=SUPPORTED_PREVIEW_PLATFORMS[normalized],
            version=APP_VERSION,
            architecture=platform.machine() or "unknown",
        )


def validate_preview_runtime(runtime: PreviewRuntime) -> None:
    """Fail closed if a restricted Preview exposes an unverified capability."""

    expected_name = SUPPORTED_PREVIEW_PLATFORMS.get(runtime.platform_id)
    if expected_name is None:
        raise RuntimeError(f"Unsupported Preview platform: {runtime.platform_id}")
    if runtime.platform_name != expected_name:
        raise RuntimeError(
            "Preview platform identity mismatch: "
            f"{runtime.platform_id} is not {runtime.platform_name}"
        )
    if runtime.enabled_product_capabilities:
        enabled = ", ".join(sorted(runtime.enabled_product_capabilities))
        raise RuntimeError(
            "Preview platform unexpectedly exposes unverified capabilities: " + enabled
        )
    if not runtime.version.strip() or not runtime.architecture.strip():
        raise RuntimeError("Preview runtime metadata is incomplete")


def parse_preview_arguments(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument("--preview-smoke-output", type=Path)
    parser.add_argument("--jit-status-output", type=Path)
    parser.add_argument(
        "--preview-platform",
        choices=tuple(SUPPORTED_PREVIEW_PLATFORMS),
    )
    parser.add_argument("--preview-expected-version")
    return parser.parse_known_args(argv)[0]


__all__ = (
    "SUPPORTED_PREVIEW_PLATFORMS",
    "PreviewRuntime",
    "normalized_preview_platform",
    "parse_preview_arguments",
    "validate_preview_runtime",
)
