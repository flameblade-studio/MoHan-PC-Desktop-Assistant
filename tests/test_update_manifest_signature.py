"""更新清單的 Ed25519 分離簽章：模組、工具與更新器整合。

安全結論只有一條：沒有能以內嵌公鑰驗證的簽章，更新器就不會把任何安裝程式
當成可用更新，不論 SHA-256 多麼一致。
"""
from __future__ import annotations

lazy import hashlib
lazy import json
lazy from email.message import Message
lazy from pathlib import Path
lazy from urllib.error import URLError

lazy import pytest

lazy from infrastructure.update_manifest_signature import (
    UpdateManifestSignatureError,
    parse_public_key,
    require_pinned_keys,
    signature_asset_name,
    verify_manifest_signature,
)
lazy from infrastructure.updater import UpdateError, UpdateManager
lazy from tools.sign_update_manifest import (
    generate_private_key,
    load_private_key,
    main as tool_main,
    public_key_hex,
    sign_manifest_bytes,
)

REPO = "flameblade-studio/MoHan-PC-Desktop-Assistant"
TAG = "v9.9.9"
MANIFEST_NAME = f"MoHan-Desktop-Assistant-{TAG}-update.json"


class _FakeResponse:
    def __init__(self, url: str, payload: bytes) -> None:
        self.url = url
        self.payload = payload
        self.offset = 0
        self.headers = Message()
        self.headers["Content-Length"] = str(len(payload))

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def geturl(self) -> str:
        return self.url

    def read(self, size: int = -1) -> bytes:
        if size < 0:
            size = len(self.payload) - self.offset
        chunk = self.payload[self.offset : self.offset + size]
        self.offset += len(chunk)
        return chunk


def _opener(responses: dict[str, bytes]):
    def open_url(request, **_kwargs):
        if request.full_url not in responses:
            raise URLError("unexpected URL")
        return _FakeResponse(request.full_url, responses[request.full_url])

    return open_url


@pytest.fixture
def owner_key(tmp_path: Path):
    public = generate_private_key(tmp_path / "keys" / "owner.pem")
    return load_private_key(tmp_path / "keys" / "owner.pem"), public


def _release(manifest_bytes: bytes, signature: bytes | None) -> dict[str, bytes]:
    base = f"https://github.com/{REPO}/releases/download/{TAG}/"
    installer = b"installer bytes"
    assets = [{"name": MANIFEST_NAME, "browser_download_url": base + MANIFEST_NAME}]
    responses = {base + MANIFEST_NAME: manifest_bytes, base + "setup.exe": installer}
    if signature is not None:
        name = signature_asset_name(MANIFEST_NAME)
        assets.append({"name": name, "browser_download_url": base + name})
        responses[base + name] = signature
    release = {
        "tag_name": TAG, "draft": False, "prerelease": False,
        "html_url": f"https://github.com/{REPO}/releases/tag/{TAG}",
        "body": "", "published_at": "2026-09-02T00:00:00Z", "assets": assets,
    }
    responses[f"https://api.github.com/repos/{REPO}/releases/latest"] = json.dumps(
        release
    ).encode()
    return responses


def _manifest_bytes() -> bytes:
    installer = b"installer bytes"
    return json.dumps({
        "schema": 1, "repository": REPO, "version": "9.9.9", "tag": TAG,
        "installers": [{
            "kind": "exe", "name": "setup.exe",
            "url": f"https://github.com/{REPO}/releases/download/{TAG}/setup.exe",
            "sha256": hashlib.sha256(installer).hexdigest(), "size": len(installer),
        }],
    }).encode()


def _manager(responses, public_keys, tmp_path: Path) -> UpdateManager:
    return UpdateManager(REPO, "1.0.0", tmp_path, _opener(responses), public_keys=public_keys)


# ---- 模組 ----

def test_signature_round_trip_and_tamper_detection(owner_key) -> None:
    private, public = owner_key
    payload = b'{"schema": 1}'
    signature = sign_manifest_bytes(payload, private, pinned=(public,))
    assert verify_manifest_signature(payload, signature, (public,)) == public
    with pytest.raises(UpdateManifestSignatureError):
        verify_manifest_signature(payload + b" ", signature, (public,))
    with pytest.raises(UpdateManifestSignatureError):
        verify_manifest_signature(payload, "0" * 128, (public,))
    assert public_key_hex(private) == public


