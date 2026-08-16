"""Verify that one packaged MoHan native module is present and operational."""

from __future__ import annotations

lazy import argparse
lazy import hashlib
lazy import json
lazy import os
lazy import re
lazy import sys
lazy from collections.abc import Sequence
lazy from importlib.util import module_from_spec, spec_from_file_location
lazy from pathlib import Path
lazy from types import ModuleType

EXPECTED_MODULE_VERSION = "0.1.0"
SUCCESS_MARKER = "PACKAGED_NATIVE_ACCELERATION_OK"


def arguments(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Load the exact _mohan_accel extension from a PyInstaller onedir "
            "package and exercise its PCM and RGBA operations."
        )
    )
    parser.add_argument("package_root", type=Path)
    parser.add_argument("--label", default="package")
    parser.add_argument("--artifact", action="append", type=Path, default=[])
    parser.add_argument("--output", type=Path)
    return parser.parse_args(argv)


def packaged_module_path(package_root: Path) -> Path:
    """Return the package's only native extension, rejecting ambiguity."""
    root = package_root.resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"Packaged application directory not found: {root}")
    candidates = tuple(sorted(root.rglob("_mohan_accel*.pyd")))
    if len(candidates) != 1:
        raise RuntimeError(
            "Expected exactly one packaged _mohan_accel extension; "
            f"found {len(candidates)}."
        )
    return candidates[0]


def packaged_abi3t_dll_path(package_root: Path) -> Path:
    """Return the package's required Python 3.15 abi3t compatibility DLL."""
    root = package_root.resolve()
    candidates = tuple(sorted(root.rglob("python3t.dll")))
    if len(candidates) != 1:
        raise RuntimeError(
            "Expected exactly one packaged python3t.dll; "
            f"found {len(candidates)}."
        )
    return candidates[0]


def packaged_build_evidence_path(package_root: Path) -> Path:
    """Return the package's one immutable native build-evidence document."""
    root = package_root.resolve()
    candidates = tuple(sorted(root.rglob("mohan-native-build-evidence.json")))
    if len(candidates) != 1:
        raise RuntimeError(
            "Expected exactly one packaged native build-evidence file; "
            f"found {len(candidates)}."
        )
    return candidates[0]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _object(value: object, context: str) -> dict[str, object]:
    if not isinstance(value, dict) or not all(
        isinstance(key, str) for key in value
    ):
        raise RuntimeError(f"{context} must be an object.")
    return value


def _digest(value: object, context: str) -> str:
    if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise RuntimeError(f"{context} must be a lowercase SHA-256 digest.")
    return value


def load_build_evidence(path: Path) -> dict[str, object]:
    """Validate the embedded build record before trusting its hashes."""
    document = _object(
        json.loads(path.read_text(encoding="utf-8")),
        "native build evidence",
    )
    if document.get("schema") != "mohan.native-acceleration.v2":
        raise RuntimeError("Packaged native build-evidence schema is unsupported.")
    if document.get("status") != "pass":
        raise RuntimeError("Packaged native build evidence did not pass.")
    _digest(document.get("wheel_sha256"), "wheel_sha256")
    _digest(document.get("wheel_module_sha256"), "wheel_module_sha256")
    dll = _object(
        document.get("abi3t_compatibility_dll"),
        "abi3t_compatibility_dll",
    )
    if dll.get("name") != "python3t.dll":
        raise RuntimeError("Native build evidence names an unexpected abi3t DLL.")
    _digest(dll.get("sha256"), "abi3t_compatibility_dll.sha256")
    return document


