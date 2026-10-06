"""Bounded, read-only directory and ZIP access for character packs."""
from __future__ import annotations

lazy import stat
lazy import os
lazy import struct
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
WINDOWS_RESERVED = frozenset({
    "con", "prn", "aux", "nul",
    *(f"{prefix}{number}" for prefix in ("com", "lpt") for number in "123456789\u00b9\u00b2\u00b3"),
})
CONTROL_CHARACTER_BOUNDARY = 32
ZIP_END_BYTES = 22
ZIP_MAX_COMMENT_BYTES = 65535
ZIP_CENTRAL_HEADER_BYTES = 46
ZIP64_SIZE_SENTINEL = 0xFFFFFFFF


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
        identities: dict[str, os.stat_result] = {}
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
            metadata = entry.stat(follow_symlinks=False)
            if not stat.S_ISREG(metadata.st_mode):
                raise _ValidationFailure("unsafe_path", "Character packs contain regular files only.")
            size = metadata.st_size
            if size > limits.max_file_bytes and name != MANIFEST_PATH:
                raise _ValidationFailure("file_too_large", "A package file exceeds the configured size limit.", name)
            files[name] = entry
            identities[name] = metadata
            total_bytes += size
            _validate_inventory_limits(files, total_bytes, limits)
        _validate_inventory_limits(files, total_bytes, limits)
        self._files = files
        self._identities = identities

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
            _check_opened_file(self._root, candidate, stream, self._identities[path], path)
            data = _read_limited(stream, limit, path)
            _check_opened_file(self._root, candidate, stream, self._identities[path], path)
            return data

    def declared_size(self, path: str) -> int:
        candidate = self._files[path]
        _check_directory_path(self._root, candidate)
        metadata = candidate.stat(follow_symlinks=False)
        _require_same_file(self._identities[path], metadata, path)
        return metadata.st_size


class _ZipReader(_PackageReader):
    source_kind = "zip"

    def __init__(self, source: Path, limits: ValidationLimits) -> None:
        self._stream = source.open("rb")
        try:
            _preflight_zip_directory(self._stream, limits)
            try:
                self._archive = zipfile.ZipFile(self._stream)
            except (OSError, zipfile.BadZipFile):
                raise _ValidationFailure("invalid_archive", "Use a readable ZIP character pack.") from None
        except BaseException:
            self._stream.close()
            raise
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
                if (file_type == stat.S_IFDIR and not info.is_dir()) or (file_type == stat.S_IFREG and info.is_dir()):
                    raise _ValidationFailure("invalid_archive", "ZIP names and declared entry types must agree.", name)
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
            _validate_zip_hierarchy(infos, folded_names)
        except BaseException:
            self._archive.close()
            self._stream.close()
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
        self._stream.close()