def test_empty_or_malformed_pins_fail_closed() -> None:
    with pytest.raises(UpdateManifestSignatureError, match="尚未內嵌"):
        require_pinned_keys(())
    with pytest.raises(UpdateManifestSignatureError):
        require_pinned_keys(("not-hex",))
    with pytest.raises(UpdateManifestSignatureError):
        parse_public_key("ab" * 31)


def test_signing_with_an_unpinned_key_is_refused(owner_key, tmp_path: Path) -> None:
    private, _public = owner_key
    stranger = generate_private_key(tmp_path / "stranger.pem")
    with pytest.raises(UpdateManifestSignatureError):
        sign_manifest_bytes(b"x", private, pinned=(stranger,))


# ---- 更新器整合 ----

def test_updater_accepts_a_manifest_signed_by_a_pinned_key(owner_key, tmp_path) -> None:
    private, public = owner_key
    manifest = _manifest_bytes()
    signature = sign_manifest_bytes(manifest, private, pinned=(public,)).encode()
    update = _manager(_release(manifest, signature), (public,), tmp_path).check("stable")
    assert update is not None and update.version == "9.9.9"


def test_updater_refuses_a_release_without_a_signature(owner_key, tmp_path) -> None:
    _private, public = owner_key
    with pytest.raises(UpdateError, match="尚未簽章"):
        _manager(_release(_manifest_bytes(), None), (public,), tmp_path).check("stable")


def test_updater_refuses_a_tampered_manifest_even_with_matching_hashes(
    owner_key, tmp_path
) -> None:
    private, public = owner_key
    manifest = _manifest_bytes()
    signature = sign_manifest_bytes(manifest, private, pinned=(public,)).encode()
    tampered = manifest.replace(b'"9.9.9"', b'"9.9.9"', 1) + b"\n"
    with pytest.raises(UpdateError, match="簽章驗證失敗"):
        _manager(_release(tampered, signature), (public,), tmp_path).check("stable")


def test_updater_refuses_a_signature_from_an_unpinned_key(owner_key, tmp_path) -> None:
    private, _public = owner_key
    stranger = generate_private_key(tmp_path / "stranger.pem")
    manifest = _manifest_bytes()
    signature = sign_manifest_bytes(manifest, private, pinned=()).encode()
    with pytest.raises(UpdateError, match="簽章驗證失敗"):
        _manager(_release(manifest, signature), (stranger,), tmp_path).check("stable")


def test_updater_with_no_pinned_key_refuses_every_update(owner_key, tmp_path) -> None:
    private, public = owner_key
    manifest = _manifest_bytes()
    signature = sign_manifest_bytes(manifest, private, pinned=(public,)).encode()
    with pytest.raises(UpdateError):
        _manager(_release(manifest, signature), (), tmp_path).check("stable")


# ---- 工具 CLI ----

def test_cli_keygen_sign_verify(tmp_path: Path, capsys) -> None:
    key_path = tmp_path / "owner.pem"
    assert tool_main(["keygen", "--private-key", str(key_path)]) == 0
    public = capsys.readouterr().out.split("：")[-1].strip()
    manifest = tmp_path / MANIFEST_NAME
    manifest.write_bytes(_manifest_bytes())
    # 臨時金鑰沒有內嵌：CLI 的 sign 必須拒絕，避免簽出用戶端不認的簽章。
    with pytest.raises(UpdateManifestSignatureError):
        tool_main(["sign", str(manifest), "--private-key", str(key_path)])
    signature = manifest.with_name(signature_asset_name(MANIFEST_NAME))
    signature.write_text(
        sign_manifest_bytes(manifest.read_bytes(), load_private_key(key_path), pinned=(public,))
        + "\n",
        encoding="ascii",
    )
    assert tool_main([
        "verify", str(manifest), str(signature), "--public-key", public,
    ]) == 0
    with pytest.raises(UpdateManifestSignatureError):
        tool_main(["verify", str(manifest), str(signature)])  # 內嵌公鑰不認臨時金鑰
    with pytest.raises(FileExistsError):
        generate_private_key(key_path)