def verify_packaged_files(
    module_path: Path,
    compatibility_dll: Path,
    build: dict[str, object],
) -> dict[str, dict[str, object]]:
    """Bind packaged binary hashes to the embedded wheel build record."""
    module_digest = _sha256(module_path)
    if module_digest != build["wheel_module_sha256"]:
        raise RuntimeError("Packaged native module hash differs from its wheel.")
    dll_evidence = _object(
        build["abi3t_compatibility_dll"],
        "abi3t_compatibility_dll",
    )
    dll_digest = _sha256(compatibility_dll)
    if dll_digest != dll_evidence["sha256"]:
        raise RuntimeError("Packaged python3t.dll hash differs from build evidence.")
    return {
        "abi3t_compatibility_dll": {
            "name": compatibility_dll.name,
            "sha256": dll_digest,
            "size": compatibility_dll.stat().st_size,
        },
        "module": {
            "name": module_path.name,
            "sha256": module_digest,
            "size": module_path.stat().st_size,
        },
    }


def artifact_evidence(paths: Sequence[Path]) -> list[dict[str, object]]:
    """Return path-free hashes for exact distributed package inputs."""
    artifacts: list[dict[str, object]] = []
    names: set[str] = set()
    for raw_path in paths:
        path = raw_path.resolve()
        if not path.is_file():
            raise FileNotFoundError(f"Release artifact not found: {path.name}")
        if path.name in names:
            raise RuntimeError(f"Duplicate release artifact name: {path.name}")
        names.add(path.name)
        artifacts.append(
            {
                "name": path.name,
                "sha256": _sha256(path),
                "size": path.stat().st_size,
            }
        )
    return sorted(artifacts, key=lambda item: str(item["name"]))


def load_exact_extension(
    path: Path,
    dependency_directories: Sequence[Path] = (),
) -> ModuleType:
    """Load the selected package file without consulting site-packages."""
    previous = sys.modules.pop("_mohan_accel", None)
    dll_directories = []
    try:
        if hasattr(os, "add_dll_directory"):
            dll_directories.extend(
                os.add_dll_directory(str(directory))
                for directory in dict.fromkeys(
                    (path.parent, *dependency_directories)
                )
            )
        specification = spec_from_file_location("_mohan_accel", path)
        if specification is None or specification.loader is None:
            raise ImportError(f"Cannot create an extension loader for {path}.")
        module = module_from_spec(specification)
        sys.modules["_mohan_accel"] = module
        specification.loader.exec_module(module)
    except BaseException:
        sys.modules.pop("_mohan_accel", None)
        if previous is not None:
            sys.modules["_mohan_accel"] = previous
        raise
    finally:
        for dll_directory in reversed(dll_directories):
            dll_directory.close()
    return module


def verify_operations(module: ModuleType) -> None:
    """Exercise one byte-exact PCM and one byte-exact RGBA operation."""
    if module.__version__ != EXPECTED_MODULE_VERSION:
        raise RuntimeError(
            f"Expected _mohan_accel {EXPECTED_MODULE_VERSION}; "
            f"found {module.__version__}."
        )
    if module.scale_pcm16(bytes.fromhex("e80318fc"), 0.5) != bytes.fromhex(
        "f4010cfe"
    ):
        raise RuntimeError("Packaged native PCM operation returned unexpected bytes.")
    actual_rgba = module.alpha_over_rgba(
        bytes((20, 40, 60, 80)),
        bytes((200, 100, 50, 128)),
    )
    if actual_rgba != bytes((110, 70, 54, 167)):
        raise RuntimeError("Packaged native RGBA operation returned unexpected bytes.")


def main(argv: Sequence[str] | None = None) -> int:
    args = arguments(argv)
    package_root = args.package_root
    module_path = packaged_module_path(package_root)
    compatibility_dll = packaged_abi3t_dll_path(package_root)
    build = load_build_evidence(packaged_build_evidence_path(package_root))
    native_files = verify_packaged_files(
        module_path,
        compatibility_dll,
        build,
    )
    verify_operations(
        load_exact_extension(module_path, (compatibility_dll.parent,))
    )
    if args.output is not None:
        document = {
            "artifacts": artifact_evidence(args.artifact),
            "build": build,
            "label": args.label,
            "native_files": native_files,
            "operations": ["pcm16", "rgba"],
            "schema": "mohan.packaged-native-verification.v1",
            "status": "pass",
        }
        output = args.output.resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True)
            + "\n",
            encoding="utf-8",
        )
    print(f"{SUCCESS_MARKER}={module_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
