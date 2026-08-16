from __future__ import annotations

lazy import json
lazy from collections.abc import Mapping
lazy from typing import Final, TypedDict

lazy from domain.contracts import SecretStorePort

PORTABLE_SECRETS_FORMAT: Final = "mohan-portable-secrets"
PORTABLE_SECRETS_VERSION: Final = 1
MAX_SECRET_BYTES: Final = 2 * 1024 * 1024
MAX_PAYLOAD_BYTES: Final = 4 * 1024 * 1024

SECRET_IDS: Final = frozenset(
    {
        "openai",
        "azure_speech",
        "azure_dragon_hd",
        "home_assistant",
        "oauth_google",
        "oauth_microsoft",
        "oauth_github",
        "face_identities",
        "gesture_templates",
    }
)
_PAYLOAD_KEYS: Final = frozenset({"format", "version", "secrets"})
# Secret stores are injected platform boundaries. Their implementation may
# raise any exception; every such detail must be replaced with a fixed error.
_STORE_OPERATION_ERRORS: Final = (Exception,)

class PortableSecretsPayload(TypedDict):
    format: str
    version: int
    secrets: dict[str, str]


class PortableSecretsError(RuntimeError):
    """A fail-closed portable-secret boundary error with no secret detail."""


def collect_sensitive_payload(
    stores: Mapping[str, SecretStorePort],
) -> PortableSecretsPayload:
    """Collect non-empty protected strings into one strict portable schema."""

    validated_stores = _validated_stores(stores)
    secrets: dict[str, str] = {}
    for secret_id in sorted(validated_stores):
        try:
            value = validated_stores[secret_id].load()
        except _STORE_OPERATION_ERRORS:
            raise PortableSecretsError("A protected secret could not be read.") from None
        _validate_secret_value(value)
        if value:
            secrets[secret_id] = value
    payload: PortableSecretsPayload = {
        "format": PORTABLE_SECRETS_FORMAT,
        "version": PORTABLE_SECRETS_VERSION,
        "secrets": secrets,
    }
    _validate_payload_size(payload)
    return payload


def apply_sensitive_payload(
    payload: Mapping[str, object],
    stores: Mapping[str, SecretStorePort],
) -> None:
    """Apply protected strings atomically while preserving omitted stores."""

    secrets = validate_sensitive_payload(payload)["secrets"]
    validated_stores = _validated_stores(stores)
    missing = set(secrets) - set(validated_stores)
    if missing:
        raise PortableSecretsError("A required protected-secret store is unavailable.")

    previous: dict[str, str] = {}
    for secret_id in secrets:
        try:
            value = validated_stores[secret_id].load()
        except _STORE_OPERATION_ERRORS:
            raise PortableSecretsError("Existing protected secrets could not be read.") from None
        _validate_secret_value(value)
        previous[secret_id] = value

    attempted: list[str] = []
    try:
        for secret_id, value in secrets.items():
            attempted.append(secret_id)
            validated_stores[secret_id].save(value)
    except _STORE_OPERATION_ERRORS:
        if not _restore_previous_values(attempted, previous, validated_stores):
            raise PortableSecretsError(
                "Protected-secret import failed and rollback was incomplete."
            ) from None
        raise PortableSecretsError(
            "Protected-secret import failed; previous values were restored."
        ) from None


def validate_sensitive_payload(
    payload: Mapping[str, object],
) -> PortableSecretsPayload:
    """Return a strict, detached copy suitable for an encrypted boundary."""

    secrets = _validated_payload(payload)
    return {
        "format": PORTABLE_SECRETS_FORMAT,
        "version": PORTABLE_SECRETS_VERSION,
        "secrets": secrets,
    }


def _validated_stores(
    stores: Mapping[str, SecretStorePort],
) -> dict[str, SecretStorePort]:
    if not isinstance(stores, Mapping):
        raise PortableSecretsError("Protected-secret stores are invalid.")
    validated: dict[str, SecretStorePort] = {}
    for secret_id, store in stores.items():
        if not isinstance(secret_id, str) or secret_id not in SECRET_IDS:
            raise PortableSecretsError("Protected-secret stores contain an unknown ID.")
        try:
            valid_store = all(
                callable(getattr(store, method, None))
                for method in ("load", "save", "clear")
            )
        except _STORE_OPERATION_ERRORS:
            raise PortableSecretsError("A protected-secret store is invalid.") from None
        if not valid_store:
            raise PortableSecretsError("A protected-secret store is invalid.")
        validated[secret_id] = store
    return validated


def _validated_payload(payload: Mapping[str, object]) -> dict[str, str]:
    if not isinstance(payload, Mapping) or set(payload) != _PAYLOAD_KEYS:
        raise PortableSecretsError("The protected-secret payload schema is invalid.")
    if payload.get("format") != PORTABLE_SECRETS_FORMAT:
        raise PortableSecretsError("The protected-secret payload format is unsupported.")
    version = payload.get("version")
    if isinstance(version, bool) or version != PORTABLE_SECRETS_VERSION:
        raise PortableSecretsError("The protected-secret payload version is unsupported.")
    raw_secrets = payload.get("secrets")
    if not isinstance(raw_secrets, Mapping):
        raise PortableSecretsError("The protected-secret payload schema is invalid.")
    secrets: dict[str, str] = {}
    for secret_id, value in raw_secrets.items():
        if not isinstance(secret_id, str) or secret_id not in SECRET_IDS:
            raise PortableSecretsError("The protected-secret payload contains an unknown ID.")
        _validate_secret_value(value)
        if not value:
            raise PortableSecretsError("The protected-secret payload contains an empty value.")
        secrets[secret_id] = value
    normalized: PortableSecretsPayload = {
        "format": PORTABLE_SECRETS_FORMAT,
        "version": PORTABLE_SECRETS_VERSION,
        "secrets": secrets,
    }
    _validate_payload_size(normalized)
    return secrets


def _validate_secret_value(value: object) -> None:
    if not isinstance(value, str):
        raise PortableSecretsError("A protected-secret value has an invalid type.")
    try:
        size = len(value.encode("utf-8"))
    except UnicodeError:
        raise PortableSecretsError("A protected-secret value is invalid.") from None
    if size > MAX_SECRET_BYTES:
        raise PortableSecretsError("A protected-secret value is too large.")


def _validate_payload_size(payload: Mapping[str, object]) -> None:
    try:
        serialized = json.dumps(
            dict(payload),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    except (TypeError, ValueError, UnicodeError):
        raise PortableSecretsError("The protected-secret payload is invalid.") from None
    if len(serialized) > MAX_PAYLOAD_BYTES:
        raise PortableSecretsError("The protected-secret payload is too large.")


def _restore_previous_values(
    attempted: list[str],
    previous: Mapping[str, str],
    stores: Mapping[str, SecretStorePort],
) -> bool:
    restored = True
    for secret_id in reversed(attempted):
        try:
            old_value = previous[secret_id]
            if old_value:
                stores[secret_id].save(old_value)
            else:
                stores[secret_id].clear()
        except _STORE_OPERATION_ERRORS:
            restored = False
    return restored
