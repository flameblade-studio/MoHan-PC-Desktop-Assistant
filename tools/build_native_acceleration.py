"""Build and verify MoHan's optional Rust acceleration wheel."""

from __future__ import annotations

lazy import argparse
lazy import hashlib
lazy import json
lazy import os
lazy import platform
lazy import shutil
lazy import subprocess
lazy import sys
lazy import tempfile
lazy import zipfile
lazy from collections.abc import Sequence
lazy from dataclasses import dataclass
lazy from pathlib import Path
lazy from typing import BinaryIO

ROOT = Path(__file__).resolve().parents[1]
NATIVE_ROOT = ROOT / "native" / "mohan_accel"
CARGO_MANIFEST = NATIVE_ROOT / "Cargo.toml"
CARGO_LOCK = NATIVE_ROOT / "Cargo.lock"
PINNED_RUST_VERSION = "1.97.1"
PINNED_MATURIN_VERSION = "1.14.1"
EXPECTED_MODULE_VERSION = "0.1.0"
WHEEL_TAG_FIELD_COUNT = 3


@dataclass(frozen=True, slots=True)
class NativeBuildEvidence:
    wheel: Path
    tags: tuple[str, ...]
    rustc: str
    cargo: str
    maturin: str
    installed_version: str | None
    native_extension: WheelMemberEvidence
    abi3t_compatibility_dll: Path | None


@dataclass(frozen=True, slots=True)
class WheelMemberEvidence:
    path: str
    sha256: str
    size: int


def arguments(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build the locked Python 3.15 abi3t native accelerator and verify "
            "that the resulting wheel imports successfully."
        )
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "native-wheels",
    )
    parser.add_argument("--evidence", type=Path)
    parser.add_argument("--install", action="store_true")
    return parser.parse_args(argv)


def _run(command: Sequence[str], *, cwd: Path = ROOT) -> None:
    subprocess.run(tuple(command), cwd=cwd, check=True)


def _output(command: Sequence[str], *, cwd: Path = ROOT) -> str:
    return subprocess.run(
        tuple(command),
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    ).stdout.strip()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _stream_sha256(handle: BinaryIO) -> str:
    digest = hashlib.sha256()
    read = handle.read
    for block in iter(lambda: read(1024 * 1024), b""):
        digest.update(block)
    return digest.hexdigest()


def _require_python315() -> None:
    if sys.version_info[:2] != (3, 15):
        raise RuntimeError("MoHan native wheels must be built with Python 3.15.")


def _require_tool_versions() -> tuple[str, str, str]:
    rustc = _output(("rustc", "--version"))
    cargo = _output(("cargo", "--version"))
    maturin = _output((sys.executable, "-m", "maturin", "--version"))
    if not rustc.startswith(f"rustc {PINNED_RUST_VERSION} "):
        raise RuntimeError(
            f"Expected rustc {PINNED_RUST_VERSION}; found {rustc or 'unknown'}."
        )
    if not cargo.startswith(f"cargo {PINNED_RUST_VERSION} "):
        raise RuntimeError(
            f"Expected cargo {PINNED_RUST_VERSION}; found {cargo or 'unknown'}."
        )
    if maturin != f"maturin {PINNED_MATURIN_VERSION}":
        raise RuntimeError(
            f"Expected maturin {PINNED_MATURIN_VERSION}; "
            f"found {maturin or 'unknown'}."
        )
    return rustc, cargo, maturin


def maturin_command(output_dir: Path) -> tuple[str, ...]:
    """Return the one canonical, locked native wheel build command."""
    return (
        sys.executable,
        "-m",
        "maturin",
        "build",
        "--manifest-path",
        str(CARGO_MANIFEST),
        "--release",
        "--locked",
        "--features",
        "extension-module",
        "--interpreter",
        sys.executable,
        "--out",
        str(output_dir),
    )


