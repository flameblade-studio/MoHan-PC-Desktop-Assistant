from __future__ import annotations

lazy from pathlib import Path

lazy import pytest

lazy from tools import check_python_licenses as license_gate

EXPECTED_DUPLICATE_RECORDS = 2


class FakeDistribution:
    def __init__(
        self,
        name: str,
        version: str,
        requires: list[str] | None = None,
        location: str = ".",
    ) -> None:
        self.metadata = {"Name": name}
        self.version = version
        self.requires = requires or []
        self.location = location

    def locate_file(self, path: str) -> str:
        return self.location


def _policy() -> dict[str, object]:
    return {
        "schema": 1,
        "allowed_licenses": [
            "Apache-2.0",
            "BSD",
            "BSD-2-Clause",
            "BSD-3-Clause",
            "ISC",
            "MIT",
            "MPL-2.0",
            "PSF",
        ],
        "quality_tools": {"deptry": {"version": "0.25.1", "license": "MIT"}},
    }


def test_license_normalization_accepts_the_declared_allowlist() -> None:
    assert license_gate.normalize_license_expression("MIT License") == ("MIT",)
    assert license_gate.normalize_license_expression("Apache Software License") == (
        "Apache-2.0",
    )
    assert license_gate.normalize_license_expression("BSD License") == ("BSD",)
    assert license_gate.normalize_license_expression(
        "Mozilla Public License 2.0 (MPL 2.0)"
    ) == ("MPL-2.0",)
    assert license_gate.normalize_license_expression("PSF-2.0") == ("PSF",)
    assert license_gate.normalize_license_expression(
        "MIT AND Python Software Foundation License"
    ) == ("MIT", "PSF")


def test_license_normalization_keeps_unknown_and_forbidden_licenses_visible() -> None:
    assert license_gate.normalize_license_expression("GPL-3.0-only") == (
        "UNRECOGNIZED:gpl-3.0-only",
    )
    assert license_gate.normalize_license_expression("MIT OR GPL-3.0-only") == (
        "MIT",
        "UNRECOGNIZED:gpl-3.0-only",
    )


def test_quality_tool_transitive_dependencies_are_checked(monkeypatch: pytest.MonkeyPatch) -> None:
    installed = {
        "deptry": FakeDistribution("deptry", "0.25.1", ["parser>=1"]),
        "parser": FakeDistribution("parser", "1.0"),
    }
    license_rows = [
        {"name": "deptry", "version": "0.25.1", "license": "MIT License"},
        {"name": "parser", "version": "1.0", "license": "GPL-3.0-only"},
    ]
    monkeypatch.setattr(license_gate, "_runtime_sbom_components", dict)

    report = license_gate.build_report(_policy(), installed, license_rows)

    assert any(
        "parser" in issue and "non-allow-listed" in issue
        for issue in report["issues"]
    )


def test_quality_tool_roots_must_match_the_pinned_version() -> None:
    installed = {"deptry": FakeDistribution("deptry", "0.25.0")}
    license_rows = [{"name": "deptry", "version": "0.25.0", "license": "MIT"}]

    report = license_gate.build_report(_policy(), installed, license_rows)

    assert any("does not match pinned version" in issue for issue in report["issues"])


def test_runtime_mpl_component_can_use_its_existing_release_record(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    installed = {
        "deptry": FakeDistribution("deptry", "0.25.1", ["certifi>=1"]),
        "certifi": FakeDistribution("certifi", "2026.7.22"),
    }
    license_rows = [
        {"name": "deptry", "version": "0.25.1", "license": "MIT"},
        {"name": "certifi", "version": "2026.7.22", "license": "MPL-2.0"},
    ]
    monkeypatch.setattr(
        license_gate,
        "_runtime_sbom_components",
        lambda: {
            "certifi": {
                "name": "certifi",
                "version": "2026.7.22",
                "license": "MPL-2.0",
            }
        },
    )

    report = license_gate.build_report(_policy(), installed, license_rows)

    certifi = next(
        package
        for package in report["checked_quality_tool_dependency_closure"]
        if package["name"] == "certifi"
    )
    assert certifi["existing_runtime_component"] is True
    assert report["issues"] == []


def test_license_inventory_preserves_system_duplicates_for_version_matching() -> None:
    duplicate_rows = [
        {"Name": "Deptry", "Version": "0.25.1", "License": "MIT"},
        {"Name": "deptry", "Version": "0.25.1", "License": "MIT"},
    ]

    assert (
        len(license_gate._validated_license_records(duplicate_rows))
        == EXPECTED_DUPLICATE_RECORDS
    )


def test_installed_distributions_prefer_active_environment_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prefix = Path.cwd() / ".venv315"
    active = FakeDistribution(
        "PySide6", "6.10.2", location=str(prefix / "Lib/site-packages")
    )
    system = FakeDistribution(
        "PySide6", "6.9.3", location=str(prefix.parent / "system/Lib/site-packages")
    )
    monkeypatch.setattr(license_gate.sys, "prefix", str(prefix))
    monkeypatch.setattr(
        license_gate.metadata,
        "distributions",
        lambda: [system, active],
    )

    assert license_gate._installed_distributions()["pyside6"] is active
