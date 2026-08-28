from __future__ import annotations

lazy import importlib
lazy import json
lazy import sys
lazy from importlib import util as importlib_util
lazy from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

_SUPPORTED_AEAD_PACKAGES = ("cryptography",)


def _installed_aead_packages() -> tuple[str, ...]:
    return tuple(
        package
        for package in _SUPPORTED_AEAD_PACKAGES
        if importlib_util.find_spec(package) is not None
    )


def _require_audited_aead_dependency() -> None:
    installed = _installed_aead_packages()
    assert installed, (
        "SECURITY_BLOCKED: Python 3.15 必須安裝經稽核的 authenticated-encryption "
        "相依套件；不得以 hashlib.scrypt 搭配自製串流加密與 MAC 取代 AEAD。"
        "請在正式環境安裝支援 Python 3.15 的 cryptography、PyNaCl 或"
        " PyCryptodome，再執行 portable_sensitive.py。"
    )


def _load_contract_module():
    _require_audited_aead_dependency()
    try:
        portable_sensitive = importlib.import_module(
            "infrastructure.portable_sensitive"
        )
    except ModuleNotFoundError as exc:
        raise AssertionError(
            "SECURITY_BLOCKED: 經稽核的 AEAD 模組必須可載入；目前找不到 "
            "infrastructure.portable_sensitive.py。"
        ) from exc
    return portable_sensitive


def _sample_sensitive_payload() -> dict[str, object]:
    return {
        "secrets": {
            "openai": "fixture-openai-key",
            "azure_speech": "fixture-azure-key",
            "azure_dragon_hd": "fixture-dragon-key",
        },
        "face_templates": [
            {
                "identity_id": "owner",
                "display_name": "主上",
                "embedding": [0.125, -0.25, 0.5],
            }
        ],
        "camera_presence_enabled": True,
        "face_identity_enabled": True,
    }


def _assert_default_excludes_sensitive_content(module) -> None:
    assert module.sensitive_export_enabled() is False
    password = bytearray(b"unused export password")
    assert (
        module.build_sensitive_envelope(
            _sample_sensitive_payload(),
            password=password,
            include_sensitive=False,
        )
        is None
    )
    assert all(value == 0 for value in password)


def _assert_password_is_mandatory(module) -> None:
    for password in (None, "", "   "):
        try:
            module.build_sensitive_envelope(
                _sample_sensitive_payload(),
                password=password,
                include_sensitive=True,
            )
        except module.SensitiveProfileError:
            continue
        raise AssertionError("tampered sensitive payload unexpectedly decrypted")


def _assert_versioned_authenticated_round_trip(module) -> None:
    payload = _sample_sensitive_payload()
    password = bytearray(b"correct horse battery staple")
    envelope = module.build_sensitive_envelope(
        payload,
        password=password,
        include_sensitive=True,
    )
    assert isinstance(envelope, bytes)
    decoded_envelope = json.loads(envelope.decode("utf-8"))
    assert decoded_envelope["format"] == "mohan-portable-sensitive"
    assert decoded_envelope["version"] >= 1
    assert decoded_envelope["cipher"] in {
        "AES-256-GCM",
        "XCHACHA20-POLY1305",
    }
    assert decoded_envelope["kdf"] in {"ARGON2ID", "SCRYPT"}
    assert "nonce" in decoded_envelope
    assert "salt" in decoded_envelope
    assert "ciphertext" in decoded_envelope
    assert "fixture-openai-key" not in envelope.decode("utf-8")
    restored = module.open_sensitive_envelope(
        envelope,
        password=bytearray(b"correct horse battery staple"),
    )
    assert restored["secrets"] == payload["secrets"]
    assert restored["face_templates"] == payload["face_templates"]
    assert restored["camera_presence_enabled"] is False
    assert restored["face_identity_enabled"] is False
    assert all(value == 0 for value in password)


def _assert_fresh_salt_and_nonce(module) -> None:
    payload = _sample_sensitive_payload()
    first = module.build_sensitive_envelope(
        payload,
        password=bytearray(b"correct horse battery staple"),
        include_sensitive=True,
    )
    second = module.build_sensitive_envelope(
        payload,
        password=bytearray(b"correct horse battery staple"),
        include_sensitive=True,
    )
    assert first != second
    first_fields = json.loads(first.decode("utf-8"))
    second_fields = json.loads(second.decode("utf-8"))
    assert first_fields["salt"] != second_fields["salt"]
    assert first_fields["nonce"] != second_fields["nonce"]


def _tampered_ciphertext(envelope: bytes) -> bytes:
    fields = json.loads(envelope.decode("utf-8"))
    ciphertext = fields["ciphertext"]
    replacement = "A" if ciphertext[-2] != "A" else "B"
    fields["ciphertext"] = ciphertext[:-2] + replacement + ciphertext[-1]
    return json.dumps(fields, sort_keys=True, separators=(",", ":")).encode("ascii")


def _assert_wrong_password_and_tampering_fail_closed(module) -> None:
    envelope = module.build_sensitive_envelope(
        _sample_sensitive_payload(),
        password=bytearray(b"correct horse battery staple"),
        include_sensitive=True,
    )
    for candidate, password in (
        (envelope, bytearray(b"wrong password")),
        (
            _tampered_ciphertext(envelope),
            bytearray(b"correct horse battery staple"),
        ),
    ):
        try:
            module.open_sensitive_envelope(candidate, password=password)
        except module.SensitiveProfileError:
            assert all(value == 0 for value in password)
            continue
        raise AssertionError("tampered envelope unexpectedly passed fail-closed validation")


def _assert_size_limits_are_enforced_before_expensive_work(module) -> None:
    oversized = b"x" * (module.MAX_SENSITIVE_ENVELOPE_BYTES + 1)
    password = bytearray(b"correct horse battery staple")
    try:
        module.open_sensitive_envelope(oversized, password=password)
    except module.SensitiveProfileError:
        assert all(value == 0 for value in password)
        return
    raise AssertionError("oversized sensitive envelope unexpectedly succeeded")


def _assert_plaintext_size_limit(module) -> None:
    password = bytearray(b"correct horse battery staple")
    payload = {"oversized": "x" * (module.MAX_SENSITIVE_PLAINTEXT_BYTES + 1)}
    try:
        module.build_sensitive_envelope(
            payload,
            password=password,
            include_sensitive=True,
        )
    except module.SensitiveProfileError:
        assert all(value == 0 for value in password)
        return
    raise AssertionError("oversized sensitive plaintext unexpectedly succeeded")


def run() -> None:
    module = _load_contract_module()
    _assert_default_excludes_sensitive_content(module)
    _assert_password_is_mandatory(module)
    _assert_versioned_authenticated_round_trip(module)
    _assert_fresh_salt_and_nonce(module)
    _assert_wrong_password_and_tampering_fail_closed(module)
    _assert_size_limits_are_enforced_before_expensive_work(module)
    _assert_plaintext_size_limit(module)
    print("PORTABLE_SENSITIVE_OK")


if __name__ == "__main__":
    run()
