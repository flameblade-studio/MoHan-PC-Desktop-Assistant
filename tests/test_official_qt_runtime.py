from __future__ import annotations

lazy import json
lazy import sys
lazy from pathlib import Path

lazy import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

lazy from tools.check_official_qt_runtime import (
    DEFAULT_HASH_REQUIREMENTS,
    DEFAULT_LOCK,
    EXPECTED_WHEEL_COUNT,
    QT_CANONICAL_NAMES,
    QT_VERSION,
    hashed_requirements_text,
    inspect_installed_runtime,
    inspect_pip_report,
    load_official_wheel_lock,
    main,
    pinned_pyside_version,
    validate_hashed_requirements,
)


def _one_platform_report(lock: dict[str, object]) -> dict[str, object]:
    wheels = lock["wheels"]
    assert isinstance(wheels, list)
    selected: dict[str, dict[str, object]] = {}
    for entry in wheels:
        assert isinstance(entry, dict)
        filename = str(entry["filename"])
        if not filename.endswith("-win_amd64.whl"):
            continue
        name = filename.partition("-")[0].replace("_", "-")
        selected[name] = entry
    return {
        "version": "1",
        "install": [
            {
                "download_info": {
                    "url": f"https://files.pythonhosted.org/packages/{entry['filename']}",
                    "archive_info": {"hashes": {"sha256": entry["sha256"]}},
                },
                "metadata": {"name": name, "version": QT_VERSION},
            }
            for name, entry in selected.items()
        ],
    }


def test_official_lock_covers_every_supplied_wheel() -> None:
    lock = load_official_wheel_lock()
    wheels = lock["wheels"]
    assert isinstance(wheels, list)
    assert len(wheels) == EXPECTED_WHEEL_COUNT
    names = {
        str(entry["filename"]).partition("-")[0].replace("_", "-")
        for entry in wheels
        if isinstance(entry, dict)
    }
    assert names == QT_CANONICAL_NAMES
    validate_hashed_requirements(DEFAULT_HASH_REQUIREMENTS, lock)
    assert DEFAULT_HASH_REQUIREMENTS.read_text(encoding="utf-8") == (
        hashed_requirements_text(lock)
    )


def test_hash_requirements_fail_closed_on_drift(tmp_path: Path) -> None:
    lock = load_official_wheel_lock()
    requirements = tmp_path / "requirements-qt.txt"
    requirements.write_text(
        hashed_requirements_text(lock).replace("efea4c2f", "0fea4c2f", 1),
        encoding="utf-8",
    )
    with pytest.raises(RuntimeError, match="do not match"):
        validate_hashed_requirements(requirements, lock)


def test_pip_report_requires_locked_hashes_for_all_four_distributions(
    tmp_path: Path,
) -> None:
    lock = load_official_wheel_lock()
    report = _one_platform_report(lock)
    path = tmp_path / "report.json"
    path.write_text(json.dumps(report), encoding="utf-8")
    assert inspect_pip_report(path, lock) == ()

    installs = report["install"]
    assert isinstance(installs, list)
    first = installs[0]
    assert isinstance(first, dict)
    download_info = first["download_info"]
    assert isinstance(download_info, dict)
    archive_info = download_info["archive_info"]
    assert isinstance(archive_info, dict)
    archive_info["hashes"] = {"sha256": "0" * 64}
    path.write_text(json.dumps(report), encoding="utf-8")
    assert any("SHA-256 mismatch" in issue for issue in inspect_pip_report(path, lock))


def test_invalid_report_stops_before_runtime_import(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    lock = load_official_wheel_lock()
    report = _one_platform_report(lock)
    installs = report["install"]
    assert isinstance(installs, list)
    first = installs[0]
    assert isinstance(first, dict)
    download_info = first["download_info"]
    assert isinstance(download_info, dict)
    archive_info = download_info["archive_info"]
    assert isinstance(archive_info, dict)
    archive_info["hashes"] = {"sha256": "0" * 64}
    path = tmp_path / "bad-report.json"
    path.write_text(json.dumps(report), encoding="utf-8")

    def unexpected_runtime_inspection() -> tuple[str, ...]:
        raise AssertionError("invalid provenance reached the PySide6 runtime")

    monkeypatch.setattr(
        "tools.check_official_qt_runtime.inspect_installed_runtime",
        unexpected_runtime_inspection,
    )
    assert main(["--pip-report", str(path)]) == 1
    assert "SHA-256 mismatch" in capsys.readouterr().out


def test_requirements_must_pin_official_release(tmp_path: Path) -> None:
    requirements = tmp_path / "requirements.txt"
    requirements.write_text(f"PySide6=={QT_VERSION}\n", encoding="utf-8")
    assert pinned_pyside_version(requirements) == QT_VERSION
    requirements.write_text("PySide6==6.11.1\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match=QT_VERSION):
        pinned_pyside_version(requirements)


def test_ci_runtime_uses_supported_official_wheels() -> None:
    assert DEFAULT_LOCK.is_file()
    assert inspect_installed_runtime() == ()
