"""Bounded, read-only directory and ZIP access for character packs."""
from __future__ import annotations

lazy import stat
lazy import unicodedata
lazy import zipfile
lazy import zlib
lazy import lzma
lazy from collections.abc import Iterator, Mapping
lazy from contextlib import AbstractContextManager
lazy from pathlib import Path, PurePosixPath
lazy from typing import IO, Self
lazy from domain.character_pack.models import ValidationLimits

MANIFEST_PATH = "manifest.json"
MAX_PATH_LENGTH = 512
READ_CHUNK_BYTES = 64 * 1024
WINDOWS_RESERVED = frozenset({"con", "prn", "aux", "nul", *(f"com{i}" for i in range(1, 10)), *(f"lpt{i}" for i in range(1, 10))})
CONTROL_CHARACTER_BOUNDARY = 32


class _ValidationFailure(ValueError):
    def __init__(self, code: str, message: str, path: str | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.path = path


class _PackageReader(AbstractContextManager["_PackageReader"]):
    source_kind: str

    @property
    def names(self) -> frozenset[str]:
        raise NotImplementedError

    def read(self, path: str, limit: int) -> bytes:
        raise NotImplementedError

    def declared_size(self, path: str) -> int:
        raise NotImplementedError

    def __enter__(self) -> Self:
        return self

    def __exit__(self, _exc_type: object, _exc: object, _traceback: object) -> None:
        return None


class _DirectoryReader(_PackageReader):
    source_kind = "directory"

    def __init__(self, root: Path, limits: ValidationLimits) -> None:
        self._root = root.resolve(strict=True)
        root = self._root
        files: dict[str, Path] = {}
        folded_names: set[str] = set()
        total_bytes = 0
        for entry in _directory_entries(root, limits):
            name = entry.relative_to(root).as_posix()
            _validate_safe_path(name)
            folded = _fold_path(name)
            if folded in folded_names:
                raise _ValidationFailure("duplicate_path", "Package paths must remain unique across platforms.", name)
            folded_names.add(folded)
            if entry.is_dir():
                continue
            if not entry.is_file():
                raise _ValidationFailure("unsafe_path", "Character packs contain regular files only.")
            size = entry.stat().st_size
            if size > limits.max_file_bytes and name != MANIFEST_PATH:
                raise _ValidationFailure("file_too_large", "A package file exceeds the configured size limit.", name)
            files[name] = entry
            total_bytes += size
            _validate_inventory_limits(files, total_bytes, limits)
        _validate_inventory_limits(files, total_bytes, limits)
        self._files = files

    @property
    def names(self) -> frozenset[str]:
        return frozenset(self._files)

    def read(self, path: str, limit: int) -> bytes:
        try:
            candidate = self._files[path]
        except KeyError:
            raise _ValidationFailure("missing_file", "A declared package file is missing.", path) from None
        _check_directory_path(self._root, candidate)
        with candidate.open("rb") as stream:
            return _read_limited(stream, limit, path)

    def declared_size(self, path: str) -> int:
        candidate = self._files[path]
        _check_directory_path(self._root, candidate)
        return candidate.stat().st_size


class _ZipReader(_PackageReader):
    source_kind = "zip"

    def __init__(self, source: Path, limits: ValidationLimits) -> None:
        if source.stat().st_size > limits.max_archive_bytes:
            raise _ValidationFailure("archive_too_large", "The archive exceeds the configured size limit.")
        try:
            self._archive = zipfile.ZipFile(source)
        except (OSError, zipfile.BadZipFile):
            raise _ValidationFailure("invalid_archive", "Use a readable ZIP character pack.") from None
        infos: dict[str, zipfile.ZipInfo] = {}
        folded_names: set[str] = set()
        total_bytes = 0
        try:
            for info in self._archive.infolist():
                name = info.filename
                _validate_safe_path(info.orig_filename.removesuffix("/") if info.is_dir() else info.orig_filename)
                _validate_safe_path(name.removesuffix("/") if info.is_dir() else name)
                folded = _fold_path(name.removesuffix("/"))
                if name in infos or folded in folded_names:
                    raise _ValidationFailure(
                        "duplicate_path",
                        "Package paths must remain unique across platforms.",
                        name,
                    )
                if info.flag_bits & 1:
                    raise _ValidationFailure("encrypted_member", "Encrypted ZIP members are not supported.", name)
                file_type = (info.external_attr >> 16) & 0o170000
                if file_type not in {0, stat.S_IFREG, stat.S_IFDIR}:
                    raise _ValidationFailure("unsafe_path", "ZIP entries must be regular files or directories.", name)
                folded_names.add(folded)
                if len(folded_names) > limits.max_files:
                    raise _ValidationFailure("too_many_files", "The ZIP entry count exceeds the configured limit.")
                if info.is_dir():
                    if info.file_size:
                        raise _ValidationFailure("invalid_archive", "ZIP directories must contain no payload.", name)
                    continue
                if info.file_size > limits.max_file_bytes and name != MANIFEST_PATH:
                    raise _ValidationFailure("file_too_large", "A package file exceeds the configured size limit.", name)
                if info.file_size / max(1, info.compress_size) > limits.max_compression_ratio:
                    raise _ValidationFailure(
                        "suspicious_compression_ratio",
                        "A ZIP member exceeds the configured compression ratio.",
                        name,
                    )
                infos[name] = info
                total_bytes += info.file_size
                _validate_inventory_limits(infos, total_bytes, limits)
            _validate_inventory_limits(infos, total_bytes, limits)
        except BaseException:
            self._archive.close()
            raise
        self._infos = infos

    @property
    def names(self) -> frozenset[str]:
        return frozenset(self._infos)

    def read(self, path: str, limit: int) -> bytes:
        try:
            info = self._infos[path]
        except KeyError:
            raise _ValidationFailure("missing_file", "A declared package file is missing.", path) from None
        try:
            with self._archive.open(info) as stream:
                data = _read_limited(stream, limit, path)
        except (OSError, RuntimeError, NotImplementedError, EOFError, zipfile.BadZipFile, zlib.error, lzma.LZMAError):
            raise _ValidationFailure("invalid_archive", "A ZIP member could not be read safely.", path) from None
        if len(data) != info.file_size:
            raise _ValidationFailure("size_mismatch", "A ZIP member size does not match its directory entry.", path)
        return data

    def declared_size(self, path: str) -> int:
        return self._infos[path].file_size

    def __exit__(self, _exc_type: object, _exc: object, _traceback: object) -> None:
        self._archive.close()


def _open_reader(source: Path, limits: ValidationLimits) -> _PackageReader:
    if source.is_symlink() or source.is_junction():
        raise _ValidationFailure("unsafe_path", "The character-pack source cannot be a symbolic link.")
    if source.is_dir():
        return _DirectoryReader(source, limits)
    if source.is_file():
        return _ZipReader(source, limits)
    raise _ValidationFailure("source_not_found", "Provide an existing character-pack directory or ZIP.")


def _directory_entries(root: Path, limits: ValidationLimits) -> Iterator[Path]:
    count = 0
    for parent, directories, filenames in root.walk(on_error=_raise_walk_error):
        for name in (*directories, *filenames):
            count += 1
            if count > limits.max_files:
                raise _ValidationFailure("too_many_files", "The directory entry count exceeds the configured limit.")
            entry = parent / name
            _check_directory_path(root, entry)
            yield entry


def _raise_walk_error(error: OSError) -> None:
    raise error


def _check_directory_path(root: Path, candidate: Path) -> None:
    if candidate.is_symlink() or candidate.is_junction():
        raise _ValidationFailure("unsafe_path", "Package paths must contain regular directories and files.")
    resolved = candidate.resolve(strict=True)
    if not resolved.is_relative_to(root):
        raise _ValidationFailure("unsafe_path", "A character-pack path escapes the package root.")
    for ancestor in candidate.parents:
        if ancestor == root:
            break
        if ancestor.is_symlink() or ancestor.is_junction():
            raise _ValidationFailure("unsafe_path", "Package ancestors must contain regular directories.")


def _validate_inventory_limits(inventory: Mapping[str, object], total_bytes: int, limits: ValidationLimits) -> None:
    if not inventory or len(inventory) > limits.max_files:
        raise _ValidationFailure("too_many_files", "The package file count is outside the configured limit.")
    if total_bytes > limits.max_total_bytes:
        raise _ValidationFailure("package_too_large", "The package expands beyond the configured total size.")


def _validate_safe_path(value: object) -> str:
    if not isinstance(value, str) or not value or len(value) > MAX_PATH_LENGTH:
        raise _ValidationFailure("unsafe_path", "Package paths must be non-empty UTF-8 strings.")
    if value != unicodedata.normalize("NFC", value):
        raise _ValidationFailure("unsafe_path", "Package paths must use NFC Unicode normalization.", value)
    path = PurePosixPath(value)
    parts = value.split("/")
    if (
        path.is_absolute()
        or "\\" in value
        or "\0" in value
        or ":" in value
        or any(part in {"", ".", ".."} for part in parts)
        or any(ord(character) < CONTROL_CHARACTER_BOUNDARY or character in '<>"|?*' for character in value)
        or any(part.endswith((".", " ")) or part.split(".", 1)[0].casefold() in WINDOWS_RESERVED for part in parts)
    ):
        raise _ValidationFailure("unsafe_path", "Package paths must stay relative to the package root.", value)
    return value


def _fold_path(value: str) -> str:
    return unicodedata.normalize("NFC", value).casefold()


def _read_limited(stream: IO[bytes], limit: int, path: str) -> bytes:
    chunks: list[bytes] = []
    total = 0
    while chunk := stream.read(min(READ_CHUNK_BYTES, limit + 1 - total)):
        chunks.append(chunk)
        total += len(chunk)
        if total > limit:
            raise _ValidationFailure("file_too_large", "A package file exceeds the configured read limit.", path)
    return b"".join(chunks)
