"""Generate the owner's Ed25519 key, sign an update manifest, and verify it.

The private key is created and kept on the owner's machine.  It is never
committed, never a CI secret, and CI never signs: after the release workflow
publishes ``MoHan-Desktop-Assistant-<tag>-update.json`` the owner runs
``release-sign``, which downloads that exact asset, signs its bytes, uploads
``<manifest>.sig`` and downloads it again to verify against the pinned keys.

    py -3.15 tools/sign_update_manifest.py keygen --private-key <path outside the repo>
    py -3.15 tools/sign_update_manifest.py release-sign --tag v4.7.0 --private-key <path>
    py -3.15 tools/sign_update_manifest.py verify <manifest.json> <manifest.json.sig>
"""
from __future__ import annotations

lazy import argparse
lazy import os
lazy import shutil
lazy import subprocess
lazy import sys
lazy import tempfile
lazy from pathlib import Path

lazy from cryptography.hazmat.primitives import serialization
lazy from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

lazy from infrastructure.update_manifest_signature import (
    PINNED_UPDATE_MANIFEST_PUBLIC_KEYS,
    UpdateManifestSignatureError,
    signature_asset_name,
    verify_manifest_signature,
)

# 讓 `py tools/sign_update_manifest.py …` 與 `py -m tools.sign_update_manifest …`
# 都找得到 infrastructure；與 tests/ 的慣例相同。
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_REPOSITORY = "flameblade-studio/MoHan-PC-Desktop-Assistant"
MANIFEST_NAME_TEMPLATE = "MoHan-Desktop-Assistant-{tag}-update.json"


def public_key_hex(private_key: Ed25519PrivateKey) -> str:
    return private_key.public_key().public_bytes(
        serialization.Encoding.Raw,
        serialization.PublicFormat.Raw,
    ).hex()


def generate_private_key(path: Path) -> str:
    """Write a new PKCS#8 PEM private key; refuse to overwrite; return its public hex."""

    if path.exists():
        raise FileExistsError(f"{path} 已存在，不覆寫既有私鑰。")
    private_key = Ed25519PrivateKey.generate()
    pem = private_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    with os.fdopen(os.open(path, flags, 0o600), "wb") as handle:
        handle.write(pem)
    return public_key_hex(private_key)


def load_private_key(path: Path) -> Ed25519PrivateKey:
    key = serialization.load_pem_private_key(path.read_bytes(), password=None)
    if not isinstance(key, Ed25519PrivateKey):
        raise UpdateManifestSignatureError(f"{path} 不是 Ed25519 私鑰。")
    return key


def sign_manifest_bytes(
    manifest_bytes: bytes,
    private_key: Ed25519PrivateKey,
    *,
    pinned: tuple[str, ...] = PINNED_UPDATE_MANIFEST_PUBLIC_KEYS,
) -> str:
    """Return the hex signature; refuse a key whose public half is not pinned."""

    signature = private_key.sign(manifest_bytes).hex()
    if pinned:
        verify_manifest_signature(manifest_bytes, signature, pinned)
    return signature


def write_signature(manifest: Path, signature_hex: str, output: Path | None) -> Path:
    target = output or manifest.with_name(signature_asset_name(manifest.name))
    target.write_text(signature_hex + "\n", encoding="ascii")
    return target


def _gh(*args: str) -> None:
    executable = shutil.which("gh")
    if executable is None:
        raise UpdateManifestSignatureError("找不到 gh CLI。")
    subprocess.run([executable, *args], check=True)


def release_sign(tag: str, repository: str, private_key_path: Path) -> str:
    manifest_name = MANIFEST_NAME_TEMPLATE.format(tag=tag)
    signature_name = signature_asset_name(manifest_name)
    private_key = load_private_key(private_key_path)
    with tempfile.TemporaryDirectory() as temporary:
        workdir = Path(temporary)
        _gh("release", "download", tag, "--repo", repository,
            "--pattern", manifest_name, "--dir", str(workdir))
        manifest = workdir / manifest_name
        signature_hex = sign_manifest_bytes(manifest.read_bytes(), private_key)
        signature = write_signature(manifest, signature_hex, None)
        _gh("release", "upload", tag, str(signature), "--repo", repository, "--clobber")
        check_dir = workdir / "check"
        check_dir.mkdir()
        _gh("release", "download", tag, "--repo", repository,
            "--pattern", signature_name, "--dir", str(check_dir))
        return verify_manifest_signature(
            manifest.read_bytes(),
            (check_dir / signature_name).read_text(encoding="ascii"),
        )


def _parse_arguments(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="command", required=True)

    keygen = commands.add_parser("keygen", help="產生擁有者私鑰並印出公鑰")
    keygen.add_argument("--private-key", type=Path, required=True)

    sign = commands.add_parser("sign", help="對本機的更新清單檔簽章")
    sign.add_argument("manifest", type=Path)
    sign.add_argument("--private-key", type=Path, required=True)
    sign.add_argument("--out", type=Path, default=None)

    verify = commands.add_parser("verify", help="以內嵌公鑰（或指定公鑰）驗證簽章")
    verify.add_argument("manifest", type=Path)
    verify.add_argument("signature", type=Path)
    verify.add_argument("--public-key", action="append", default=None,
                        help="十六進位公鑰；可重複。省略時用內嵌公鑰")

    release = commands.add_parser(
        "release-sign", help="下載已發布的更新清單、簽章、上傳 .sig、再下載驗證",
    )
    release.add_argument("--tag", required=True)
    release.add_argument("--repo", default=DEFAULT_REPOSITORY)
    release.add_argument("--private-key", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_arguments(argv)
    if args.command == "keygen":
        public = generate_private_key(args.private_key)
        print(f"私鑰已寫入 {args.private_key}（只有這一份，請離線備份）")
        print(f"公鑰（填入 PINNED_UPDATE_MANIFEST_PUBLIC_KEYS）：{public}")
        return 0
    if args.command == "sign":
        private_key = load_private_key(args.private_key)
        signature_hex = sign_manifest_bytes(args.manifest.read_bytes(), private_key)
        print(write_signature(args.manifest, signature_hex, args.out))
        return 0
    if args.command == "verify":
        key = verify_manifest_signature(
            args.manifest.read_bytes(),
            args.signature.read_text(encoding="ascii"),
            args.public_key,
        )
        print(f"UPDATE_MANIFEST_SIGNATURE_OK key={key[:16]}…")
        return 0
    key = release_sign(args.tag, args.repo, args.private_key)
    print(f"UPDATE_MANIFEST_SIGNED tag={args.tag} key={key[:16]}…")
    return 0


if __name__ == "__main__":
    # 只在當腳本跑時改主控台編碼；被測試匯入時不能動 pytest 接管的 stdout。
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
