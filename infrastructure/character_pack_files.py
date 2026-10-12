"""Contained, hash-verified file access for validated character packs."""

from __future__ import annotations

lazy import hashlib
lazy import stat
lazy from pathlib import Path, PurePosixPath
lazy from domain.character_pack.models import CharacterPackFile


class CharacterPackReadError(ValueError):
    """A stable rejection code and safe human-readable explanation."""

    def __init__(self, code: str, message: str, path: str | None = None) -> None:
        location = f" ({path})" if path else ""
        super().__init__(f"Character pack rejected [{code}]{location}: {message}")
        self.code = code
        self.path = path


def _read_verified_file(root: Path, record: CharacterPackFile) -> bytes:
    candidate = root.joinpath(*PurePosixPath(record.path).parts)
    _require_contained_path(root, candidate, record.path)
    metadata = candidate.stat(follow_symlinks=False)
    if not stat.S_ISREG(metadata.st_mode) or metadata.st_size != record.bytes:
        raise CharacterPackReadError(
            "size_mismatch",
            "A character asset no longer matches the validated byte count.",
            record.path,
        )
    data = candidate.read_bytes()
    if hashlib.sha256(data).hexdigest() != record.sha256:
        raise CharacterPackReadError(
            "file_hash_mismatch",
            "A character asset no longer matches the validated SHA-256.",
            record.path,
        )
    return data


def _require_contained_path(root: Path, candidate: Path, name: str) -> None:
    if candidate.is_symlink() or candidate.is_junction():
        raise CharacterPackReadError(
            "unsafe_path",
            "Character asset paths cannot use symbolic links or junctions.",
            name,
        )
    try:
        resolved = candidate.resolve(strict=True)
    except OSError:
        raise CharacterPackReadError(
            "missing_file",
            "A validated character asset is no longer present.",
            name,
        ) from None
    if not resolved.is_relative_to(root):
        raise CharacterPackReadError(
            "unsafe_path",
            "A character asset path escapes the validated package root.",
            name,
        )
    for ancestor in candidate.parents:
        if ancestor == root:
            break
        if ancestor.is_symlink() or ancestor.is_junction():
            raise CharacterPackReadError(
                "unsafe_path",
                "Character asset ancestors cannot use symbolic links or junctions.",
                name,
            )


def _relative_path(value: str) -> PurePosixPath:
    if not isinstance(value, str) or not value or "\\" in value:
        raise CharacterPackReadError(
            "unsafe_path",
            "Character asset paths must use relative POSIX syntax.",
        )
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise CharacterPackReadError(
            "unsafe_path",
            "Character asset paths must use canonical relative syntax.",
            value,
        )
    return path


__all__ = ("CharacterPackReadError",)