def wheel_tags(path: Path) -> tuple[str, ...]:
    """Read normalized compatibility tags from one wheel archive."""
    with zipfile.ZipFile(path) as archive:
        wheel_metadata = tuple(
            name for name in archive.namelist() if name.endswith(".dist-info/WHEEL")
        )
        if len(wheel_metadata) != 1:
            raise RuntimeError("Native wheel must contain exactly one WHEEL file.")
        document = archive.read(wheel_metadata[0]).decode("utf-8")
    return tuple(
        line.partition(":")[2].strip()
        for line in document.splitlines()
        if line.startswith("Tag:")
    )


def validate_wheel(path: Path) -> tuple[str, ...]:
    tags = wheel_tags(path)
    parsed_tags = tuple(tag.split("-", maxsplit=2) for tag in tags)
    python_values = tuple(fields[0] for fields in parsed_tags if len(fields) == WHEEL_TAG_FIELD_COUNT)
    abi_values = tuple(fields[1] for fields in parsed_tags if len(fields) == WHEEL_TAG_FIELD_COUNT)
    platform_values = tuple(fields[2] for fields in parsed_tags if len(fields) == WHEEL_TAG_FIELD_COUNT)
    if (
        not tags
        or len(python_values) != len(tags)
        or len(abi_values) != len(tags)
        or len(platform_values) != len(tags)
        or set(python_values) != {"cp315"}
        or "abi3t" not in abi_values
        or not set(abi_values) <= {"abi3", "abi3t"}
        or len(set(platform_values)) != 1
        or platform_values[0] in {"", "any"}
    ):
        raise RuntimeError(
            "MoHan native acceleration must include Python 3.15 abi3t, may "
            "only add the companion abi3 stable ABI tag, and must remain "
            "platform-specific; "
            f"found tags {tags or ('missing',)}."
        )
    return tags


def wheel_native_extension(path: Path) -> WheelMemberEvidence:
    """Hash the one compiled extension embedded in a wheel."""
    with zipfile.ZipFile(path) as archive:
        candidates = tuple(
            info
            for info in archive.infolist()
            if Path(info.filename).name.startswith("_mohan_accel")
            and Path(info.filename).suffix in {".pyd", ".so"}
        )
        if len(candidates) != 1:
            raise RuntimeError(
                "Native wheel must contain exactly one compiled "
                f"_mohan_accel extension; found {len(candidates)}."
            )
        member = candidates[0]
        with archive.open(member) as handle:
            digest = _stream_sha256(handle)
    return WheelMemberEvidence(member.filename, digest, member.file_size)


def _abi3t_dll_candidates() -> tuple[Path, ...]:
    roots = {
        Path(sys.executable).resolve().parent,
        Path(sys.base_prefix).resolve(),
        Path(sys.prefix).resolve(),
    }
    relatives = (
        Path("python3t.dll"),
        Path("abi3t-compat/python3t.dll"),
        Path("DLLs/python3t.dll"),
        Path("PCbuild/amd64/python3t.dll"),
        Path("PCbuild/amd64/abi3t-compat/python3t.dll"),
    )
    return tuple(
        sorted(
            {
                *(
                    candidate.resolve()
                    for root in roots
                    for relative in relatives
                    if (candidate := root / relative).is_file()
                )
            },
            key=lambda candidate: candidate.as_posix().casefold(),
        )
    )


def _publish_abi3t_compatibility_dll(output_dir: Path) -> Path | None:
    if os.name != "nt":
        return None
    candidates = _abi3t_dll_candidates()
    if not candidates:
        raise FileNotFoundError(
            "Python 3.15 abi3t compatibility DLL was not found beside the "
            "selected build runtime."
        )
    hashes = {_sha256(candidate) for candidate in candidates}
    if len(hashes) != 1:
        raise RuntimeError(
            "Conflicting python3t.dll files were found beside the selected "
            "build runtime."
        )
    source = candidates[0]
    destination = output_dir / "python3t.dll"
    if destination.exists() and _sha256(destination) != _sha256(source):
        raise FileExistsError(
            "Refusing to overwrite a different python3t.dll build input."
        )
    output_dir.mkdir(parents=True, exist_ok=True)
    if not destination.exists():
        shutil.copy2(source, destination)
    return destination


