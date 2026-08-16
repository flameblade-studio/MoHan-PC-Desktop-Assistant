from __future__ import annotations

lazy import base64
lazy import binascii
lazy import json
lazy import os
lazy from collections.abc import Mapping
lazy from typing import Any

lazy from cryptography.exceptions import InvalidTag
lazy from cryptography.hazmat.primitives.ciphers.aead import AESGCM
lazy from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

ENVELOPE_FORMAT = "mohan-portable-sensitive"
ENVELOPE_VERSION = 1
CIPHER_NAME = "AES-256-GCM"
KDF_NAME = "SCRYPT"
MAX_SENSITIVE_PLAINTEXT_BYTES = 4 * 1024 * 1024
MAX_SENSITIVE_ENVELOPE_BYTES = 8 * 1024 * 1024

_KEY_BYTES = 32
_SALT_BYTES = 16
_NONCE_BYTES = 12
_SCRYPT_N = 1 << 17
_SCRYPT_R = 8
_SCRYPT_P = 1
_REQUIRED_ENVELOPE_KEYS = frozenset({
    "format",
    "version",
    "cipher",
    "kdf",
    "kdf_params",
    "salt",
    "nonce",
    "ciphertext",
})


class SensitiveProfileError(RuntimeError):
    """A fail-closed sensitive-profile boundary error."""


def sensitive_export_enabled() -> bool:
    """Sensitive profile export is always opt-in at the calling UI boundary."""

    return False


def _wipe(buffer: bytearray | None) -> None:
    if buffer is not None:
        buffer[:] = b"\0" * len(buffer)


def _password_buffer(password: str | bytes | bytearray | None) -> bytearray:
    if isinstance(password, bytearray):
        candidate = password
    elif isinstance(password, bytes):
        candidate = bytearray(password)
    elif isinstance(password, str):
        candidate = bytearray(password.encode("utf-8"))
    elif password is None:
        raise SensitiveProfileError("A password is required.")
    else:
        raise SensitiveProfileError("The password type is not supported.")
    if not candidate or not bytes(candidate).strip():
        _wipe(candidate)
        raise SensitiveProfileError("A password is required.")
    return candidate


def _derive_key(password: bytearray, salt: bytes) -> bytearray:
    derived = Scrypt(
        salt=salt,
        length=_KEY_BYTES,
        n=_SCRYPT_N,
        r=_SCRYPT_R,
        p=_SCRYPT_P,
    ).derive(password)
    return bytearray(derived)


def _kdf_parameters() -> dict[str, int]:
    return {
        "n": _SCRYPT_N,
        "r": _SCRYPT_R,
        "p": _SCRYPT_P,
        "length": _KEY_BYTES,
    }


def _metadata() -> dict[str, object]:
    return {
        "format": ENVELOPE_FORMAT,
        "version": ENVELOPE_VERSION,
        "cipher": CIPHER_NAME,
        "kdf": KDF_NAME,
        "kdf_params": _kdf_parameters(),
    }


