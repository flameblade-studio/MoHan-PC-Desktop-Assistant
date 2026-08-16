"""Generate a reproducible CycloneDX inventory for the Rust native core."""

from __future__ import annotations

lazy import argparse
lazy import hashlib
lazy import json
lazy import re
lazy import subprocess
lazy import tomllib
lazy from collections.abc import Mapping, Sequence
lazy from dataclasses import dataclass
lazy from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NATIVE_ROOT = ROOT / "native" / "mohan_accel"
MANIFEST = NATIVE_ROOT / "Cargo.toml"
LOCK = NATIVE_ROOT / "Cargo.lock"
SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")

type JsonObject = dict[str, object]
type LockIndex = Mapping[tuple[str, str], str | None]


@dataclass(frozen=True, slots=True)
class NativeSbomIdentity:
    tag: str
    evidence_name: str
    evidence_sha256: str


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


def load_cargo_lock(path: Path = LOCK) -> dict[tuple[str, str], str | None]:
    """Index every locked package and registry checksum."""
    document = tomllib.loads(path.read_text(encoding="utf-8"))
    index: dict[tuple[str, str], str | None] = {}
    for row in _objects(document.get("package"), "Cargo.lock packages"):
        key = (
            _string(row, "name", "Cargo.lock package"),
            _string(row, "version", "Cargo.lock package"),
        )
        if key in index:
            raise RuntimeError(f"Duplicate Cargo.lock package: {key}")
        checksum = row.get("checksum")
        if checksum is not None and (
            not isinstance(checksum, str)
            or SHA256_PATTERN.fullmatch(checksum) is None
        ):
            raise ValueError(f"Invalid Cargo.lock checksum for {key}.")
        index[key] = checksum
    return index


