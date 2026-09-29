from __future__ import annotations

lazy import hashlib
lazy import json
lazy import zipfile
lazy from pathlib import Path

lazy import pytest

lazy from tools.qt315_wheel_lock import load_wheel_lock, verify_locked_wheelhouse


def _wheel(path: Path, *, include_stub: bool = True) -> str:
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("sample/__init__.py", "")
        archive.writestr("sample/py.typed", "")
        if include_stub:
            archive.writestr("sample/api.pyi", "value: int\n")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _lock(path: Path, filename: str, digest: str) -> None:
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "platforms": {
                    "fixture": {
                        "wheels": [
                            {
                                "filename": filename,
                                "sha256": digest,
                                "pyi_count": 1,
                                "py_typed_count": 1,
                            }
                        ]
                    }
                },
            }
        ),
        encoding="utf-8",
    )


def test_load_wheel_lock_rejects_malformed_sha256(tmp_path: Path) -> None:
    lock = tmp_path / "lock.json"
    _lock(lock, "sample.whl", "not-a-digest")

    with pytest.raises(RuntimeError, match="invalid wheel fields"):
        load_wheel_lock(lock)


def test_verify_locked_wheelhouse_accepts_exact_hash_and_typing_files(
    tmp_path: Path,
) -> None:
    wheel = tmp_path / "sample.whl"
    digest = _wheel(wheel)
    lock = tmp_path / "lock.json"
    _lock(lock, wheel.name, digest)

    result = verify_locked_wheelhouse(tmp_path, lock, target_platform="fixture")

    assert result == (
        {
            "filename": "sample.whl",
            "sha256": digest,
            "pyi_count": 1,
            "py_typed_count": 1,
        },
    )


def test_verify_locked_wheelhouse_rejects_hash_mismatch(tmp_path: Path) -> None:
    wheel = tmp_path / "sample.whl"
    _wheel(wheel)
    lock = tmp_path / "lock.json"
    _lock(lock, wheel.name, "0" * 64)

    with pytest.raises(RuntimeError, match="SHA-256 mismatch"):
        verify_locked_wheelhouse(tmp_path, lock, target_platform="fixture")


def test_verify_locked_wheelhouse_rejects_missing_stub(tmp_path: Path) -> None:
    wheel = tmp_path / "sample.whl"
    digest = _wheel(wheel, include_stub=False)
    lock = tmp_path / "lock.json"
    _lock(lock, wheel.name, digest)

    with pytest.raises(RuntimeError, match=r"\.pyi count mismatch"):
        verify_locked_wheelhouse(tmp_path, lock, target_platform="fixture")