def _associated_data(metadata: Mapping[str, object]) -> bytes:
    return json.dumps(
        dict(metadata),
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("ascii")


def _encode(value: bytes) -> str:
    return base64.b64encode(value).decode("ascii")


def _decode(value: object, *, expected_size: int | None = None) -> bytes:
    if not isinstance(value, str):
        raise SensitiveProfileError("The encrypted profile is invalid.")
    try:
        decoded = base64.b64decode(value, validate=True)
    except binascii.Error, ValueError:
        raise SensitiveProfileError("The encrypted profile is invalid.") from None
    if _encode(decoded) != value:
        raise SensitiveProfileError("The encrypted profile is invalid.")
    if expected_size is not None and len(decoded) != expected_size:
        raise SensitiveProfileError("The encrypted profile is invalid.")
    return decoded


def _serialize_payload(payload: Mapping[str, object]) -> bytearray:
    try:
        serialized = json.dumps(
            dict(payload),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    except TypeError, ValueError, UnicodeError:
        raise SensitiveProfileError(
            "The sensitive profile content is not serializable."
        ) from None
    if len(serialized) > MAX_SENSITIVE_PLAINTEXT_BYTES:
        raise SensitiveProfileError("The sensitive profile content is too large.")
    return bytearray(serialized)


def _validated_envelope(envelope: bytes) -> dict[str, Any]:
    if not envelope or len(envelope) > MAX_SENSITIVE_ENVELOPE_BYTES:
        raise SensitiveProfileError("The encrypted profile size is invalid.")
    try:
        decoded = json.loads(envelope.decode("utf-8"))
    except UnicodeError, json.JSONDecodeError:
        raise SensitiveProfileError("The encrypted profile is invalid.") from None
    if not isinstance(decoded, dict) or set(decoded) != _REQUIRED_ENVELOPE_KEYS:
        raise SensitiveProfileError("The encrypted profile is invalid.")
    metadata = _metadata()
    if any(decoded.get(key) != value for key, value in metadata.items()):
        raise SensitiveProfileError("The encrypted profile version is unsupported.")
    return decoded


def build_sensitive_envelope(
    payload: Mapping[str, object],
    *,
    password: str | bytes | bytearray | None,
    include_sensitive: bool = False,
) -> bytes | None:
    """Encrypt explicitly selected secrets and biometric templates."""

    password_bytes: bytearray | None = None
    plaintext: bytearray | None = None
    key: bytearray | None = None
    try:
        if not include_sensitive:
            if isinstance(password, bytearray):
                _wipe(password)
            return None
        if not isinstance(payload, Mapping):
            raise SensitiveProfileError("The sensitive profile content is invalid.")
        password_bytes = _password_buffer(password)
        plaintext = _serialize_payload(payload)
        metadata = _metadata()
        salt = os.urandom(_SALT_BYTES)
        nonce = os.urandom(_NONCE_BYTES)
        key = _derive_key(password_bytes, salt)
        ciphertext = AESGCM(key).encrypt(
            nonce,
            plaintext,
            _associated_data(metadata),
        )
        envelope = {
            **metadata,
            "salt": _encode(salt),
            "nonce": _encode(nonce),
            "ciphertext": _encode(ciphertext),
        }
        encoded = json.dumps(
            envelope,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("ascii")
        if len(encoded) > MAX_SENSITIVE_ENVELOPE_BYTES:
            raise SensitiveProfileError("The encrypted profile is too large.")
        return encoded
    finally:
        _wipe(key)
        _wipe(plaintext)
        _wipe(password_bytes)


def open_sensitive_envelope(
    envelope: bytes,
    *,
    password: str | bytes | bytearray | None,
) -> dict[str, object]:
    """Authenticate and decrypt a sensitive envelope without enabling devices."""

    password_bytes: bytearray | None = None
    plaintext: bytearray | None = None
    key: bytearray | None = None
    try:
        password_bytes = _password_buffer(password)
        decoded = _validated_envelope(envelope)
        salt = _decode(decoded["salt"], expected_size=_SALT_BYTES)
        nonce = _decode(decoded["nonce"], expected_size=_NONCE_BYTES)
        ciphertext = _decode(decoded["ciphertext"])
        if len(ciphertext) > MAX_SENSITIVE_PLAINTEXT_BYTES + 16:
            raise SensitiveProfileError("The encrypted profile content is too large.")
        metadata = {key: decoded[key] for key in _metadata()}
        key = _derive_key(password_bytes, salt)
        try:
            decrypted = AESGCM(key).decrypt(
                nonce,
                ciphertext,
                _associated_data(metadata),
            )
        except InvalidTag:
            raise SensitiveProfileError(
                "The password is incorrect or the encrypted profile was modified."
            ) from None
        plaintext = bytearray(decrypted)
        if len(plaintext) > MAX_SENSITIVE_PLAINTEXT_BYTES:
            raise SensitiveProfileError("The sensitive profile content is too large.")
        try:
            payload = json.loads(plaintext.decode("utf-8"))
        except UnicodeError, json.JSONDecodeError:
            raise SensitiveProfileError(
                "The decrypted profile content is invalid."
            ) from None
        if not isinstance(payload, dict):
            raise SensitiveProfileError("The decrypted profile content is invalid.")
        result = dict(payload)
        result["camera_presence_enabled"] = False
        result["face_identity_enabled"] = False
        return result
    except SensitiveProfileError:
        raise
    except MemoryError, OverflowError, TypeError, ValueError:
        raise SensitiveProfileError("The encrypted profile is invalid.") from None
    finally:
        _wipe(key)
        _wipe(plaintext)
        _wipe(password_bytes)