def cargo_metadata(cargo: str = "cargo") -> JsonObject:
    """Read the exact locked Windows dependency graph used by the release."""
    completed = subprocess.run(
        (
            cargo,
            "metadata",
            "--locked",
            "--format-version",
            "1",
            "--filter-platform",
            "x86_64-pc-windows-msvc",
            "--features",
            "extension-module",
            "--manifest-path",
            str(MANIFEST),
        ),
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return _object(json.loads(completed.stdout), "cargo metadata")


def _purl(name: str, version: str) -> str:
    return f"pkg:cargo/{name}@{version}"


def _component(package: JsonObject, checksum: str | None) -> JsonObject:
    name = _string(package, "name", "cargo package")
    version = _string(package, "version", "cargo package")
    license_expression = _string(package, "license", f"cargo package {name}")
    component: JsonObject = {
        "bom-ref": _purl(name, version),
        "licenses": [
            {"acknowledgement": "declared", "expression": license_expression}
        ],
        "name": name,
        "purl": _purl(name, version),
        "type": "library",
        "version": version,
    }
    if checksum is not None:
        component["hashes"] = [{"alg": "SHA-256", "content": checksum}]
    return component


def _file_component(name: str, details: JsonObject) -> JsonObject:
    digest = _string(details, "sha256", name)
    size = details.get("size")
    if SHA256_PATTERN.fullmatch(digest) is None:
        raise ValueError(f"{name} evidence does not contain SHA-256.")
    if not isinstance(size, int) or isinstance(size, bool) or size <= 0:
        raise ValueError(f"{name} evidence size is invalid.")
    return {
        "bom-ref": f"urn:sha256:{digest}",
        "hashes": [{"alg": "SHA-256", "content": digest}],
        "name": name,
        "properties": [
            {"name": "com.flamebladestudio.packaged-size", "value": str(size)}
        ],
        "type": "file",
    }


def _resolved_graph(
    metadata: JsonObject,
) -> tuple[str, dict[str, JsonObject], dict[str, JsonObject], set[str]]:
    resolve = _object(metadata.get("resolve"), "cargo resolve")
    root_id = _string(resolve, "root", "cargo resolve")
    nodes = {
        _string(node, "id", "cargo node"): node
        for node in _objects(resolve.get("nodes"), "cargo nodes")
    }
    reachable: set[str] = set()
    pending = [root_id]
    while pending:
        package_id = pending.pop()
        if package_id in reachable:
            continue
        if package_id not in nodes:
            raise RuntimeError(f"Cargo graph is missing node {package_id}.")
        reachable.add(package_id)
        dependencies = nodes[package_id].get("dependencies")
        if not isinstance(dependencies, list) or not all(
            isinstance(item, str) for item in dependencies
        ):
            raise TypeError(f"Cargo dependencies for {package_id} are invalid.")
        pending.extend(dependencies)
    packages = {
        _string(package, "id", "cargo package"): package
        for package in _objects(metadata.get("packages"), "cargo packages")
    }
    if not set(packages).issuperset(reachable):
        raise RuntimeError("Cargo metadata omitted a resolved package.")
    return root_id, nodes, packages, reachable


def _cargo_components(
    packages: Mapping[str, JsonObject],
    reachable: set[str],
    root_id: str,
    lock: LockIndex,
) -> list[JsonObject]:
    components: list[JsonObject] = []
    for package_id in sorted(reachable - {root_id}):
        package = packages[package_id]
        key = (
            _string(package, "name", "cargo package"),
            _string(package, "version", "cargo package"),
        )
        if key not in lock:
            raise RuntimeError(f"Resolved crate is absent from Cargo.lock: {key}")
        components.append(_component(package, lock[key]))
    return components


def _native_file_components(evidence: JsonObject) -> tuple[JsonObject, JsonObject]:
    native_files = _object(evidence.get("native_files"), "native files")
    module = _object(native_files.get("module"), "native module")
    dll = _object(
        native_files.get("abi3t_compatibility_dll"),
        "abi3t compatibility DLL",
    )
    return (
        _file_component("_mohan_accel.pyd", module),
        _file_component("python3t.dll", dll),
    )


def _dependency_graph(
    nodes: Mapping[str, JsonObject],
    packages: Mapping[str, JsonObject],
    reachable: set[str],
    file_components: Sequence[JsonObject],
) -> list[JsonObject]:
    refs = {
        package_id: _purl(
            _string(packages[package_id], "name", "cargo package"),
            _string(packages[package_id], "version", "cargo package"),
        )
        for package_id in reachable
    }
    dependencies: list[JsonObject] = [
        {
            "dependsOn": sorted(refs[item] for item in nodes[package_id]["dependencies"]),
            "ref": refs[package_id],
        }
        for package_id in sorted(reachable)
    ]
    dependencies.extend(
        {"dependsOn": [], "ref": component["bom-ref"]}
        for component in file_components
    )
    return sorted(dependencies, key=lambda item: str(item["ref"]))


def _root_component(root: JsonObject, identity: NativeSbomIdentity) -> JsonObject:
    name = _string(root, "name", "root package")
    version = _string(root, "version", "root package")
    return {
        "bom-ref": _purl(name, version),
        "licenses": [
            {
                "acknowledgement": "declared",
                "expression": _string(root, "license", "root package"),
            }
        ],
        "name": name,
        "purl": _purl(name, version),
        "properties": [
            {"name": "com.flamebladestudio.release-tag", "value": identity.tag},
            {
                "name": "com.flamebladestudio.native-evidence-name",
                "value": identity.evidence_name,
            },
            {
                "name": "com.flamebladestudio.native-evidence-sha256",
                "value": identity.evidence_sha256,
            },
        ],
        "type": "library",
        "version": version,
    }


def build_native_sbom(
    metadata: JsonObject,
    lock: LockIndex,
    evidence: JsonObject,
    *,
    identity: NativeSbomIdentity,
) -> JsonObject:
    """Build one deterministic native SBOM from Cargo and package evidence."""
    if evidence.get("schema") != "mohan.native-release-evidence.v1":
        raise ValueError("Native release evidence schema is unsupported.")
    if evidence.get("status") != "pass":
        raise ValueError("Native release evidence did not pass.")
    if SHA256_PATTERN.fullmatch(identity.evidence_sha256) is None:
        raise ValueError("Native release evidence hash must be SHA-256.")
    root_id, nodes, packages, reachable = _resolved_graph(metadata)
    root = packages[root_id]
    file_components = _native_file_components(evidence)
    return {
        "bomFormat": "CycloneDX",
        "components": [
            *_cargo_components(packages, reachable, root_id, lock),
            *file_components,
        ],
        "dependencies": _dependency_graph(
            nodes,
            packages,
            reachable,
            file_components,
        ),
        "metadata": {
            "component": _root_component(root, identity),
            "properties": [{"name": "cdx:reproducible", "value": "true"}],
        },
        "specVersion": "1.7",
        "version": 1,
    }


def _arguments(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cargo", default="cargo")
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _arguments(argv)
    evidence_path = args.evidence.resolve()
    evidence = _object(
        json.loads(evidence_path.read_text(encoding="utf-8")),
        evidence_path.name,
    )
    document = build_native_sbom(
        cargo_metadata(args.cargo),
        load_cargo_lock(),
        evidence,
        identity=NativeSbomIdentity(
            args.tag,
            evidence_path.name,
            _sha256(evidence_path),
        ),
    )
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"MOHAN_NATIVE_SBOM_OK={output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
