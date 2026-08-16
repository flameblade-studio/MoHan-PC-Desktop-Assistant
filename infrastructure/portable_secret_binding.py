from __future__ import annotations

lazy from collections.abc import Mapping
lazy from dataclasses import dataclass, field
lazy from pathlib import Path
lazy from types import MappingProxyType
lazy from typing import Protocol

lazy from domain.contracts import SecretStoreFactoryPort, SecretStorePort
lazy from infrastructure.portable_secrets import (
    SECRET_IDS,
    PortableSecretsPayload,
    apply_sensitive_payload,
    collect_sensitive_payload,
)


class PortableSecretBindingError(RuntimeError):
    """A fixed-detail error for invalid secret-store composition."""


_BOUNDARY_ERRORS = (Exception,)


class DashboardSecretBoundaries(Protocol):
    """Secret boundaries exposed by DashboardDependencies without UI imports."""

    secret_store: SecretStorePort
    azure_secret_store: SecretStorePort | None
    azure_hd_secret_store: SecretStorePort | None
    secret_store_factory: SecretStoreFactoryPort | None


@dataclass(frozen=True, slots=True)
class PortableSecretBinding:
    """Complete typed bridge between composition roots and portable secrets."""

    _stores: Mapping[str, SecretStorePort] = field(repr=False)

    def collect(self) -> PortableSecretsPayload:
        return collect_sensitive_payload(self._stores)

    def apply(self, payload: Mapping[str, object]) -> None:
        apply_sensitive_payload(payload, self._stores)

    def store_ids(self) -> frozenset[str]:
        return frozenset(self._stores)


def bind_portable_secret_stores(
    stores: Mapping[str, SecretStorePort],
) -> PortableSecretBinding:
    """Bind one distinct store for every supported portable secret ID."""

    if not isinstance(stores, Mapping) or set(stores) != SECRET_IDS:
        raise PortableSecretBindingError(
            "Portable secret stores must provide the complete supported mapping."
        )
    normalized: dict[str, SecretStorePort] = {}
    identities: set[int] = set()
    for secret_id in sorted(SECRET_IDS):
        store = stores[secret_id]
        if not _is_secret_store(store):
            raise PortableSecretBindingError("A portable secret store is invalid.")
        identity = id(store)
        if identity in identities:
            raise PortableSecretBindingError(
                "Portable secret stores must not be shared between IDs."
            )
        identities.add(identity)
        normalized[secret_id] = store
    return PortableSecretBinding(MappingProxyType(normalized))


def bind_dashboard_portable_secrets(
    dependencies: DashboardSecretBoundaries,
    data_path: Path,
) -> PortableSecretBinding:
    """Create every portable-secret binding from composition boundaries."""

    factory = dependencies.secret_store_factory
    if (
        dependencies.azure_secret_store is None
        or dependencies.azure_hd_secret_store is None
        or factory is None
    ):
        raise PortableSecretBindingError(
            "Dashboard secret-store boundaries are incomplete."
        )
    root = Path(data_path)
    generated = {
        "home_assistant": _create_store(
            factory,
            root / "home-assistant-token.dpapi",
            "MoHan Home Assistant token",
        ),
        "oauth_google": _create_store(
            factory,
            root / "oauth-google.dpapi",
            "MoHan google OAuth token",
        ),
        "oauth_microsoft": _create_store(
            factory,
            root / "oauth-microsoft.dpapi",
            "MoHan microsoft OAuth token",
        ),
        "oauth_github": _create_store(
            factory,
            root / "oauth-github.dpapi",
            "MoHan github OAuth token",
        ),
        "face_identities": _create_store(
            factory,
            root / "face-identities.dpapi",
            "MoHan local face identity templates",
        ),
        "gesture_templates": _create_store(
            factory,
            root / "gesture-templates.dpapi",
            "MoHan local gesture skeleton templates",
        ),
    }
    return bind_portable_secret_stores(
        {
            "openai": dependencies.secret_store,
            "azure_speech": dependencies.azure_secret_store,
            "azure_dragon_hd": dependencies.azure_hd_secret_store,
            **generated,
        }
    )


def _create_store(
    factory: SecretStoreFactoryPort,
    path: Path,
    description: str,
) -> SecretStorePort:
    try:
        store = factory(path, description)
    except _BOUNDARY_ERRORS:
        raise PortableSecretBindingError(
            "A required portable secret store could not be created."
        ) from None
    if not _is_secret_store(store):
        raise PortableSecretBindingError("A portable secret store is invalid.")
    return store


def _is_secret_store(store: object) -> bool:
    try:
        return all(
            callable(getattr(store, method, None))
            for method in ("load", "save", "clear")
        )
    except _BOUNDARY_ERRORS:
        return False
