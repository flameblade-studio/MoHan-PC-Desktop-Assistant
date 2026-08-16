from __future__ import annotations

lazy import tempfile
lazy from pathlib import Path

lazy import pytest

lazy from tools.verify_packaged_native_acceleration import (
    packaged_abi3t_dll_path,
    packaged_build_evidence_path,
    packaged_module_path,
)


def test_packaged_module_path_requires_one_exact_extension() -> None:
    with tempfile.TemporaryDirectory(prefix="mohan-native-package-") as raw:
        root = Path(raw)
        with pytest.raises(RuntimeError, match="found 0"):
            packaged_module_path(root)

        extension = root / "_internal" / "_mohan_accel.cp315-win_amd64.pyd"
        extension.parent.mkdir()
        extension.touch()
        assert packaged_module_path(root) == extension.resolve()

        second = root / "_mohan_accel.pyd"
        second.touch()
        with pytest.raises(RuntimeError, match="found 2"):
            packaged_module_path(root)


def test_packaged_abi3t_dll_path_requires_one_exact_file() -> None:
    with tempfile.TemporaryDirectory(prefix="mohan-abi3t-package-") as raw:
        root = Path(raw)
        with pytest.raises(RuntimeError, match="found 0"):
            packaged_abi3t_dll_path(root)
        compatibility_dll = root / "_internal" / "python3t.dll"
        compatibility_dll.parent.mkdir()
        compatibility_dll.touch()
        assert packaged_abi3t_dll_path(root) == compatibility_dll.resolve()


def test_packaged_build_evidence_requires_one_exact_file() -> None:
    with tempfile.TemporaryDirectory(prefix="mohan-native-evidence-") as raw:
        root = Path(raw)
        with pytest.raises(RuntimeError, match="found 0"):
            packaged_build_evidence_path(root)
        evidence = root / "_internal" / "mohan-native-build-evidence.json"
        evidence.parent.mkdir()
        evidence.write_text("{}", encoding="utf-8")
        assert packaged_build_evidence_path(root) == evidence.resolve()


def main() -> None:
    test_packaged_module_path_requires_one_exact_extension()
    test_packaged_abi3t_dll_path_requires_one_exact_file()
    test_packaged_build_evidence_requires_one_exact_file()
    print("PACKAGED_NATIVE_VERIFIER_TESTS_OK")


if __name__ == "__main__":
    main()