def _preflight_zip_directory(stream: IO[bytes], limits: ValidationLimits) -> None:
    """Bound ZIP index allocation before ZipFile constructs its in-memory index.

    v1 supports single-disk ZIPs with a classic end record. Count actual central
    headers as well as the declared count, so a forged count cannot bypass the
    ceiling. Variable metadata is skipped rather than allocated.
    """
    stream.seek(0, 2)
    archive_size = stream.tell()
    if archive_size > limits.max_archive_bytes:
        raise _ValidationFailure("archive_too_large", "The archive exceeds the configured size limit.")
    tail_start = max(0, archive_size - ZIP_END_BYTES - ZIP_MAX_COMMENT_BYTES)
    stream.seek(tail_start)
    tail = stream.read(ZIP_END_BYTES + ZIP_MAX_COMMENT_BYTES)
    position = tail.rfind(b"PK\x05\x06")
    if position < 0 or len(tail) - position < ZIP_END_BYTES:
        raise _ValidationFailure("invalid_archive", "The ZIP end record is missing or truncated.")
    _, disk, directory_disk, disk_count, count, size, offset, comment_size = struct.unpack_from("<4s4H2IH", tail, position)
    if disk or directory_disk or disk_count != count or count == ZIP_MAX_COMMENT_BYTES or ZIP64_SIZE_SENTINEL in {size, offset}:
        raise _ValidationFailure("invalid_archive", "Use a single-disk ZIP with a classic end record; ZIP64 is unsupported.")
    if count > limits.max_files:
        raise _ValidationFailure("too_many_files", "The ZIP entry count exceeds the configured limit.")
    if size > limits.max_zip_directory_bytes:
        raise _ValidationFailure("zip_directory_too_large", "The ZIP central metadata exceeds the configured limit.")
    end_position = tail_start + position
    if position + ZIP_END_BYTES + comment_size != len(tail) or offset + size != end_position:
        raise _ValidationFailure("invalid_archive", "The ZIP directory and end-record bounds must agree.")
    stream.seek(offset)
    actual_count = 0
    while stream.tell() < end_position:
        header = stream.read(ZIP_CENTRAL_HEADER_BYTES)
        if len(header) != ZIP_CENTRAL_HEADER_BYTES or header[:4] != b"PK\x01\x02":
            raise _ValidationFailure("invalid_archive", "The ZIP central directory is malformed.")
        actual_count += 1
        if actual_count > limits.max_files:
            raise _ValidationFailure("too_many_files", "The actual ZIP entry count exceeds the configured limit.")
        name_size, extra_size, entry_comment_size = struct.unpack_from("<HHH", header, 28)
        stream.seek(name_size + extra_size + entry_comment_size, 1)
        if stream.tell() > end_position:
            raise _ValidationFailure("invalid_archive", "A ZIP central entry escapes the directory bounds.")
    if actual_count != count:
        raise _ValidationFailure("invalid_archive", "The ZIP central entry count differs from its end record.")


def _open_reader(source: Path, limits: ValidationLimits) -> _PackageReader:
    if source.is_symlink() or source.is_junction():
        raise _ValidationFailure("unsafe_path", "The character-pack source cannot be a symbolic link.")
    if source.is_dir():
        return _DirectoryReader(source, limits)
    if source.is_file():
        return _ZipReader(source, limits)
    raise _ValidationFailure("source_not_found", "Provide an existing character-pack directory or ZIP.")


def _validate_zip_hierarchy(files: Mapping[str, object], entries: set[str]) -> None:
    """Require a hierarchy that can also exist as a regular directory pack."""
    folded_files = {_fold_path(name) for name in files}
    for name in sorted(entries):
        for parent in PurePosixPath(name).parents:
            if parent.as_posix() in folded_files:
                raise _ValidationFailure("unsafe_path", "A ZIP file cannot also be a parent directory.", name)


def _directory_entries(root: Path, limits: ValidationLimits) -> Iterator[Path]:
    count = 0
    pending = [root]
    while pending:
        parent = pending.pop()
        with os.scandir(parent) as entries:
            for item in entries:
                count += 1
                if count > limits.max_files:
                    raise _ValidationFailure("too_many_files", "The directory entry count exceeds the configured limit.")
                entry = parent / item.name
                _check_directory_path(root, entry)
                if item.is_dir(follow_symlinks=False):
                    pending.append(entry)
                yield entry


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


def _check_opened_file(
    root: Path,
    candidate: Path,
    stream: IO[bytes],
    expected: os.stat_result,
    path: str,
) -> None:
    """Bind a directory entry to the regular file inventoried before reading."""
    _check_directory_path(root, candidate)
    opened = os.fstat(stream.fileno())
    current = candidate.stat(follow_symlinks=False)
    _require_same_file(expected, opened, path)
    _require_same_file(opened, current, path)


def _require_same_file(expected: os.stat_result, actual: os.stat_result, path: str) -> None:
    if (
        not stat.S_ISREG(actual.st_mode)
        or expected.st_dev != actual.st_dev
        or expected.st_ino != actual.st_ino
    ):
        raise _ValidationFailure(
            "unsafe_path",
            "A package file changed identity while it was being validated.",
            path,
        )


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
