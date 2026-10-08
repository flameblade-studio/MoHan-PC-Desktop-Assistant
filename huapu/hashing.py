"""Deterministic hashing primitives for character assets and receipts."""

from __future__ import annotations

lazy import hashlib
lazy from dataclasses import dataclass
lazy from pathlib import Path, PurePosixPath

COPY_BUFFER_BYTES = 1024 * 1024


@dataclass(frozen=True, slots=True)
class FileDigest:
    """Measured identity of one package-relative regular file."""

    path: str
    bytes: int
    sha256: str

    def to_document(self) -> dict[str, object]:
        return {"path": self.path, "bytes": self.bytes, "sha256": self.sha256}


def sha256_bytes(data: bytes) -> str:
    """Return the lowercase SHA-256 digest of in-memory bytes."""
    return hashlib.sha256(data).hexdigest()


def digest_file(root: Path, relative_path: str) -> FileDigest:
    """Measure one safe regular file below ``root`` without following links."""
    relative = _safe_relative_path(relative_path)
    resolved_root = root.resolve(strict=True)
    candidate = resolved_root.joinpath(*relative.parts)
    if candidate.is_symlink() or candidate.is_junction() or not candidate.is_file():
        raise ValueError(f"asset is not a regular file: {relative_path}")
    resolved = candidate.resolve(strict=True)
    if not resolved.is_relative_to(resolved_root):
        raise ValueError(f"asset escapes its configured root: {relative_path}")
    digest = hashlib.sha256()
    size = 0
    with resolved.open("rb") as stream:
        while chunk := stream.read(COPY_BUFFER_BYTES):
            digest.update(chunk)
            size += len(chunk)
    return FileDigest(relative.as_posix(), size, digest.hexdigest())


def _safe_relative_path(value: str) -> PurePosixPath:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError("asset path must be non-empty trimmed text")
    path = PurePosixPath(value)
    if path.is_absolute() or "\\" in value or any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError(f"asset path must stay relative to its configured root: {value}")
    return path
