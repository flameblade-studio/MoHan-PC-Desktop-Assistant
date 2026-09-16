"""Consolidate completed visible-partition batches while preserving separate remainders."""

from __future__ import annotations

lazy import argparse
lazy from copy import deepcopy
lazy import hashlib
lazy import json
lazy from pathlib import Path
lazy from typing import Sequence

lazy from tools.art_pipeline.reviewed_partitions import (
    ROLES, SCHEMA, integrate_batch, verify_completed_entry,
)

SHA256_HEX_LENGTH = 64


def _read(path: Path, snapshots: dict[Path, bytes], digest: str | None = None) -> bytes:
    payload = path.read_bytes()
    if digest is not None and hashlib.sha256(payload).hexdigest() != digest:
        raise ValueError(f"Batch file hash mismatch: {path}")
    if path in snapshots and snapshots[path] != payload:
        raise ValueError(f"Batch file changed during intake: {path}")
    snapshots[path] = payload
    return payload


def _absolute_entry(entry: dict, base: Path) -> dict:
    result = deepcopy(entry)
    records = [result["source"], *(part["mask"] for part in result["parts"])]
    for record in records:
        record["path"] = str((base / record["path"]).resolve())
    for part in result["parts"]:
        review = part["review"]
        for name in ("evidence", "trace"):
            if f"{name}_sha256" in review:
                path = review.get(name)
                if not isinstance(path, str) or not path.strip():
                    raise ValueError(f"Hashed review {name} requires a file path")
                review[name] = str((base / path).resolve())
    return result


def _verify_entry_export(
    entry: dict, report: dict, batch: Path, base: Path, snapshots: dict[Path, bytes],
) -> None:
    if any(entry[key] != report.get(key) for key in ("id", "source", "parts")):
        raise ValueError("Batch receipt inputs differ from its manifest")
    # Derive output paths exclusively from allowed roles; receipt names are metadata.
    identifier = entry["id"]
    if not isinstance(identifier, str) or not identifier or any(
        char not in "abcdefghijklmnopqrstuvwxyz0123456789_+-" for char in identifier
    ):
        raise ValueError("A view identifier matching the required format is required")
    roles = [part["role"] for part in entry["parts"]]
    if not roles or len(set(roles)) != len(roles) or not set(roles) <= ROLES:
        raise ValueError("Component roles must be valid and unique")
    names = {f"{role}.png" for role in roles} | {"remaining_foreground.png", "reconstruction.png"}
    outputs = report.get("outputs")
    if not isinstance(outputs, dict) or set(outputs) != names:
        raise ValueError("Batch output inventory differs from its declared components")
    directory = batch / identifier
    if {path.name for path in directory.iterdir()} != names:
        raise ValueError("Completed entry outputs must exactly match the listed output set")
    payloads = {}
    for name in sorted(names):
        digest = outputs[name]
        if not isinstance(digest, str) or len(digest) != SHA256_HEX_LENGTH:
            raise ValueError("A batch output digest matching the required SHA-256 format is required")
        payloads[name] = _read(directory / name, snapshots, digest)
    verify_completed_entry(entry, report, payloads, base, snapshots)


