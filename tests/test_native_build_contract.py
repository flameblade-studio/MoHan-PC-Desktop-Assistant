from __future__ import annotations

lazy import sys
lazy import zipfile
lazy from pathlib import Path

lazy import pytest

lazy from tools import build_native_acceleration


def _wheel(path: Path, *tags: str) -> Path:
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(
            "mohan_accel-0.1.0.dist-info/WHEEL",
            "Wheel-Version: 1.0\n" + "".join(f"Tag: {tag}\n" for tag in tags),
        )
        archive.writestr("_mohan_accel/_mohan_accel.pyd", b"native-extension")
    return path


def test_native_build_tools_are_exactly_pinned() -> None:
    assert build_native_acceleration.PINNED_RUST_VERSION == "1.97.1"
    assert build_native_acceleration.PINNED_MATURIN_VERSION == "1.14.1"
    assert build_native_acceleration.EXPECTED_MODULE_VERSION == "0.1.0"
    manifest = build_native_acceleration.CARGO_MANIFEST.read_text(encoding="utf-8")
    assert 'rust-version = "1.97.1"' in manifest


def test_maturin_command_is_release_locked_and_targets_abi_feature(
    tmp_path: Path,
) -> None:
    command = build_native_acceleration.maturin_command(tmp_path)
    assert command[:4] == (sys.executable, "-m", "maturin", "build")
    assert "--release" in command
    assert "--locked" in command
    assert command[command.index("--features") + 1] == "extension-module"
    assert command[command.index("--interpreter") + 1] == sys.executable


def test_wheel_validation_requires_python315_stable_abi(tmp_path: Path) -> None:
    valid = _wheel(
        tmp_path / "valid.whl",
        "cp315-abi3-win_amd64",
        "cp315-abi3t-win_amd64",
    )
    assert build_native_acceleration.validate_wheel(valid) == (
        "cp315-abi3-win_amd64",
        "cp315-abi3t-win_amd64",
    )

    invalid = _wheel(tmp_path / "invalid.whl", "cp315-cp315-win_amd64")
    with pytest.raises(RuntimeError, match="abi3t"):
        build_native_acceleration.validate_wheel(invalid)

    unexpected = _wheel(
        tmp_path / "unexpected.whl",
        "cp315-abi3t-win_amd64",
        "cp315-cp315-win_amd64",
    )
    with pytest.raises(RuntimeError, match="only add"):
        build_native_acceleration.validate_wheel(unexpected)

    wrong_interpreter = _wheel(
        tmp_path / "wrong-interpreter.whl",
        "cp316-abi3t-win_amd64",
    )
    with pytest.raises(RuntimeError, match="Python 3.15"):
        build_native_acceleration.validate_wheel(wrong_interpreter)

    platform_neutral = _wheel(
        tmp_path / "platform-neutral.whl",
        "cp315-abi3t-any",
    )
    with pytest.raises(RuntimeError, match="platform-specific"):
        build_native_acceleration.validate_wheel(platform_neutral)


def test_wheel_validation_rejects_ambiguous_metadata(tmp_path: Path) -> None:
    path = tmp_path / "ambiguous.whl"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("one.dist-info/WHEEL", "Tag: cp315-abi3t-win_amd64\n")
        archive.writestr("two.dist-info/WHEEL", "Tag: cp315-abi3t-win_amd64\n")
    with pytest.raises(RuntimeError, match="exactly one"):
        build_native_acceleration.wheel_tags(path)


def test_wheel_evidence_hashes_the_exact_native_member(tmp_path: Path) -> None:
    wheel = _wheel(tmp_path / "native.whl", "cp315-abi3t-win_amd64")
    member = build_native_acceleration.wheel_native_extension(wheel)
    assert member.path == "_mohan_accel/_mohan_accel.pyd"
    assert member.size == len(b"native-extension")
    assert len(member.sha256) == 64