def _quality_gate() -> None:
    if not CARGO_LOCK.is_file():
        raise FileNotFoundError("Cargo.lock is required for reproducible native builds.")
    _run(("cargo", "fmt", "--manifest-path", str(CARGO_MANIFEST), "--", "--check"))
    _run(
        (
            "cargo",
            "clippy",
            "--manifest-path",
            str(CARGO_MANIFEST),
            "--locked",
            "--all-targets",
            "--all-features",
            "--",
            "-D",
            "warnings",
        )
    )
    _run(
        (
            "cargo",
            "test",
            "--manifest-path",
            str(CARGO_MANIFEST),
            "--locked",
        )
    )


def _install_and_verify(path: Path) -> str:
    _run(
        (
            sys.executable,
            "-m",
            "pip",
            "install",
            "--no-deps",
            "--force-reinstall",
            str(path),
        )
    )
    version = _output(
        (
            sys.executable,
            "-c",
            "import _mohan_accel; print(_mohan_accel.__version__)",
        )
    )
    if version != EXPECTED_MODULE_VERSION:
        raise RuntimeError(
            f"Expected _mohan_accel {EXPECTED_MODULE_VERSION}; found {version}."
        )
    return version


def _publish_wheel(source: Path, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    destination = output_dir / source.name
    if destination.exists():
        if _sha256(destination) != _sha256(source):
            raise FileExistsError(
                f"Refusing to overwrite a different native wheel: {destination.name}"
            )
        return destination
    shutil.copy2(source, destination)
    return destination


def _write_evidence(path: Path, evidence: NativeBuildEvidence) -> None:
    document = {
        "cargo": evidence.cargo,
        "installed_module_version": evidence.installed_version,
        "maturin": evidence.maturin,
        "module": "_mohan_accel",
        "python": platform.python_version(),
        "rustc": evidence.rustc,
        "schema": "mohan.native-acceleration.v2",
        "status": "pass",
        "wheel": evidence.wheel.name,
        "wheel_module": evidence.native_extension.path,
        "wheel_module_sha256": evidence.native_extension.sha256,
        "wheel_module_size": evidence.native_extension.size,
        "wheel_sha256": _sha256(evidence.wheel),
        "wheel_tags": list(evidence.tags),
    }
    if evidence.abi3t_compatibility_dll is not None:
        dll = evidence.abi3t_compatibility_dll
        document["abi3t_compatibility_dll"] = {
            "name": dll.name,
            "sha256": _sha256(dll),
            "size": dll.stat().st_size,
        }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main(argv: Sequence[str] | None = None) -> int:
    args = arguments(argv)
    _require_python315()
    rustc, cargo, maturin = _require_tool_versions()
    _quality_gate()
    with tempfile.TemporaryDirectory(prefix="mohan-native-wheel-") as raw:
        temporary_output = Path(raw)
        _run(maturin_command(temporary_output))
        wheels = tuple(sorted(temporary_output.glob("*.whl")))
        if len(wheels) != 1:
            raise RuntimeError(
                f"Expected exactly one native wheel; found {len(wheels)}."
            )
        tags = validate_wheel(wheels[0])
        native_extension = wheel_native_extension(wheels[0])
        wheel = _publish_wheel(wheels[0], args.output_dir.resolve())
    compatibility_dll = _publish_abi3t_compatibility_dll(
        args.output_dir.resolve()
    )
    installed_version = _install_and_verify(wheel) if args.install else None
    if args.evidence is not None:
        _write_evidence(
            args.evidence.resolve(),
            NativeBuildEvidence(
                wheel,
                tags,
                rustc,
                cargo,
                maturin,
                installed_version,
                native_extension,
                compatibility_dll,
            ),
        )
    print(f"MOHAN_NATIVE_WHEEL_OK={wheel}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
