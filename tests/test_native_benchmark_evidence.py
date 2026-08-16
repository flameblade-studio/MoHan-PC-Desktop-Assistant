from __future__ import annotations

lazy import hashlib
lazy import json
lazy import zipfile
lazy from pathlib import Path
lazy from types import ModuleType

lazy import pytest

lazy from domain import lip_sync
lazy from tools.benchmark_native_integrated import (
    NATIVE_WHEEL_MEMBER,
    _native_provenance,
    _schedule_50hz_evidence,
    _validate_safe_evidence,
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _native_modules(
    root: Path,
    binary: bytes,
) -> tuple[ModuleType, ModuleType]:
    package_directory = root / "site-packages" / "_mohan_accel"
    package_directory.mkdir(parents=True)
    package_file = package_directory / "__init__.py"
    package_file.write_text("", encoding="utf-8")
    extension_file = package_directory / "_mohan_accel.pyd"
    extension_file.write_bytes(binary)

    package = ModuleType("_mohan_accel")
    package.__file__ = str(package_file)
    package.__version__ = "0.1.0"
    extension = ModuleType("_mohan_accel._mohan_accel")
    extension.__file__ = str(extension_file)
    return package, extension


def _validation_wheel(root: Path, binary: bytes) -> Path:
    wheel = root / "mohan_accel-0.1.0-cp315-abi3.abi3t-win_amd64.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr(NATIVE_WHEEL_MEMBER, binary)
    return wheel


def test_provenance_binds_loaded_binary_to_validation_wheel(
    tmp_path: Path,
) -> None:
    binary = b"same native binary"
    package, extension = _native_modules(tmp_path, binary)
    wheel = _validation_wheel(tmp_path, binary)

    evidence = _native_provenance(
        package,
        validation_wheel=wheel,
        expected_wheel_sha256=_sha256(wheel),
        extension_module=extension,
    )

    loaded = evidence["loaded_native_binary"]
    validation = evidence["validation_wheel"]
    assert loaded["path"] == NATIVE_WHEEL_MEMBER
    assert loaded["sha256"] == hashlib.sha256(binary).hexdigest()
    assert validation["filename"] == wheel.name
    assert validation["native_binary_matches_loaded"] is True
    assert str(tmp_path) not in json.dumps(evidence)
    _validate_safe_evidence(evidence)


def test_provenance_rejects_cli_wheel_hash_drift(tmp_path: Path) -> None:
    binary = b"same native binary"
    package, extension = _native_modules(tmp_path, binary)
    wheel = _validation_wheel(tmp_path, binary)

    with pytest.raises(RuntimeError, match="CLI value"):
        _native_provenance(
            package,
            validation_wheel=wheel,
            expected_wheel_sha256="0" * 64,
            extension_module=extension,
        )


def test_provenance_rejects_loaded_binary_drift(tmp_path: Path) -> None:
    package, extension = _native_modules(tmp_path, b"loaded binary")
    wheel = _validation_wheel(tmp_path, b"wheel binary")

    with pytest.raises(RuntimeError, match="does not match the validation wheel"):
        _native_provenance(
            package,
            validation_wheel=wheel,
            expected_wheel_sha256=_sha256(wheel),
            extension_module=extension,
        )


def test_50hz_schedule_is_descriptive_and_not_a_hard_realtime_claim() -> None:
    native = ModuleType("_mohan_accel")
    native.infer_vowel_pcm16 = lip_sync.infer_vowel_pcm16

    evidence = _schedule_50hz_evidence(native, tick_count=2)

    assert evidence["completed"] is True
    assert evidence["requested_rate_hz"] == 50
    assert evidence["target_interval_ms"] == 20.0
    assert evidence["tick_count"] == 2
    assert evidence["hard_realtime_claimed"] is False
    assert evidence["observed_intervals_ms"]["samples"] == 1
