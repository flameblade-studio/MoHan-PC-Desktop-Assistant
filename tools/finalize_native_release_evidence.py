"""Bind every Windows package form to one verified native build."""

from __future__ import annotations

lazy import argparse
lazy import hashlib
lazy import json
lazy import re
lazy from collections.abc import Mapping, Sequence
lazy from dataclasses import dataclass
lazy from pathlib import Path

EXPECTED_LABELS = (
    "onedir",
    "zip",
    "exe",
    "msi-zh-TW",
    "msi-en-US",
    "msi-zh-CN",
    "msi-ja-JP",
)
TAG_PATTERN = re.compile(
    r"^v[0-9]+\.[0-9]+\.[0-9]+(?:-rc\.[1-9][0-9]*)?$"
)
SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")

type JsonObject = dict[str, object]


@dataclass(frozen=True, slots=True)
class PackageVerification:
    build: JsonObject
    native_files: JsonObject
    artifacts: tuple[JsonObject, ...]


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


def _digest(value: Mapping[str, object], key: str, context: str) -> str:
    candidate = _string(value, key, context)
    if SHA256_PATTERN.fullmatch(candidate) is None:
        raise ValueError(f"{context}.{key} must be a SHA-256 digest.")
    return candidate


def _positive_size(value: Mapping[str, object], context: str) -> int:
    candidate = value.get("size")
    if not isinstance(candidate, int) or isinstance(candidate, bool) or candidate <= 0:
        raise ValueError(f"{context}.size must be a positive integer.")
    return candidate


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


def _load_verifications(root: Path) -> dict[str, JsonObject]:
    documents: dict[str, JsonObject] = {}
    for path in sorted(root.glob("*.json")):
        document = _object(
            json.loads(path.read_text(encoding="utf-8")),
            path.name,
        )
        label = _string(document, "label", path.name)
        if label in documents:
            raise RuntimeError(f"Duplicate native verification label: {label}")
        documents[label] = document
    if set(documents) != set(EXPECTED_LABELS):
        raise RuntimeError(
            "Native verification labels are incomplete or unexpected: "
            f"{sorted(documents)}"
        )
    return documents


def _validated_native_files(document: JsonObject, label: str) -> JsonObject:
    native_files = _object(document.get("native_files"), f"{label}.native_files")
    if set(native_files) != {"module", "abi3t_compatibility_dll"}:
        raise RuntimeError(f"{label} native file set is incomplete.")
    for key in sorted(native_files):
        item = _object(native_files[key], f"{label}.{key}")
        _string(item, "name", f"{label}.{key}")
        _digest(item, "sha256", f"{label}.{key}")
        _positive_size(item, f"{label}.{key}")
    return native_files


def _validated_artifacts(
    document: JsonObject,
    artifacts: Path,
    expected_names: tuple[str, ...],
    label: str,
) -> list[JsonObject]:
    rows = _objects(document.get("artifacts"), f"{label}.artifacts")
    names = [_string(row, "name", f"{label}.artifact") for row in rows]
    if tuple(sorted(names)) != tuple(sorted(expected_names)):
        raise RuntimeError(f"{label} release artifact set is incorrect.")
    validated: list[JsonObject] = []
    for row in rows:
        name = _string(row, "name", f"{label}.artifact")
        digest = _digest(row, "sha256", f"{label}.artifact")
        size = _positive_size(row, f"{label}.artifact")
        path = artifacts / name
        if not path.is_file():
            raise FileNotFoundError(f"Native release artifact is missing: {name}")
        if _sha256(path) != digest or path.stat().st_size != size:
            raise RuntimeError(f"Native release artifact hash drift: {name}")
        validated.append({"name": name, "sha256": digest, "size": size})
    return validated


def _validated_verification(
    document: JsonObject,
    artifacts: Path,
    expected_names: tuple[str, ...],
    label: str,
) -> PackageVerification:
    if (
        document.get("schema") != "mohan.packaged-native-verification.v1"
        or document.get("status") != "pass"
    ):
        raise RuntimeError(f"{label} native verification did not pass.")
    if document.get("operations") != ["pcm16", "rgba"]:
        raise RuntimeError(f"{label} native operations were not fully verified.")
    return PackageVerification(
        _object(document.get("build"), f"{label}.build"),
        _validated_native_files(document, label),
        tuple(
            _validated_artifacts(document, artifacts, expected_names, label)
        ),
    )


def _merge_artifacts(
    destination: dict[str, JsonObject],
    rows: Sequence[JsonObject],
) -> None:
    for row in rows:
        name = str(row["name"])
        if name in destination and destination[name] != row:
            raise RuntimeError(f"Conflicting artifact evidence: {name}")
        destination[name] = row


def _require_matching_build(
    candidate: PackageVerification,
    canonical: PackageVerification,
    label: str,
) -> None:
    if (
        candidate.build != canonical.build
        or candidate.native_files != canonical.native_files
    ):
        raise RuntimeError(f"{label} does not contain the canonical native build.")


def _require_binary_bindings(verification: PackageVerification) -> None:
    module = _object(verification.native_files["module"], "native module")
    if module["sha256"] != verification.build.get("wheel_module_sha256"):
        raise RuntimeError("Packaged native module does not match the wheel evidence.")
    dll = _object(
        verification.native_files["abi3t_compatibility_dll"],
        "abi3t compatibility DLL",
    )
    build_dll = _object(
        verification.build.get("abi3t_compatibility_dll"),
        "build abi3t compatibility DLL",
    )
    if dll["sha256"] != build_dll.get("sha256"):
        raise RuntimeError("Packaged python3t.dll does not match build evidence.")


def finalize_evidence(
    verification_dir: Path,
    artifacts_dir: Path,
    tag: str,
) -> JsonObject:
    """Validate and merge seven package-form verification documents."""
    if TAG_PATTERN.fullmatch(tag) is None:
        raise ValueError("Native release evidence requires a valid Release tag.")
    verifications = _load_verifications(verification_dir.resolve())
    artifacts = artifacts_dir.resolve()
    expected_artifacts = _artifact_names(tag)
    validated = {
        label: _validated_verification(
            verifications[label],
            artifacts,
            expected_artifacts[label],
            label,
        )
        for label in EXPECTED_LABELS
    }
    canonical = validated[EXPECTED_LABELS[0]]
    release_artifacts: dict[str, JsonObject] = {}
    validation_rows: list[JsonObject] = []
    for label in EXPECTED_LABELS:
        verification = validated[label]
        _require_matching_build(verification, canonical, label)
        _merge_artifacts(release_artifacts, verification.artifacts)
        validation_rows.append(
            {"artifacts": sorted(expected_artifacts[label]), "label": label}
        )
    _require_binary_bindings(canonical)
    return {
        "build": canonical.build,
        "native_files": canonical.native_files,
        "release_artifacts": [
            release_artifacts[name] for name in sorted(release_artifacts)
        ],
        "schema": "mohan.native-release-evidence.v1",
        "status": "pass",
        "tag": tag,
        "validations": validation_rows,
        "verified_labels": list(EXPECTED_LABELS),
    }


def _arguments(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--verifications", type=Path, required=True)
    parser.add_argument("--artifacts", type=Path, required=True)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _arguments(argv)
    document = finalize_evidence(args.verifications, args.artifacts, args.tag)
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"MOHAN_NATIVE_RELEASE_EVIDENCE_OK={output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
