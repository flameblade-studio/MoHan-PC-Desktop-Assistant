"""Atomic installation for validated per-user body packs."""

from __future__ import annotations

lazy from dataclasses import dataclass
lazy from pathlib import Path

lazy from domain.body_pack import (
    BodyPackMismatchError,
    BodyPackReference,
    parse_body_pack_reference,
)
lazy from infrastructure.body_pack_reader import BodyPackReader
lazy from infrastructure.platform_services import resolved_data_dir

BODY_PACKS_DIRECTORY = "body-packs"
MOHAN_BODY_PACK_ID = "mohan-body-v2"


class BodyPackInstallError(RuntimeError):
    """A staged body pack could not be validated or published safely."""


@dataclass(frozen=True, slots=True)
class BodyPackInstallation:
    """Measured identity and location of one installed body pack."""

    path: Path
    pack_id: str
    pack_version: str
    fingerprint: str
    checked_files: int
    checked_bytes: int


def installed_body_pack_root(data_root: str | Path | None = None) -> Path:
    """Return the per-user body-pack directory beside the application profile."""

    root = resolved_data_dir() if data_root is None else Path(data_root)
    return root.expanduser() / BODY_PACKS_DIRECTORY


def installed_body_pack_path(
    pack_id: str = MOHAN_BODY_PACK_ID,
    *,
    data_root: str | Path | None = None,
) -> Path:
    """Return the deterministic userdata path for one safe body-pack ID."""

    if (
        not isinstance(pack_id, str)
        or not pack_id
        or not pack_id.isascii()
        or any(not (character.islower() or character.isdigit() or character in "._-") for character in pack_id)
        or pack_id[0] in "._-"
        or pack_id[-1] in "._-"
        or ".." in pack_id
    ):
        raise BodyPackInstallError("Body-pack IDs must use lowercase ASCII letters, digits, dots, underscores, or hyphens.")
    return installed_body_pack_root(data_root) / pack_id


def install_staged_body_pack(
    staged_directory: str | Path,
    reference: BodyPackReference,
    *,
    data_root: str | Path | None = None,
) -> BodyPackInstallation:
    """Validate a complete body pack and atomically publish it without overwrite."""

    expected = parse_body_pack_reference(reference)
    root = installed_body_pack_root(data_root)
    try:
        root.mkdir(parents=True, exist_ok=True)
        if root.is_symlink() or root.is_junction():
            raise BodyPackInstallError("The per-user body-pack directory cannot be a link.")
        resolved_root = root.resolve(strict=True)
        staged = Path(staged_directory)
        if staged.is_symlink() or staged.is_junction() or not staged.is_dir():
            raise BodyPackInstallError("The staged body pack must be a regular directory.")
        resolved_staged = staged.resolve(strict=True)
        if not resolved_staged.is_relative_to(resolved_root):
            raise BodyPackInstallError("The staged body pack must stay on the userdata body-pack volume.")
        destination = resolved_root / expected.id
        if destination.exists() or destination.is_symlink() or destination.is_junction():
            raise BodyPackInstallError(
                f"Body pack {expected.id!r} is already installed at {destination}."
            )
        reader = BodyPackReader(resolved_staged, expected)
        records = {}
        for view in (*reader.manifest.full_body, *reader.manifest.half_body):
            for _state, record in view.frames:
                records[record.path] = record
        for _view_id, record in reader.manifest.face_core_masks:
            records[record.path] = record
        checked_bytes = (resolved_staged / "manifest.json").stat().st_size
        for record in records.values():
            reader.read_image(record)
            checked_bytes += resolved_staged.joinpath(*record.path.split("/")).stat().st_size
        if destination.exists() or destination.is_symlink() or destination.is_junction():
            raise BodyPackInstallError("The body-pack destination appeared during validation.")
        try:
            resolved_staged.rename(destination)
        except OSError as error:
            raise BodyPackInstallError("The validated body pack could not be published atomically.") from error
    except BodyPackInstallError:
        raise
    except BodyPackMismatchError as error:
        path = f" path={error.path}" if error.path else ""
        raise BodyPackInstallError(f"Body pack rejected [{error.code}]{path}: {error}") from error
    except OSError as error:
        raise BodyPackInstallError("The body pack could not be installed safely.") from error

    return BodyPackInstallation(
        destination,
        reader.manifest.id,
        reader.manifest.version,
        reader.manifest.fingerprint,
        len(records) + 1,
        checked_bytes,
    )


__all__ = (
    "BODY_PACKS_DIRECTORY",
    "MOHAN_BODY_PACK_ID",
    "BodyPackInstallError",
    "BodyPackInstallation",
    "install_staged_body_pack",
    "installed_body_pack_path",
    "installed_body_pack_root",
)