def _completed_entries(manifest: Path, batch: Path, snapshots: dict[Path, bytes]) -> list[dict]:
    payload = _read(manifest, snapshots)
    spec = json.loads(payload)
    receipt = json.loads(_read(batch / "receipt.json", snapshots))
    if (
        spec.get("schema") != SCHEMA
        or receipt.get("schema") != SCHEMA
        or receipt.get("manifest_sha256") != hashlib.sha256(payload).hexdigest()
        or receipt.get("status") != "integrated_partial_visible_partitions"
        or receipt.get("production_runtime_ready") is not False
        or receipt.get("complete_24_600") is not False
    ):
        raise ValueError(f"Expected a completed partial batch bound to its manifest: {batch}")
    entries, reports = spec.get("entries"), receipt.get("entries")
    if not isinstance(entries, list) or not entries or not isinstance(reports, list):
        raise ValueError("Completed batch entries must be nonempty lists")
    if len(entries) != len(reports):
        raise ValueError("Batch receipt entry count differs from its manifest")
    for entry, report in zip(entries, reports, strict=True):
        _verify_entry_export(entry, report, batch, manifest.parent, snapshots)
    if {path.name for path in batch.iterdir()} != {entry["id"] for entry in entries} | {"receipt.json"}:
        raise ValueError("Completed batch entries must exactly match the listed entry set")
    normalized = [_absolute_entry(entry, manifest.parent) for entry in entries]
    for entry in normalized:
        records = [entry["source"], *(part["mask"] for part in entry["parts"])]
        for part in entry["parts"]:
            review = part["review"]
            for name in ("evidence", "trace"):
                if f"{name}_sha256" in review:
                    records.append({"path": review[name], "sha256": review[f"{name}_sha256"]})
        for record in records:
            _read(Path(record["path"]), snapshots, record["sha256"])
    return normalized


def verify_completed_batch(manifest: Path, batch: Path) -> list[dict]:
    """Read a completed partial batch, verifying native pixels and evidence.

    Return entries with absolute paths through read-only inspection.
    """
    snapshots: dict[Path, bytes] = {}
    entries = _completed_entries(manifest.resolve(), batch.resolve(), snapshots)
    identifiers = [entry["id"] for entry in entries]
    if len(set(identifiers)) != len(identifiers):
        raise ValueError("Duplicate source identifiers in completed batch")
    for path, original in snapshots.items():
        if path.read_bytes() != original:
            raise ValueError(f"Batch file changed during verification: {path}")
    return entries


def consolidate_batches(
    batches: Sequence[tuple[Path, Path]], manifest: Path, output: Path,
) -> dict:
    """Verify completed batches, group disjoint roles, then rebuild from native sources.

    Writes a new manifest and a new partial batch. A manifest can remain after
    validation stops; only the export's final receipt denotes successful output.
    Existing manifests, exports, source images and review artifacts stay unchanged.
    """
    if not batches or manifest.exists() or output.exists():
        raise ValueError("Require input batches and unused manifest/output paths")
    snapshots: dict[Path, bytes] = {}
    grouped: dict[str, dict] = {}
    provenance = []
    for source_manifest, batch in batches:
        source_manifest, batch = source_manifest.resolve(), batch.resolve()
        for entry in _completed_entries(source_manifest, batch, snapshots):
            identifier = entry["id"]
            if identifier not in grouped:
                grouped[identifier] = entry
                continue
            previous = grouped[identifier]
            if previous["source"]["sha256"] != entry["source"]["sha256"]:
                raise ValueError(f"Conflicting native sources for view: {identifier}")
            existing_roles = {part["role"] for part in previous["parts"]}
            if existing_roles & {part["role"] for part in entry["parts"]}:
                raise ValueError(f"Duplicate component across batches: {identifier}")
            previous["parts"].extend(entry["parts"])
        provenance.append({"manifest": str(source_manifest), "batch": str(batch),
                           "receipt_sha256": hashlib.sha256(snapshots[batch / "receipt.json"]).hexdigest()})
    for path, original in snapshots.items():
        if path.read_bytes() != original:
            raise ValueError(f"Batch file changed before consolidation: {path}")
    spec = {"schema": SCHEMA, "entries": list(grouped.values()), "input_batches": provenance}
    with manifest.open("x", encoding="utf-8") as handle:
        json.dump(spec, handle, indent=2)
        handle.write("\n")
    # Recompute a single complement for each view; adding old complements would overlap.
    return integrate_batch(manifest, output)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch", nargs=2, action="append", required=True,
                        metavar=("MANIFEST", "EXPORT"), type=Path)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = consolidate_batches(args.batch, args.manifest, args.output)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
