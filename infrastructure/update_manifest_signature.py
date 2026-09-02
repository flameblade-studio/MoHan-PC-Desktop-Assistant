"""Ed25519 detached signatures for the GitHub update manifest.

The manifest's SHA-256 values prove that a downloaded installer matches the
manifest.  They do not prove who issued the manifest: manifest and installer
sit in the same GitHub Release, so anyone who can write to the Release can
replace both together and every hash still matches.  The detached signature
moves the trust anchor from "the GitHub account" to "the owner's private
key", which never leaves the owner's machine and is never a CI secret.

Contract:
- the signature covers the manifest asset's exact bytes, nothing canonical;
- it is published as a separate Release asset named ``<manifest>.sig`` and
  contains the 64-byte Ed25519 signature as 128 lowercase hex characters;
- the client pins one or more public keys here and refuses any release whose
  manifest lacks a signature that verifies under a pinned key (fail closed);
- an empty pin list is a build-time error caught before release, never a
  runtime "skip verification".
"""
from __future__ import annotations

lazy import binascii
lazy from collections.abc import Iterable

lazy from cryptography.exceptions import InvalidSignature
lazy from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

SIGNATURE_SUFFIX = ".sig"
PUBLIC_KEY_HEX_LENGTH = 64
SIGNATURE_HEX_LENGTH = 128
MAX_SIGNATURE_BYTES = 4 * 1024

# Owner-generated with `py -3.15 tools/sign_update_manifest.py keygen`.  The
# private key stays on the owner's machine; only the public half is pinned.
# Rotation: append the new key, ship a client release, then remove the old
# key in a later release.  While this tuple is empty the release workflow
# refuses to publish a client and the updater refuses every update.
PINNED_UPDATE_MANIFEST_PUBLIC_KEYS: tuple[str, ...] = (
    "411f1e848009b997f1d0685b271e04f560f66ec0c3260b1f3d508dba6bdb0f6f",  # owner key #1, generated 2026-09-02
)


class UpdateManifestSignatureError(ValueError):
    """The manifest signature is missing, malformed or does not verify."""


def signature_asset_name(manifest_name: str) -> str:
    return f"{manifest_name}{SIGNATURE_SUFFIX}"


def parse_public_key(hex_key: str) -> Ed25519PublicKey:
    text = hex_key.strip().lower()
    if len(text) != PUBLIC_KEY_HEX_LENGTH:
        raise UpdateManifestSignatureError("公鑰必須是 64 個十六進位字元。")
    try:
        raw = binascii.unhexlify(text)
    except (binascii.Error, ValueError):
        raise UpdateManifestSignatureError("公鑰不是合法的十六進位字串。") from None
    try:
        return Ed25519PublicKey.from_public_bytes(raw)
    except ValueError:
        raise UpdateManifestSignatureError("公鑰不是合法的 Ed25519 公鑰。") from None


def parse_signature(signature_text: str | bytes) -> bytes:
    if isinstance(signature_text, bytes):
        try:
            signature_text = signature_text.decode("ascii")
        except UnicodeDecodeError:
            raise UpdateManifestSignatureError("簽章檔不是 ASCII 文字。") from None
    text = signature_text.strip().lower()
    if len(text) != SIGNATURE_HEX_LENGTH:
        raise UpdateManifestSignatureError("簽章必須是 128 個十六進位字元。")
    try:
        return binascii.unhexlify(text)
    except (binascii.Error, ValueError):
        raise UpdateManifestSignatureError("簽章不是合法的十六進位字串。") from None


def require_pinned_keys(
    public_keys: Iterable[str] | None = None,
) -> tuple[str, ...]:
    """Return the pinned keys or raise; used as a release-time gate."""

    keys = tuple(
        PINNED_UPDATE_MANIFEST_PUBLIC_KEYS if public_keys is None else public_keys
    )
    if not keys:
        raise UpdateManifestSignatureError(
            "尚未內嵌任何更新清單公鑰；請先執行 tools/sign_update_manifest.py keygen "
            "並把公鑰填入 PINNED_UPDATE_MANIFEST_PUBLIC_KEYS。"
        )
    for key in keys:
        parse_public_key(key)
    return keys


def verify_manifest_signature(
    manifest_bytes: bytes,
    signature_text: str | bytes,
    public_keys: Iterable[str] | None = None,
) -> str:
    """Verify and return the hex of the pinned key that signed the manifest."""

    keys = require_pinned_keys(public_keys)
    signature = parse_signature(signature_text)
    for key_hex in keys:
        try:
            parse_public_key(key_hex).verify(signature, manifest_bytes)
        except InvalidSignature:
            continue
        return key_hex.strip().lower()
    raise UpdateManifestSignatureError("更新清單的簽章與任何內嵌公鑰都不符。")
