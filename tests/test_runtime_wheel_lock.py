from __future__ import annotations

lazy import re
lazy import sys
lazy from pathlib import Path

lazy import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

lazy from tools.lock_runtime_requirements import (
    DEFAULT_LOCK,
    DEFAULT_REQUIREMENTS,
    RuntimeLockError,
    check_lock,
    direct_pins,
    locked_entries,
)

DIGEST = "a" * 64
RUNTIME_INSTALL = re.compile(
    r"-m pip install --only-binary=:all:\s+(?P<options>(?:--\S+\s+)*)-r (?P<file>\S+)"
)


def test_repository_lock_covers_every_direct_pin():
    check_lock(DEFAULT_REQUIREMENTS, DEFAULT_LOCK)
    assert len(locked_entries(DEFAULT_LOCK)) > len(direct_pins(DEFAULT_REQUIREMENTS)), (
        "the lock must hold the transitive closure, not only direct pins"
    )


@pytest.mark.parametrize("workflow_name", ["release.yml", "windows-ci.yml"])
def test_packaging_workflows_install_runtime_only_by_hash(workflow_name: str):
    workflow = (ROOT / ".github" / "workflows" / workflow_name).read_text(encoding="utf-8")
    installs = [
        (match["file"], match["options"].split())
        for match in RUNTIME_INSTALL.finditer(workflow)
        if match["file"].startswith("requirements") and match["file"] != "requirements-dev.txt"
    ]
    assert installs, f"{workflow_name} has no runtime dependency install"
    for requirement_file, options in installs:
        assert requirement_file != "requirements.txt", workflow_name
        if requirement_file in {"requirements-qt.txt", "requirements-windows-lock.txt"}:
            assert "--require-hashes" in options, (workflow_name, requirement_file)
    assert "requirements-windows-lock.txt" in {name for name, _ in installs}


def test_security_audit_covers_the_locked_closure():
    workflow = (ROOT / ".github" / "workflows" / "security-audit.yml").read_text(encoding="utf-8")
    assert "pip_audit -r requirements-windows-lock.txt --strict --no-deps --disable-pip" in workflow


def _write(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


def test_check_rejects_version_drift(tmp_path: Path):
    requirements = _write(tmp_path / "requirements.txt", "certifi==2026.10.19\n")
    lock = _write(tmp_path / "lock.txt", f"certifi==2026.9.1 \\\n    --hash=sha256:{DIGEST}\n")
    with pytest.raises(RuntimeLockError, match="pins 2026.10.19"):
        check_lock(requirements, lock)


def test_check_rejects_missing_direct_pin(tmp_path: Path):
    requirements = _write(tmp_path / "requirements.txt", "certifi==2026.10.19\nnumpy==2.5.2\n")
    lock = _write(tmp_path / "lock.txt", f"certifi==2026.10.19 \\\n    --hash=sha256:{DIGEST}\n")
    with pytest.raises(RuntimeLockError, match="numpy==2.5.2"):
        check_lock(requirements, lock)


def test_check_rejects_unhashed_entry(tmp_path: Path):
    requirements = _write(tmp_path / "requirements.txt", "certifi==2026.10.19\n")
    lock = _write(tmp_path / "lock.txt", "certifi==2026.10.19\n")
    with pytest.raises(RuntimeLockError, match="no sha256 hash"):
        check_lock(requirements, lock)


def test_check_rejects_duplicated_qt_wheels(tmp_path: Path):
    requirements = _write(tmp_path / "requirements.txt", "PySide6_Essentials==6.12.0\n")
    lock = _write(tmp_path / "lock.txt", f"pyside6-essentials==6.12.0 \\\n    --hash=sha256:{DIGEST}\n")
    with pytest.raises(RuntimeLockError, match="must not duplicate Qt"):
        check_lock(requirements, lock)


def test_check_rejects_non_exact_direct_pin(tmp_path: Path):
    requirements = _write(tmp_path / "requirements.txt", "certifi>=2026\n")
    lock = _write(tmp_path / "lock.txt", f"certifi==2026.10.19 \\\n    --hash=sha256:{DIGEST}\n")
    with pytest.raises(RuntimeLockError, match="non-exact pin"):
        check_lock(requirements, lock)
