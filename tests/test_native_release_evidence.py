from __future__ import annotations

lazy import hashlib
lazy import json
lazy from pathlib import Path

lazy import pytest

lazy from tools.finalize_native_release_evidence import finalize_evidence
lazy from tools.generate_native_sbom import NativeSbomIdentity, build_native_sbom
lazy from tools.validate_native_sbom import SCHEMA_VALIDATION_PROGRAM, validate_document

LABELS = (
    "onedir",
    "zip",
    "exe",
    "msi-zh-TW",
    "msi-en-US",
    "msi-zh-CN",
    "msi-ja-JP",
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _artifact_names(tag: str) -> dict[str, tuple[str, ...]]:
    base = f"MoHan-Desktop-Assistant-{tag}"
    msi = f"{base}-Windows-x64.msi"
    return {
        "onedir": (),
        "zip": (f"{base}-Windows-x64.zip",),
        "exe": (f"{base}-Windows-x64-Setup.exe",),
        "msi-zh-TW": (msi,),
        "msi-en-US": (msi, f"{base}-en-US.mst"),
        "msi-zh-CN": (msi, f"{base}-zh-CN.mst"),
        "msi-ja-JP": (msi, f"{base}-ja-JP.mst"),
    }


def _seed_verifications(root: Path, artifacts: Path, tag: str) -> None:
    build = {
        "abi3t_compatibility_dll": {
            "name": "python3t.dll",
            "sha256": "d" * 64,
            "size": 456,
        },
        "schema": "mohan.native-acceleration.v2",
        "wheel": "mohan_accel-0.1.0-cp315-abi3.abi3t-win_amd64.whl",
        "wheel_module": "_mohan_accel/_mohan_accel.pyd",
        "wheel_module_sha256": "b" * 64,
        "wheel_module_size": 123,
        "wheel_sha256": "c" * 64,
        "wheel_tags": [
            "cp315-abi3-win_amd64",
            "cp315-abi3t-win_amd64",
        ],
    }
    names = {
        *(
            item
            for values in _artifact_names(tag).values()
            for item in values
        )
    }
    for name in sorted(names):
        (artifacts / name).write_bytes(name.encode("utf-8"))
    for label in LABELS:
        artifact_rows = [
            {
                "name": name,
                "sha256": _sha256(artifacts / name),
                "size": (artifacts / name).stat().st_size,
            }
            for name in _artifact_names(tag)[label]
        ]
        document = {
            "artifacts": artifact_rows,
            "build": build,
            "label": label,
            "native_files": {
                "abi3t_compatibility_dll": {
                    "name": "python3t.dll",
                    "sha256": "d" * 64,
                    "size": 456,
                },
                "module": {
                    "name": "_mohan_accel.pyd",
                    "sha256": "b" * 64,
                    "size": 123,
                },
            },
            "operations": ["pcm16", "rgba"],
            "schema": "mohan.packaged-native-verification.v1",
            "status": "pass",
        }
        (root / f"{label}.json").write_text(
            json.dumps(document),
            encoding="utf-8",
        )


def test_release_evidence_requires_all_seven_verified_forms(tmp_path: Path) -> None:
    tag = "v4.0.0"
    verifications = tmp_path / "verifications"
    artifacts = tmp_path / "artifacts"
    verifications.mkdir()
    artifacts.mkdir()
    _seed_verifications(verifications, artifacts, tag)

    evidence = finalize_evidence(verifications, artifacts, tag)
    assert evidence["verified_labels"] == list(LABELS)
    assert evidence["native_files"]["module"]["sha256"] == "b" * 64
    assert evidence["build"]["wheel_module_sha256"] == "b" * 64
    assert len(evidence["release_artifacts"]) == 6

    (verifications / "msi-ja-JP.json").unlink()
    with pytest.raises(RuntimeError, match="verification labels"):
        finalize_evidence(verifications, artifacts, tag)


def test_release_evidence_rejects_artifact_hash_drift(tmp_path: Path) -> None:
    tag = "v4.0.0"
    verifications = tmp_path / "verifications"
    artifacts = tmp_path / "artifacts"
    verifications.mkdir()
    artifacts.mkdir()
    _seed_verifications(verifications, artifacts, tag)
    zip_name = _artifact_names(tag)["zip"][0]
    (artifacts / zip_name).write_bytes(b"tampered")
    with pytest.raises(RuntimeError, match="hash drift"):
        finalize_evidence(verifications, artifacts, tag)


def test_native_sbom_contains_root_rayon_transitives_and_evidence() -> None:
    root_id = "path+file:///workspace#mohan-accel@0.1.0"
    rayon_id = "registry+crates.io#rayon@1.12.0"
    core_id = "registry+crates.io#rayon-core@1.13.0"
    metadata = {
        "packages": [
            {"id": root_id, "license": "MIT", "name": "mohan-accel", "source": None, "version": "0.1.0"},
            {"id": rayon_id, "license": "MIT OR Apache-2.0", "name": "rayon", "source": "registry+crates.io", "version": "1.12.0"},
            {"id": core_id, "license": "MIT OR Apache-2.0", "name": "rayon-core", "source": "registry+crates.io", "version": "1.13.0"},
        ],
        "resolve": {
            "root": root_id,
            "nodes": [
                {"id": root_id, "dependencies": [rayon_id]},
                {"id": rayon_id, "dependencies": [core_id]},
                {"id": core_id, "dependencies": []},
            ],
        },
    }
    lock = {
        ("mohan-accel", "0.1.0"): None,
        ("rayon", "1.12.0"): "1" * 64,
        ("rayon-core", "1.13.0"): "2" * 64,
    }
    evidence = {
        "schema": "mohan.native-release-evidence.v1",
        "status": "pass",
        "build": {"wheel_sha256": "3" * 64},
        "native_files": {
            "module": {"sha256": "4" * 64, "size": 123},
            "abi3t_compatibility_dll": {"sha256": "5" * 64, "size": 456},
        },
    }
    sbom = build_native_sbom(
        metadata,
        lock,
        evidence,
        identity=NativeSbomIdentity(
            "v4.0.0",
            "MoHan-Desktop-Assistant-v4.0.0-Native-Evidence.json",
            "6" * 64,
        ),
    )
    assert sbom["metadata"]["component"]["name"] == "mohan-accel"
    names = {component["name"] for component in sbom["components"]}
    assert {"rayon", "rayon-core", "python3t.dll"}.issubset(names)
    assert "6" * 64 in json.dumps(sbom)
    validate_document(
        sbom,
        evidence,
        evidence_name="MoHan-Desktop-Assistant-v4.0.0-Native-Evidence.json",
        evidence_sha256="6" * 64,
    )
    with pytest.raises(RuntimeError, match="evidence hash"):
        validate_document(
            sbom,
            evidence,
            evidence_name=(
                "MoHan-Desktop-Assistant-v4.0.0-Native-Evidence.json"
            ),
            evidence_sha256="7" * 64,
        )


def test_native_sbom_schema_program_is_standard_python() -> None:
    compile(SCHEMA_VALIDATION_PROGRAM, "native-sbom-schema.py", "exec")
