"""Verify the byte and typing contract of MoHan's locked Qt wheel set."""

from __future__ import annotations

lazy import argparse
lazy import hashlib
lazy import json
lazy import os
lazy import platform
lazy import sys
lazy import zipfile
lazy from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LOCK = ROOT / "tools" / "qt315" / "wheel-hashes.json"
WHEELHOUSE_ENVIRONMENT = "MOHAN_QT315_WHEELHOUSE"
SHA256_HEXDIGEST_LENGTH = 64


def platform_key() -> str:
    machine = platform.machine().casefold()
    if sys.platform == "win32" and machine in {"amd64", "x86_64"}:
        return "win_amd64"
    if sys.platform == "linux" and machine in {"amd64", "x86_64"}:
        return "manylinux_x86_64"
    if sys.platform == "darwin" and machine in {"arm64", "aarch64"}:
        return "macosx_arm64"
    if sys.platform == "darwin" and machine in {"amd64", "x86_64"}:
        return "macosx_x86_64"
    return f"{sys.platform}_{machine or 'unknown'}"


def default_shared_wheelhouse(root: Path = ROOT) -> Path:
    return root.parents[1] / "shared" / "qt315-ci-parity" / platform_key()


def selected_wheelhouse(root: Path = ROOT) -> Path:
    configured = os.environ.get(WHEELHOUSE_ENVIRONMENT)
    if configured:
        return Path(configured).expanduser().resolve()
    ci_wheelhouse = root / "qt315-wheelhouse"
    if ci_wheelhouse.is_dir():
        return ci_wheelhouse.resolve()
    return default_shared_wheelhouse(root).resolve()


def load_wheel_lock(path: Path = DEFAULT_LOCK) -> dict[str, object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise RuntimeError(f"Cannot read Qt wheel hash lock {path}: {error}") from error
    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        raise RuntimeError("Qt wheel hash lock requires schema_version 1")
    platforms = payload.get("platforms")
    if not isinstance(platforms, dict) or not platforms:
        raise RuntimeError("Qt wheel hash lock requires a non-empty platforms object")
    for key, value in platforms.items():
        if not isinstance(key, str) or not isinstance(value, dict):
            raise RuntimeError("Qt wheel hash lock has an invalid platform entry")
        wheels = value.get("wheels")
        if not isinstance(wheels, list) or not wheels:
            raise RuntimeError(f"Qt wheel hash lock platform {key} has no wheels")
        filenames: set[str] = set()
        for wheel in wheels:
            if not isinstance(wheel, dict):
                raise RuntimeError(f"Qt wheel hash lock platform {key} has an invalid wheel")
            filename = wheel.get("filename")
            digest = wheel.get("sha256")
            pyi_count = wheel.get("pyi_count")
            py_typed_count = wheel.get("py_typed_count")
            if (
                not isinstance(filename, str)
                or not filename.endswith(".whl")
                or not isinstance(digest, str)
                or len(digest) != SHA256_HEXDIGEST_LENGTH
                or any(character not in "0123456789abcdef" for character in digest)
                or not isinstance(pyi_count, int)
                or pyi_count < 0
                or not isinstance(py_typed_count, int)
                or py_typed_count < 0
            ):
                raise RuntimeError(
                    f"Qt wheel hash lock platform {key} has invalid wheel fields"
                )
            if filename in filenames:
                raise RuntimeError(f"Qt wheel hash lock repeats {filename}")
            filenames.add(filename)
    return payload


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_locked_wheelhouse(
    wheelhouse: Path,
    lock_path: Path = DEFAULT_LOCK,
    *,
    target_platform: str | None = None,
) -> tuple[dict[str, object], ...]:
    payload = load_wheel_lock(lock_path)
    key = target_platform or platform_key()
    platforms = payload["platforms"]
    assert isinstance(platforms, dict)
    platform_entry = platforms.get(key)
    if not isinstance(platform_entry, dict):
        raise RuntimeError(f"Qt wheel hash lock has no entry for platform {key}")
    wheels = platform_entry["wheels"]
    assert isinstance(wheels, list)
    expected = {str(item["filename"]): item for item in wheels}
    actual_names = {path.name for path in wheelhouse.glob("*.whl") if path.is_file()}
    if actual_names != set(expected):
        missing = sorted(set(expected) - actual_names)
        extra = sorted(actual_names - set(expected))
        raise RuntimeError(
            f"Qt wheel set mismatch for {key}: missing={missing}, extra={extra}"
        )
    verified: list[dict[str, object]] = []
    for filename in sorted(expected):
        specification = expected[filename]
        assert isinstance(specification, dict)
        wheel = wheelhouse / filename
        digest = _sha256(wheel)
        if digest != specification["sha256"]:
            raise RuntimeError(
                f"Qt wheel SHA-256 mismatch for {filename}: "
                f"expected {specification['sha256']}, found {digest}"
            )
        with zipfile.ZipFile(wheel) as archive:
            names = archive.namelist()
        pyi_count = sum(name.endswith(".pyi") for name in names)
        py_typed_count = sum(name.endswith("py.typed") for name in names)
        if pyi_count != specification["pyi_count"]:
            raise RuntimeError(
                f"Qt wheel .pyi count mismatch for {filename}: "
                f"expected {specification['pyi_count']}, found {pyi_count}"
            )
        if py_typed_count != specification["py_typed_count"]:
            raise RuntimeError(
                f"Qt wheel py.typed count mismatch for {filename}: "
                f"expected {specification['py_typed_count']}, found {py_typed_count}"
            )
        verified.append(
            {
                "filename": filename,
                "sha256": digest,
                "pyi_count": pyi_count,
                "py_typed_count": py_typed_count,
            }
        )
    return tuple(verified)


def arguments(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify the locked Qt wheel set.")
    parser.add_argument("--wheelhouse", type=Path)
    parser.add_argument("--lock", type=Path, default=DEFAULT_LOCK)
    parser.add_argument("--platform", dest="target_platform")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = arguments(argv)
    wheelhouse = (args.wheelhouse or selected_wheelhouse()).resolve()
    try:
        verified = verify_locked_wheelhouse(
            wheelhouse,
            args.lock.resolve(),
            target_platform=args.target_platform,
        )
    except (OSError, RuntimeError, zipfile.BadZipFile) as error:
        print(f"QT315_WHEEL_PARITY_FAILED: {error}", file=sys.stderr)
        print(
            "Run: python tools/install_python315_dependencies.py --like-ci",
            file=sys.stderr,
        )
        return 1
    print(
        f"QT315_WHEEL_PARITY_OK platform={args.target_platform or platform_key()} "
        f"wheels={len(verified)} wheelhouse={wheelhouse}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
