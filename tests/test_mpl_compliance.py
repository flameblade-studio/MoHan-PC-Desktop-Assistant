"""Regression tests for the fail-closed MPL evidence boundary."""

from __future__ import annotations

lazy import builtins
lazy from collections.abc import Callable
lazy import copy
lazy from dataclasses import dataclass
lazy import hashlib
lazy import json
lazy from pathlib import Path
lazy from urllib import request
lazy import warnings
lazy from unittest.mock import Mock
lazy from zipfile import ZipFile

lazy import pytest

lazy from tools.mpl_compliance import (
    MANIFEST,
    SCHEMA,
    verify_environment,
    verify_evidence,
    verify_policy,
)


MPL_LICENSE = (
    Path(__file__).resolve().parents[1]
    / "third_party_licenses/mpl/MPL-2.0.txt"
).read_bytes()


@dataclass
class EvidenceFixture:
    root: Path
    site_packages: Path
    manifest: dict[str, object]
    source_files: dict[str, bytes]


def _sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _write_artifact(root: Path, relative: str, payload: bytes) -> dict[str, str]:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return {"path": relative, "sha256": _sha(payload)}


def _save_manifest(fixture: EvidenceFixture) -> None:
    path = fixture.root / MANIFEST
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(fixture.manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _component(fixture: EvidenceFixture) -> dict[str, object]:
    components = fixture.manifest["components"]
    assert isinstance(components, list)
    component = components[0]
    assert isinstance(component, dict)
    return component


def _archive_path(fixture: EvidenceFixture) -> Path:
    source_archive = _component(fixture)["source_archive"]
    assert isinstance(source_archive, dict)
    relative = source_archive["path"]
    assert isinstance(relative, str)
    return fixture.root / relative


def _rewrite_archive(fixture: EvidenceFixture, entries: dict[str, bytes]) -> None:
    path = _archive_path(fixture)
    with ZipFile(path, "w") as archive:
        for name, payload in entries.items():
            archive.writestr(name, payload)
    source_archive = _component(fixture)["source_archive"]
    assert isinstance(source_archive, dict)
    source_archive["sha256"] = _sha(path.read_bytes())
    _save_manifest(fixture)


def _metadata_path(fixture: EvidenceFixture) -> Path:
    return next(fixture.site_packages.glob("*.dist-info/METADATA"))


def _make_fixture(
    tmp_path: Path,
    *,
    name: str = "certifi",
    version: str = "2026.7.22",
    expression: str = "MPL-2.0",
    source_status: str = "installed-source-snapshot",
    installed_files: dict[str, bytes] | None = None,
    install: bool = True,
) -> EvidenceFixture:
    root = tmp_path / "project"
    root.mkdir()
    notice_payload = b"Fixture notice\n"
    source_files = {
        f"{name}/__init__.py": b"VALUE = 'fixture'\n",
        f"{name}/data.pem": b"certificate-data\n",
        f"{name}/NOTICE.txt": notice_payload,
    }
    license_text = _write_artifact(
        root,
        "third_party_licenses/mpl/LICENSE.txt",
        MPL_LICENSE,
    )
    notice = _write_artifact(
        root,
        f"third_party_licenses/mpl/{name}-NOTICE.txt",
        notice_payload,
    )
    archive_relative = f"third_party_licenses/mpl/{name}-source.zip"
    archive_path = root / archive_relative
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(archive_path, "w") as archive:
        for relative, payload in source_files.items():
            archive.writestr(relative, payload)
    source_rows = [
        {"path": relative, "sha256": _sha(payload)}
        for relative, payload in source_files.items()
    ]
    component: dict[str, object] = {
        "name": name,
        "version": version,
        "license_expression": expression,
        "scope": "local-art-tooling",
        "source_archive": {
            "path": archive_relative,
            "sha256": _sha(archive_path.read_bytes()),
        },
        "notices": [notice],
        "upstream_url": f"https://example.invalid/{name}",
        "source_status": source_status,
        "source_files": source_rows,
    }
    metadata_relative = f"{name}-{version}.dist-info/METADATA"
    metadata_payload = (
        "Metadata-Version: 2.4\n"
        f"Name: {name}\n"
        f"Version: {version}\n"
        f"License-Expression: {expression}\n"
    ).encode("utf-8")
    installed_payloads = installed_files or {
        f"{name}/native.pyd": b"native-binary-fixture",
        metadata_relative: metadata_payload,
    }
    if source_status == "upstream-source-archive":
        component["installed_files"] = [
            {"path": relative, "sha256": _sha(payload)}
            for relative, payload in installed_payloads.items()
        ]
    fixture = EvidenceFixture(
        root=root,
        site_packages=tmp_path / "site-packages",
        manifest={
            "schema": SCHEMA,
            "license_text": license_text,
            "components": [component],
        },
        source_files=source_files,
    )
    fixture.site_packages.mkdir()
    if install:
        if source_status == "upstream-source-archive":
            for relative, payload in installed_payloads.items():
                _write_artifact(fixture.site_packages, relative, payload)
        else:
            for relative, payload in source_files.items():
                _write_artifact(fixture.site_packages, relative, payload)
            _write_artifact(fixture.site_packages, metadata_relative, metadata_payload)
    _save_manifest(fixture)
    return fixture


@pytest.mark.parametrize(
    "expression",
    ("MPL-2.0", "MPL-2.0 AND MIT", "MPL-2.0 AND (Apache-2.0 OR MIT)"),
)
def test_verify_evidence_accepts_supported_license_expressions(
    tmp_path: Path,
    expression: str,
) -> None:
    fixture = _make_fixture(tmp_path, expression=expression, install=False)

    assert verify_evidence(fixture.root) == []


def test_verify_environment_accepts_matching_installed_source_snapshot(
    tmp_path: Path,
) -> None:
    fixture = _make_fixture(tmp_path)

    assert verify_environment(fixture.root, fixture.site_packages) == []


def test_verify_environment_allows_uninstalled_manifest_component(
    tmp_path: Path,
) -> None:
    fixture = _make_fixture(tmp_path, install=False)

    assert verify_environment(fixture.root, fixture.site_packages) == []


def test_verify_environment_uses_installed_files_for_upstream_archive(
    tmp_path: Path,
) -> None:
    fixture = _make_fixture(
        tmp_path,
        name="nativefixture",
        version="1.0.0",
        expression="MPL-2.0 AND (Apache-2.0 OR MIT)",
        source_status="upstream-source-archive",
    )

    assert verify_environment(fixture.root, fixture.site_packages) == []


@pytest.mark.parametrize("invalid_kind", ("outside-package-root", "missing-extension"))
def test_verify_evidence_rejects_unbound_upstream_installed_files(
    tmp_path: Path,
    invalid_kind: str,
) -> None:
    fixture = _make_fixture(
        tmp_path,
        name="nativefixture",
        version="1.0.0",
        expression="MPL-2.0 AND (Apache-2.0 OR MIT)",
        source_status="upstream-source-archive",
    )
    component = _component(fixture)
    installed = component["installed_files"]
    assert isinstance(installed, list)
    if invalid_kind == "outside-package-root":
        binary = installed[0]
        assert isinstance(binary, dict)
        binary["path"] = "unrelated/native.pyd"
    else:
        installed[:] = [
            row
            for row in installed
            if isinstance(row, dict) and str(row["path"]).endswith(".dist-info/METADATA")
        ]
    _save_manifest(fixture)

    errors = verify_evidence(fixture.root)

    assert errors
    assert any("installed" in error.lower() for error in errors)


def test_verify_evidence_returns_error_for_missing_manifest(tmp_path: Path) -> None:
    root = tmp_path / "empty-project"
    root.mkdir()

    errors = verify_evidence(root)

    assert errors
    assert "components.json" in errors[0]


def test_verify_evidence_rejects_incomplete_license_text(tmp_path: Path) -> None:
    fixture = _make_fixture(tmp_path, install=False)
    record = fixture.manifest["license_text"]
    assert isinstance(record, dict)
    path = fixture.root / record["path"]
    truncated = (
        b"Mozilla Public License Version 2.0\n"
        b"Section 3.2. This body is intentionally truncated.\n"
    )
    path.write_bytes(truncated)
    record["sha256"] = _sha(path.read_bytes())
    _save_manifest(fixture)

    errors = verify_evidence(fixture.root)

    assert any('provide the full MPL license text' in error for error in errors)


def test_verify_evidence_rejects_notice_not_matching_source_archive(
    tmp_path: Path,
) -> None:
    fixture = _make_fixture(tmp_path, install=False)
    notice = _component(fixture)["notices"][0]
    assert isinstance(notice, dict)
    notice_path = fixture.root / notice["path"]
    changed_notice = b"Notice for a different package.\n"
    notice_path.write_bytes(changed_notice)
    notice["sha256"] = _sha(changed_notice)
    _save_manifest(fixture)

    errors = verify_evidence(fixture.root)

    assert any("retain the component notice" in error for error in errors)


def test_verify_evidence_rejects_missing_notice(tmp_path: Path) -> None:
    fixture = _make_fixture(tmp_path, install=False)
    notices = _component(fixture)["notices"]
    assert isinstance(notices, list)
    notice = notices[0]
    assert isinstance(notice, dict)
    (fixture.root / notice["path"]).unlink()

    errors = verify_evidence(fixture.root)

    assert errors
    assert "NOTICE" in errors[0]


def test_verify_evidence_rejects_unsupported_license_expression(
    tmp_path: Path,
) -> None:
    fixture = _make_fixture(tmp_path, install=False)
    _component(fixture)["license_expression"] = "Apache-2.0"
    _save_manifest(fixture)

    errors = verify_evidence(fixture.root)

    assert any("unreviewed MPL license expression" in error for error in errors)


@pytest.mark.parametrize(
    "unsafe_path",
    ("../escape.zip", "/absolute.zip", r"nested\\escape.zip", "C:/escape.zip"),
)
def test_verify_evidence_rejects_unsafe_artifact_paths(
    tmp_path: Path,
    unsafe_path: str,
) -> None:
    fixture = _make_fixture(tmp_path, install=False)
    source_archive = _component(fixture)["source_archive"]
    assert isinstance(source_archive, dict)
    source_archive["path"] = unsafe_path
    _save_manifest(fixture)

    errors = verify_evidence(fixture.root)

    assert errors
    assert any("evidence path" in error for error in errors)


def test_verify_evidence_rejects_duplicate_source_ledger_entries(
    tmp_path: Path,
) -> None:
    fixture = _make_fixture(tmp_path, install=False)
    source_files = _component(fixture)["source_files"]
    assert isinstance(source_files, list)
    source_files.append(copy.deepcopy(source_files[0]))
    _save_manifest(fixture)

    errors = verify_evidence(fixture.root)

    assert any("duplicate source entry" in error for error in errors)


def test_verify_evidence_rejects_archive_entry_set_mismatch(tmp_path: Path) -> None:
    fixture = _make_fixture(tmp_path, install=False)
    entries = dict(fixture.source_files)
    entries["certifi/extra.py"] = b"EXTRA = True\n"
    _rewrite_archive(fixture, entries)

    errors = verify_evidence(fixture.root)

    assert any("archive entries differ" in error for error in errors)


def test_verify_evidence_rejects_archive_content_hash_mismatch(tmp_path: Path) -> None:
    fixture = _make_fixture(tmp_path, install=False)
    entries = dict(fixture.source_files)
    entries["certifi/__init__.py"] = b"VALUE = 'changed'\n"
    _rewrite_archive(fixture, entries)

    errors = verify_evidence(fixture.root)

    assert any("archive content mismatch" in error for error in errors)


def test_verify_evidence_rejects_duplicate_zip_names(tmp_path: Path) -> None:
    fixture = _make_fixture(tmp_path, install=False)
    path = _archive_path(fixture)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        with ZipFile(path, "w") as archive:
            archive.writestr("certifi/__init__.py", fixture.source_files["certifi/__init__.py"])
            archive.writestr("certifi/__init__.py", fixture.source_files["certifi/__init__.py"])
            archive.writestr("certifi/data.pem", fixture.source_files["certifi/data.pem"])
            archive.writestr("certifi/NOTICE.txt", fixture.source_files["certifi/NOTICE.txt"])
    source_archive = _component(fixture)["source_archive"]
    assert isinstance(source_archive, dict)
    source_archive["sha256"] = _sha(path.read_bytes())
    _save_manifest(fixture)

    errors = verify_evidence(fixture.root)

    assert any("archive entries differ" in error for error in errors)


def test_verify_evidence_rejects_corrupt_source_archive(tmp_path: Path) -> None:
    fixture = _make_fixture(tmp_path, install=False)
    path = _archive_path(fixture)
    path.write_bytes(b"not a zip archive")
    source_archive = _component(fixture)["source_archive"]
    assert isinstance(source_archive, dict)
    source_archive["sha256"] = _sha(path.read_bytes())
    _save_manifest(fixture)

    errors = verify_evidence(fixture.root)

    assert any("File is not a zip file" in error for error in errors)


def test_verify_evidence_rejects_duplicate_component_version(tmp_path: Path) -> None:
    fixture = _make_fixture(tmp_path, install=False)
    components = fixture.manifest["components"]
    assert isinstance(components, list)
    components.append(copy.deepcopy(components[0]))
    _save_manifest(fixture)

    errors = verify_evidence(fixture.root)

    assert any("duplicate MPL component version" in error for error in errors)


@pytest.mark.parametrize(
    ("components", "message"),
    (([], "MPL components must be nonempty"), ([None], "component must be an object")),
)
def test_verify_evidence_rejects_empty_or_malformed_components(
    tmp_path: Path,
    components: list[object],
    message: str,
) -> None:
    fixture = _make_fixture(tmp_path, install=False)
    fixture.manifest["components"] = components
    _save_manifest(fixture)

    errors = verify_evidence(fixture.root)

    assert any(message in error for error in errors)


def test_verify_evidence_rejects_snapshot_without_python_source(tmp_path: Path) -> None:
    fixture = _make_fixture(tmp_path, install=False)
    source_files = _component(fixture)["source_files"]
    assert isinstance(source_files, list)
    source_files[:] = [row for row in source_files if not row["path"].endswith(".py")]
    _rewrite_archive(
        fixture,
        {
            relative: payload
            for relative, payload in fixture.source_files.items()
            if not relative.endswith(".py")
        },
    )

    errors = verify_evidence(fixture.root)

    assert any("source" in error.lower() for error in errors)


def test_verify_evidence_does_not_extract_or_fetch_sources(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _make_fixture(tmp_path, install=False)

    def fail(*args: object, **kwargs: object) -> None:
        raise AssertionError('source verification must inspect existing archive data in place')

    monkeypatch.setattr(ZipFile, "extract", fail)
    monkeypatch.setattr(request, "urlopen", fail)

    assert verify_evidence(fixture.root) == []


def _mock_packaging_preflight(
    root: Path,
    site_packages: Path,
    runner: Mock,
    *,
    policy_checker: Callable[[Path], list[str]],
) -> None:
    errors = list(policy_checker(root))
    errors.extend(verify_environment(root, site_packages))
    if errors:
        raise RuntimeError('MPL compliance requires correction: ' + "; ".join(errors))
    runner()


def test_mock_packaging_preflight_stops_on_missing_evidence(
    tmp_path: Path,
) -> None:
    root = tmp_path / "missing-evidence"
    root.mkdir()
    site_packages = tmp_path / "site-packages"
    site_packages.mkdir()
    runner = Mock()
    policy_checker = Mock(return_value=[])

    with pytest.raises(RuntimeError, match="MPL compliance requires correction"):
        _mock_packaging_preflight(
            root,
            site_packages,
            runner,
            policy_checker=policy_checker,
        )

    policy_checker.assert_called_once_with(root)
    runner.assert_not_called()


def test_mock_packaging_preflight_stops_on_policy_rejection(
    tmp_path: Path,
) -> None:
    fixture = _make_fixture(tmp_path)
    runner = Mock()
    policy_checker = Mock(return_value=["MPL-2.0 use requires authorization"])

    with pytest.raises(RuntimeError, match="MPL compliance requires correction"):
        _mock_packaging_preflight(
            fixture.root,
            fixture.site_packages,
            runner,
            policy_checker=policy_checker,
        )

    policy_checker.assert_called_once_with(fixture.root)
    runner.assert_not_called()


def _write_policy(root: Path, allowed_licenses: list[str]) -> None:
    (root / "THIRD_PARTY_DENYLIST.json").write_text(
        json.dumps({"policy": {"allowed_licenses": allowed_licenses}}),
        encoding="utf-8",
    )


def test_verify_policy_accepts_explicit_mpl_allowlist(tmp_path: Path) -> None:
    fixture = _make_fixture(tmp_path, install=False)
    _write_policy(fixture.root, ["MIT", "MPL-2.0"])

    assert verify_policy(fixture.root) == []


def test_verify_policy_rejects_missing_mpl_allowlist(tmp_path: Path) -> None:
    fixture = _make_fixture(tmp_path, install=False)
    _write_policy(fixture.root, ["MIT"])

    assert verify_policy(fixture.root) == [
        'MPL-2.0 use requires authorization in the project allowlist',
    ]


def test_verify_environment_rejects_missing_site_packages(tmp_path: Path) -> None:
    fixture = _make_fixture(tmp_path, install=False)

    errors = verify_environment(fixture.root, tmp_path / "missing-site-packages")

    assert any("site-packages is missing" in error for error in errors)


def test_verify_environment_rejects_known_package_without_metadata(
    tmp_path: Path,
) -> None:
    fixture = _make_fixture(tmp_path)
    metadata_dir = next(fixture.site_packages.glob("*.dist-info"))
    for path in sorted(metadata_dir.rglob("*"), reverse=True):
        if path.is_file():
            path.unlink()
        else:
            path.rmdir()
    metadata_dir.rmdir()

    errors = verify_environment(fixture.root, fixture.site_packages)

    assert any("metadata is missing or changed: certifi" in error for error in errors)


def test_verify_environment_rejects_unlisted_python_file(tmp_path: Path) -> None:
    fixture = _make_fixture(tmp_path)
    (fixture.site_packages / "certifi/unlisted.py").write_bytes(
        b"UNLISTED = True\n",
    )

    errors = verify_environment(fixture.root, fixture.site_packages)

    assert any("file inventory changed: certifi" in error for error in errors)


def test_verify_environment_rejects_unlisted_mpl_version(tmp_path: Path) -> None:
    fixture = _make_fixture(tmp_path)
    _metadata_path(fixture).write_text(
        "Metadata-Version: 2.4\n"
        "Name: certifi\n"
        "Version: 999.0\n"
        "License-Expression: MPL-2.0\n",
        encoding="utf-8",
    )

    errors = verify_environment(fixture.root, fixture.site_packages)

    assert any("MPL source evidence missing for certifi 999.0" in error for error in errors)


def test_verify_environment_rejects_metadata_expression_drift(tmp_path: Path) -> None:
    fixture = _make_fixture(tmp_path)
    _metadata_path(fixture).write_text(
        "Metadata-Version: 2.4\n"
        "Name: certifi\n"
        "Version: 2026.7.22\n"
        "License-Expression: MPL-2.0 AND MIT\n",
        encoding="utf-8",
    )

    errors = verify_environment(fixture.root, fixture.site_packages)

    assert any("MPL license expression drift: certifi" in error for error in errors)


def test_verify_environment_rejects_modified_installed_source(tmp_path: Path) -> None:
    fixture = _make_fixture(tmp_path)
    (fixture.site_packages / "certifi/__init__.py").write_bytes(b"MODIFIED = True\n")

    errors = verify_environment(fixture.root, fixture.site_packages)

    assert any("installed MPL source changed: certifi/__init__.py" in error for error in errors)


def test_verify_environment_ignores_non_mpl_metadata(tmp_path: Path) -> None:
    fixture = _make_fixture(tmp_path, install=False)
    metadata_dir = fixture.site_packages / "requests-2.34.2.dist-info"
    metadata_dir.mkdir()
    (metadata_dir / "METADATA").write_text(
        "Metadata-Version: 2.4\n"
        "Name: requests\n"
        "Version: 2.34.2\n"
        "License-Expression: Apache-2.0\n",
        encoding="utf-8",
    )

    assert verify_environment(fixture.root, fixture.site_packages) == []


def test_verify_environment_ignores_mpl_substring_in_non_mpl_license(
    tmp_path: Path,
) -> None:
    fixture = _make_fixture(tmp_path, install=False)
    metadata_dir = fixture.site_packages / "implied-1.0.dist-info"
    metadata_dir.mkdir()
    (metadata_dir / "METADATA").write_text(
        "Metadata-Version: 2.4\n"
        "Name: implied\n"
        "Version: 1.0\n"
        "License: BSD-3-Clause; IMPLIED by upstream\n",
        encoding="utf-8",
    )

    assert verify_environment(fixture.root, fixture.site_packages) == []


def test_verify_environment_does_not_import_installed_mpl_code(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _make_fixture(tmp_path)
    original_import = builtins.__import__

    def guarded_import(name: str, *args: object, **kwargs: object) -> object:
        if name.partition(".")[0] in {"certifi", "tqdm"}:
            raise AssertionError('MPL compliance must inspect files exclusively as data')
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded_import)

    assert verify_environment(fixture.root, fixture.site_packages) == []
