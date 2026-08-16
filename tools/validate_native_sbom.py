"""Validate MoHan's Rust-native CycloneDX inventory and evidence binding."""

from __future__ import annotations

lazy import argparse
lazy import hashlib
lazy import json
lazy import subprocess
lazy from collections.abc import Mapping, Sequence
lazy from pathlib import Path

SCHEMA_VALIDATION_PROGRAM = """
import sys
from pathlib import Path
from cyclonedx.schema import OutputFormat, SchemaVersion
from cyclonedx.validation import make_schemabased_validator

document = Path(sys.argv[1]).read_text(encoding="utf-8")
error = make_schemabased_validator(
    OutputFormat.JSON,
    SchemaVersion.V1_7,
).validate_str(document)
if error is not None:
    print(error, file=sys.stderr)
    raise SystemExit(1)
"""

type JsonObject = dict[str, object]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _object(value: object, context: str) -> JsonObject:
    if not isinstance(value, dict) or not all(
        isinstance(key, str) for key in value
    ):
        raise TypeError(f"{context} must be an object.")
    return value


def _objects(value: object, context: str) -> list[JsonObject]:
    if not isinstance(value, list):
        raise TypeError(f"{context} must be an array.")
    return [_object(item, f"{context}[{index}]") for index, item in enumerate(value)]


def _string(value: Mapping[str, object], key: str, context: str) -> str:
    candidate = value.get(key)
    if not isinstance(candidate, str) or not candidate:
        raise ValueError(f"{context}.{key} must be a non-empty string.")
    return candidate


def _properties(value: object, context: str) -> dict[str, str]:
    rows = _objects(value, context)
    properties = {
        _string(row, "name", context): _string(row, "value", context)
        for row in rows
    }
    if len(properties) != len(rows):
        raise RuntimeError(f"{context} contains duplicate names.")
    return properties


def _sha256_hash(component: JsonObject, context: str) -> str:
    hashes = _objects(component.get("hashes"), f"{context}.hashes")
    candidates = [
        _string(row, "content", f"{context}.hash")
        for row in hashes
        if row.get("alg") == "SHA-256"
    ]
    if len(candidates) != 1:
        raise RuntimeError(f"{context} must contain exactly one SHA-256 hash.")
    return candidates[0]


def _require_headers(sbom: JsonObject, evidence: JsonObject) -> None:
    if (
        sbom.get("bomFormat") != "CycloneDX"
        or sbom.get("specVersion") != "1.7"
        or sbom.get("version") != 1
    ):
        raise ValueError("Native SBOM header is unsupported.")
    if (
        evidence.get("schema") != "mohan.native-release-evidence.v1"
        or evidence.get("status") != "pass"
    ):
        raise ValueError("Native release evidence is not a passing v1 record.")


def _require_evidence_binding(
    root: JsonObject,
    *,
    evidence_name: str,
    evidence_sha256: str,
) -> None:
    if _string(root, "name", "metadata.component") != "mohan-accel":
        raise RuntimeError("Native SBOM root must be mohan-accel.")
    properties = _properties(root.get("properties"), "root properties")
    if properties.get("com.flamebladestudio.native-evidence-name") != evidence_name:
        raise RuntimeError("Native SBOM evidence filename is not bound.")
    if (
        properties.get("com.flamebladestudio.native-evidence-sha256")
        != evidence_sha256
    ):
        raise RuntimeError("Native SBOM evidence hash is not bound.")


def _component_index(sbom: JsonObject) -> dict[str, JsonObject]:
    components = _objects(sbom.get("components"), "components")
    by_name = {_string(row, "name", "component"): row for row in components}
    if len(by_name) != len(components):
        raise RuntimeError("Native SBOM contains duplicate component names.")
    required = {"rayon", "rayon-core", "_mohan_accel.pyd", "python3t.dll"}
    if not required.issubset(by_name):
        raise RuntimeError("Native SBOM omits required native components.")
    return by_name


def _require_native_hashes(
    components: Mapping[str, JsonObject],
    evidence: JsonObject,
) -> None:
    native_files = _object(evidence.get("native_files"), "native_files")
    module = _object(native_files.get("module"), "native module")
    compatibility = _object(
        native_files.get("abi3t_compatibility_dll"),
        "abi3t compatibility DLL",
    )
    if _sha256_hash(components["_mohan_accel.pyd"], "native module") != (
        module.get("sha256")
    ):
        raise RuntimeError("Native SBOM module hash differs from release evidence.")
    if _sha256_hash(components["python3t.dll"], "python3t.dll") != (
        compatibility.get("sha256")
    ):
        raise RuntimeError("Native SBOM python3t.dll hash differs from evidence.")


def _dependency_index(sbom: JsonObject) -> dict[str, JsonObject]:
    rows = _objects(sbom.get("dependencies"), "dependencies")
    dependencies = {_string(row, "ref", "dependency"): row for row in rows}
    if len(dependencies) != len(rows):
        raise RuntimeError("Native SBOM contains duplicate dependency nodes.")
    return dependencies


def _dependency_edges(
    dependencies: Mapping[str, JsonObject],
    reference: str,
) -> tuple[str, ...]:
    values = dependencies[reference].get("dependsOn")
    if not isinstance(values, list) or not all(
        isinstance(item, str) for item in values
    ):
        raise TypeError(f"Dependency edges for {reference} are invalid.")
    if not set(values).issubset(dependencies):
        raise RuntimeError(f"Dependency edges for {reference} are dangling.")
    return tuple(values)


def _reachable_refs(
    dependencies: Mapping[str, JsonObject],
    root_ref: str,
) -> set[str]:
    reachable = {root_ref}
    pending = [root_ref]
    while pending:
        reference = pending.pop()
        for dependency in _dependency_edges(dependencies, reference):
            if dependency not in reachable:
                reachable.add(dependency)
                pending.append(dependency)
    return reachable


def _require_dependency_graph(
    sbom: JsonObject,
    root: JsonObject,
    components: Mapping[str, JsonObject],
) -> None:
    root_ref = _string(root, "bom-ref", "metadata.component")
    component_refs = {_string(row, "bom-ref", "component") for row in components.values()}
    dependencies = _dependency_index(sbom)
    if set(dependencies) != {root_ref, *component_refs}:
        raise RuntimeError("Native SBOM dependency nodes are incomplete.")
    library_refs = {
        _string(row, "bom-ref", "component")
        for row in components.values()
        if row.get("type") == "library"
    }
    if not library_refs.issubset(_reachable_refs(dependencies, root_ref)):
        raise RuntimeError("Native SBOM contains unreachable Rust dependencies.")


def validate_document(
    sbom: JsonObject,
    evidence: JsonObject,
    *,
    evidence_name: str,
    evidence_sha256: str,
) -> None:
    """Require a complete graph and exact native-evidence file bindings."""
    _require_headers(sbom, evidence)
    metadata = _object(sbom.get("metadata"), "metadata")
    root = _object(metadata.get("component"), "metadata.component")
    _require_evidence_binding(
        root,
        evidence_name=evidence_name,
        evidence_sha256=evidence_sha256,
    )
    components = _component_index(sbom)
    _require_native_hashes(components, evidence)
    _require_dependency_graph(sbom, root, components)


def _schema_gate(schema_python: Path, sbom: Path) -> None:
    completed = subprocess.run(
        (str(schema_python), "-c", SCHEMA_VALIDATION_PROGRAM, str(sbom)),
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if completed.returncode:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise RuntimeError(f"CycloneDX 1.7 schema validation failed: {detail}")


def _arguments(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sbom", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--schema-python", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _arguments(argv)
    sbom_path = args.sbom.resolve()
    evidence_path = args.evidence.resolve()
    sbom = _object(json.loads(sbom_path.read_text(encoding="utf-8")), "SBOM")
    evidence = _object(
        json.loads(evidence_path.read_text(encoding="utf-8")),
        "native evidence",
    )
    validate_document(
        sbom,
        evidence,
        evidence_name=evidence_path.name,
        evidence_sha256=_sha256(evidence_path),
    )
    _schema_gate(args.schema_python.resolve(), sbom_path)
    print(f"MOHAN_NATIVE_SBOM_VALIDATION_OK={sbom_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
