"""Read-only loader for a hash-bound body pack installed beside character packs."""

from __future__ import annotations

lazy import hashlib
lazy import json
lazy import logging
lazy import os
lazy import stat
lazy import warnings
lazy from collections import OrderedDict
lazy from collections.abc import Iterable, Mapping
lazy from dataclasses import dataclass
lazy from io import BytesIO
lazy from pathlib import Path, PurePosixPath
lazy from threading import RLock

lazy from PIL import Image, UnidentifiedImageError
lazy from domain.body_pack import (
    BodyPackError,
    BodyPackFile,
    BodyPackManifest,
    BodyPackMismatchError,
    BodyPackReference,
    parse_body_pack,
    parse_body_pack_reference,
)
lazy from domain.character_pack.character_data_models import CharacterRigManifest
lazy from domain.character_layer_plan import CharacterLayerPlan
lazy from domain.character_pose import canonical_view_id
lazy from domain.character_source import CharacterCanvas

LOGGER = logging.getLogger(__name__)
MANIFEST_PATH = "manifest.json"
MAX_MANIFEST_BYTES = 1024 * 1024
MAX_IMAGE_BYTES = 64 * 1024 * 1024
MAX_CACHED_IMAGE_BYTES = 16 * 1024 * 1024
_PNG_IHDR_MIN_BYTES = 33
_PNG_IHDR_CHUNK_BYTES = 13
_PNG_COLOR_TYPE_RGBA = 6
_FileSignature = tuple[int, int, int, int, int, int]


@dataclass(frozen=True, slots=True)
class _PayloadCacheEntry:
    data: bytes
    signature: _FileSignature


class BodyPackReader:
    """Validate a body-pack manifest and every referenced PNG without mutation."""

    def __init__(self, root: str | Path, reference: BodyPackReference) -> None:
        self._reference = parse_body_pack_reference(reference)
        requested_root = Path(root)
        manifest_candidate = requested_root / MANIFEST_PATH
        try:
            pack_root = requested_root.resolve(strict=True)
            manifest_path = manifest_candidate.resolve(strict=True)
        except OSError:
            raise _mismatch(
                "body_pack_missing",
                "The declared body-pack directory and manifest must both exist.",
                self._reference.id,
            ) from None
        if (
            requested_root.is_symlink()
            or requested_root.is_junction()
            or not pack_root.is_dir()
            or not manifest_path.is_relative_to(pack_root)
            or manifest_candidate.is_symlink()
            or manifest_candidate.is_junction()
        ):
            raise _mismatch(
                "unsafe_path",
                "The body-pack root and manifest must be contained regular paths.",
                self._reference.id,
            )
        self._root = pack_root
        manifest_bytes = _read_manifest(self._root, manifest_candidate)
        try:
            raw_manifest = json.loads(
                manifest_bytes.decode("utf-8"),
                object_pairs_hook=_unique_object,
                parse_constant=_reject_json_constant,
            )
            if not isinstance(raw_manifest, Mapping):
                raise BodyPackError("manifest.json must contain a JSON object.")
            self._manifest = parse_body_pack(raw_manifest, self._reference)
        except BodyPackMismatchError as error:
            _log_rejection(error.code, str(error), error.path or self._reference.id)
            raise
        except (BodyPackError, UnicodeError, ValueError, RecursionError) as error:
            raise _mismatch(
                "invalid_manifest",
                f"The body-pack manifest violates its contract: {type(error).__name__}.",
                MANIFEST_PATH,
            ) from None

        self._full_frames = _frame_map(self._manifest.full_body)
        self._half_frames = _frame_map(self._manifest.half_body)
        self._face_core = dict(self._manifest.face_core_masks)
        self._declared_records = _unique_records(
            (
                *(
                    record
                    for frames in self._full_frames.values()
                    for record in frames.values()
                ),
                *(
                    record
                    for frames in self._half_frames.values()
                    for record in frames.values()
                ),
                *self._face_core.values(),
            )
        )
        self._image_sizes: dict[str, tuple[int, int]] = {}
        self._decoded_image_signatures: dict[str, _FileSignature] = {}
        self._payload_cache: OrderedDict[str, _PayloadCacheEntry] = OrderedDict()
        self._payload_cache_size = 0
        self._payload_cache_lock = RLock()

        for record in self._declared_records.values():
            self._inspect_image(record)

        full_sizes = self._frame_sizes(self._full_frames)
        if not full_sizes:
            raise _mismatch(
                "missing_frame",
                "The body pack must contain at least one full-body frame.",
                MANIFEST_PATH,
            )
        if len(full_sizes) != 1:
            expected_size = next(iter(full_sizes))
            bad_record = next(
                record
                for frames in self._full_frames.values()
                for record in frames.values()
                if self._image_sizes[record.path] != expected_size
            )
            raise _mismatch(
                "image_dimensions_mismatch",
                "Every full-body frame must use one canvas size.",
                bad_record.path,
            )
        full_canvas = next(iter(full_sizes))

        half_sizes = self._frame_sizes(self._half_frames)
        if not half_sizes:
            raise _mismatch(
                "missing_frame",
                "The body pack must contain at least one half-body frame.",
                MANIFEST_PATH,
            )
        if len(half_sizes) != 1:
            expected_size = next(iter(half_sizes))
            bad_record = next(
                record
                for frames in self._half_frames.values()
                for record in frames.values()
                if self._image_sizes[record.path] != expected_size
            )
            raise _mismatch(
                "image_dimensions_mismatch",
                "Every half-body frame must use one canvas size.",
                bad_record.path,
            )
        half_canvas = next(iter(half_sizes))
        for view, record in self._face_core.items():
            in_full_body = view in self._full_frames
            in_half_body = view in self._half_frames
            if not in_full_body and not in_half_body:
                raise _mismatch(
                    "unknown_face_core_view",
                    "A face-core mask must match a declared full- or half-body view.",
                    view,
                )
            if in_full_body and in_half_body and full_canvas != half_canvas:
                raise _mismatch(
                    "ambiguous_face_core_view",
                    "A face-core mask view used by both body canvases has ambiguous dimensions.",
                    view,
                )
            expected_canvas = half_canvas if in_half_body and not in_full_body else full_canvas
            if self._image_sizes[record.path] != expected_canvas:
                raise _mismatch(
                    "image_dimensions_mismatch",
                    "A face-core mask must use the canvas dimensions for its declared view.",
                    record.path,
                )
        self._fullbody_canvas = full_canvas
        self._halfbody_canvas = half_canvas

    def _frame_sizes(self, views: Mapping[str, Mapping[str, BodyPackFile]]) -> set[tuple[int, int]]:
        sizes: set[tuple[int, int]] = set()
        for frames in views.values():
            sizes.update(self._image_sizes[record.path] for record in frames.values())
        return sizes

    @property
    def manifest(self) -> BodyPackManifest:
        return self._manifest

    @property
    def reference(self) -> BodyPackReference:
        return self._reference

    @property
    def fullbody_canvas(self) -> tuple[int, int]:
        return self._fullbody_canvas

    @property
    def halfbody_canvas(self) -> tuple[int, int]:
        return self._halfbody_canvas

    def frame_keys(self, view: str, *, halfbody: bool = False) -> tuple[str, ...]:
        """Return the declared state keys for one full- or half-body view."""
        frames = self._select_view(view, halfbody=halfbody)
        return tuple(frames)

    def load_frame(self, view: str, key: str, *, halfbody: bool = False) -> bytes:
        """Read one verified body frame, rejecting absent views and states."""
        frames = self._select_view(view, halfbody=halfbody)
        record = frames.get(key)
        if record is None:
            raise _mismatch(
                "missing_frame",
                "The body pack does not declare the requested frame state.",
                f"{view}/{key}",
            )
        return self.read_image(record)

    def load_face_core(self, view: str) -> bytes | None:
        """Read a verified face-core mask for a declared body view when present."""
        record = self._face_core.get(view)
        return None if record is None else self.read_image(record)

    def read_image(self, record: BodyPackFile) -> bytes:
        """Read a verified image, decoding its PNG only on first use."""
        declared = self._declared_records.get(record.path)
        if declared != record:
            raise _mismatch(
                "undeclared_path",
                "The requested image record is not part of this body pack.",
                record.path,
            )
        data, signature = self._read_payload(record)
        if self._decoded_image_signatures.get(record.path) != signature:
            _decode_image(record, data, self._image_sizes[record.path])
            self._decoded_image_signatures[record.path] = signature
        return data

    def _select_view(self, view: str, *, halfbody: bool) -> Mapping[str, BodyPackFile]:
        groups = self._half_frames if halfbody else self._full_frames
        try:
            return groups[view]
        except KeyError:
            raise _mismatch(
                "missing_view",
                "The body pack does not declare the requested view.",
                view,
            ) from None

    def _inspect_image(self, record: BodyPackFile) -> tuple[int, int]:
        data, _ = self._read_payload(record)
        size = _png_size(data, record.path)
        self._image_sizes[record.path] = size
        return size

    def _read_payload(self, record: BodyPackFile) -> tuple[bytes, _FileSignature]:
        """Read/hash once and retain verified bytes within the reader budget."""
        candidate = self._root.joinpath(*PurePosixPath(record.path).parts)
        with self._payload_cache_lock:
            _require_contained_path(self._root, candidate, record.path)
            try:
                metadata = candidate.stat(follow_symlinks=False)
            except OSError:
                raise _mismatch(
                    "missing_file", "A declared body-pack image is missing.", record.path
                ) from None
            if not stat.S_ISREG(metadata.st_mode):
                raise _mismatch(
                    "unsafe_path", "Body-pack assets must be regular files.", record.path
                )
            if metadata.st_size > MAX_IMAGE_BYTES:
                raise _mismatch(
                    "file_too_large", "A body-pack image exceeds the read limit.", record.path
                )

            cached = self._payload_cache.get(record.path)
            state_changed = False
            try:
                with candidate.open("rb") as stream:
                    opened = os.fstat(stream.fileno())
                    _require_same_file(metadata, opened, record.path)
                    signature = _file_signature(opened)
                    if cached is not None and signature == cached.signature:
                        current = candidate.stat(follow_symlinks=False)
                        _require_same_file(metadata, current, record.path)
                        confirmed = os.fstat(stream.fileno())
                        if (
                            _same_file_state(current, confirmed)
                            and _file_signature(confirmed) == cached.signature
                        ):
                            self._payload_cache.move_to_end(record.path)
                            return cached.data, cached.signature

                    if cached is not None:
                        self._discard_cached_payload(record.path)
                    data = stream.read(MAX_IMAGE_BYTES + 1)
                    after_read = os.fstat(stream.fileno())
                    after_path = candidate.stat(follow_symlinks=False)
                    _require_same_file(metadata, after_read, record.path)
                    _require_same_file(metadata, after_path, record.path)
                    state_changed = (
                        _file_signature(opened) != _file_signature(after_read)
                        or not _same_file_state(metadata, opened)
                        or not _same_file_state(after_read, after_path)
                    )
            except BodyPackMismatchError:
                raise
            except OSError as error:
                raise _mismatch(
                    "missing_file",
                    f"A declared body-pack image could not be read: {type(error).__name__}.",
                    record.path,
                ) from None

            if len(data) > MAX_IMAGE_BYTES or len(data) != metadata.st_size:
                raise _mismatch(
                    "size_mismatch",
                    "A body-pack image changed while it was read.",
                    record.path,
                )
            if hashlib.sha256(data).hexdigest() != record.sha256:
                raise _mismatch(
                    "file_hash_mismatch",
                    "A body-pack image does not match its declared SHA-256.",
                    record.path,
                )
            if state_changed:
                raise _mismatch(
                    "file_changed",
                    "A body-pack image changed while it was read.",
                    record.path,
                )

            signature = _file_signature(opened)
            if len(data) <= MAX_CACHED_IMAGE_BYTES:
                self._remember_payload(record.path, data, signature)
            return data, signature

    def _remember_payload(
        self,
        path: str,
        data: bytes,
        signature: _FileSignature,
    ) -> None:
        previous = self._payload_cache.pop(path, None)
        if previous is not None:
            self._payload_cache_size -= len(previous.data)
        if len(data) > MAX_CACHED_IMAGE_BYTES:
            return
        self._payload_cache[path] = _PayloadCacheEntry(data, signature)
        self._payload_cache_size += len(data)
        while self._payload_cache_size > MAX_CACHED_IMAGE_BYTES:
            _, evicted = self._payload_cache.popitem(last=False)
            self._payload_cache_size -= len(evicted.data)

    def _discard_cached_payload(self, path: str) -> None:
        previous = self._payload_cache.pop(path, None)
        if previous is not None:
            self._payload_cache_size -= len(previous.data)


def resolve_body_pack(
    reference: BodyPackReference,
    roots: Iterable[str | Path],
) -> BodyPackReader:
    """Resolve ``root/<id>/manifest.json`` from the configured roots, read-only."""
    expected = parse_body_pack_reference(reference)
    for raw_root in roots:
        root = Path(raw_root)
        candidate = root / expected.id
        if candidate.exists() or candidate.is_symlink() or candidate.is_junction():
            return BodyPackReader(candidate, expected)
    raise _mismatch(
        "body_pack_missing",
        "No configured body-pack root contains the declared pack ID.",
        expected.id,
    )


def validate_body_pack_binding(
    body_pack: BodyPackReader,
    *,
    expected_full_canvas: tuple[int, int],
    expected_half_canvas: tuple[int, int],
    required_view_ids: tuple[str, ...],
    layer_views: Mapping[str, CharacterLayerPlan],
) -> None:
    """Check the resolved pack against its character rig and layer plans."""
    manifest = body_pack.manifest
    if body_pack.fullbody_canvas != expected_full_canvas:
        raise _mismatch(
            "incompatible_canvas",
            "The body-pack full-body canvas does not match the character rig.",
        )
    if body_pack.halfbody_canvas != expected_half_canvas:
        raise _mismatch(
            "incompatible_canvas",
            "The body-pack half-body canvas does not match the character rig.",
        )

    full_view_ids = {view.view_id for view in manifest.full_body}
    half_view_ids = {view.view_id for view in manifest.half_body}
    missing_views = set(required_view_ids) - full_view_ids
    if missing_views:
        first_missing = min(missing_views)
        raise _mismatch(
            "missing_view",
            "The body pack must declare every view in the character rig view ring.",
            first_missing,
        )

    face_core_views = {view_id for view_id, _ in manifest.face_core_masks}
    for view_id, plan in layer_views.items():
        if view_id not in full_view_ids and view_id not in half_view_ids:
            raise _mismatch(
                "missing_view",
                "A character layer plan references a view absent from the body pack.",
                view_id,
            )

        if (plan.layers or plan.base_hide is not None) and view_id not in face_core_views:
            raise _mismatch(
                "missing_face_core",
                "A view with character layers requires a body-pack face-core mask.",
                view_id,
            )


@dataclass(frozen=True, slots=True)
class CharacterBodyBinding:
    resolved_body_pack: BodyPackReader | None
    fullbody_canvas: CharacterCanvas
    halfbody_canvas: CharacterCanvas
    view_ids: tuple[str, ...]


def resolve_character_body_binding(
    reference: BodyPackReference | None,
    rig: CharacterRigManifest,
    roots: Iterable[str | Path],
    layer_views: Mapping[str, CharacterLayerPlan],
) -> CharacterBodyBinding:
    """Resolve an optional body pack and bind its dimensions and views to the rig."""
    fullbody_canvas = CharacterCanvas(
        rig.full_body_canvas.width,
        rig.full_body_canvas.height,
        rig.full_body_canvas.mode,
    )
    halfbody_canvas = CharacterCanvas(
        rig.half_body_asset_canvas.width,
        rig.half_body_asset_canvas.height,
        rig.half_body_asset_canvas.mode,
    )
    view_ids = tuple(canonical_view_id(yaw) for yaw in rig.view_ring.yaws)
    resolved = resolve_body_pack(reference, roots) if reference is not None else None
    if resolved is not None:
        validate_body_pack_binding(
            resolved,
            expected_full_canvas=(fullbody_canvas.width, fullbody_canvas.height),
            expected_half_canvas=(halfbody_canvas.width, halfbody_canvas.height),
            required_view_ids=view_ids,
            layer_views=layer_views,
        )
    return CharacterBodyBinding(resolved, fullbody_canvas, halfbody_canvas, view_ids)


def _frame_map(views: tuple[object, ...]) -> dict[str, dict[str, BodyPackFile]]:
    return {
        view.view_id: dict(view.frames)
        for view in views
    }


def _unique_records(records: Iterable[BodyPackFile]) -> Mapping[str, BodyPackFile]:
    result: dict[str, BodyPackFile] = {}
    for record in records:
        previous = result.get(record.path)
        if previous is not None and previous != record:
            raise _mismatch(
                "duplicate_path",
                "One body-pack path cannot name conflicting file hashes.",
                record.path,
            )
        result[record.path] = record
    return result


def _read_manifest(root: Path, candidate: Path) -> bytes:
    _require_contained_path(root, candidate, MANIFEST_PATH)
    try:
        metadata = candidate.stat(follow_symlinks=False)
    except OSError:
        raise _mismatch("missing_file", "The body-pack manifest is missing.", MANIFEST_PATH) from None
    if not stat.S_ISREG(metadata.st_mode):
        raise _mismatch("unsafe_path", "The body-pack manifest must be a regular file.", MANIFEST_PATH)
    if metadata.st_size > MAX_MANIFEST_BYTES:
        raise _mismatch("manifest_too_large", "The body-pack manifest exceeds the read limit.", MANIFEST_PATH)
    try:
        with candidate.open("rb") as stream:
            _require_same_file(metadata, os.fstat(stream.fileno()), MANIFEST_PATH)
            data = stream.read(MAX_MANIFEST_BYTES + 1)
            _require_same_file(metadata, candidate.stat(follow_symlinks=False), MANIFEST_PATH)
    except OSError as error:
        raise _mismatch(
            "missing_file",
            f"The body-pack manifest could not be read: {type(error).__name__}.",
            MANIFEST_PATH,
        ) from None
    if len(data) > MAX_MANIFEST_BYTES or len(data) != metadata.st_size:
        raise _mismatch("size_mismatch", "The body-pack manifest changed while it was read.", MANIFEST_PATH)
    return data


def _file_signature(metadata: os.stat_result) -> _FileSignature:
    """Return a complete signature for comparisons from the same stat API."""
    return (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_mode,
        metadata.st_size,
        metadata.st_mtime_ns,
        metadata.st_ctime_ns,
    )


def _same_file_state(left: os.stat_result, right: os.stat_result) -> bool:
    """Compare fields shared by Windows path.stat() and os.fstat()."""
    return (
        left.st_dev == right.st_dev
        and left.st_ino == right.st_ino
        and left.st_mode == right.st_mode
        and left.st_size == right.st_size
        and left.st_mtime_ns == right.st_mtime_ns
    )


def _png_size(data: bytes, relative: str) -> tuple[int, int]:
    signature = b"\x89PNG\r\n\x1a\n"
    if (
        len(data) < _PNG_IHDR_MIN_BYTES
        or data[:8] != signature
        or int.from_bytes(data[8:12], "big") != _PNG_IHDR_CHUNK_BYTES
        or data[12:16] != b"IHDR"
    ):
        raise _mismatch("invalid_image", "A body-pack image must have a valid PNG header.", relative)

    width = int.from_bytes(data[16:20], "big")
    height = int.from_bytes(data[20:24], "big")
    bit_depth = data[24]
    color_type = data[25]
    compression = data[26]
    filtering = data[27]
    interlace = data[28]
    if (
        width < 1
        or height < 1
        or color_type != _PNG_COLOR_TYPE_RGBA
        or bit_depth not in {8, 16}
        or compression != 0
        or filtering != 0
        or interlace not in {0, 1}
    ):
        raise _mismatch(
            "invalid_image",
            "Body-pack images must use positive-dimension RGBA PNG encoding.",
            relative,
        )
    return width, height


def _decode_image(
    record: BodyPackFile,
    data: bytes,
    expected_size: tuple[int, int],
) -> None:
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(data)) as image:
                if image.format != "PNG" or image.mode != "RGBA" or image.size != expected_size:
                    raise _mismatch(
                        "invalid_image",
                        "Body-pack images must decode as RGBA PNGs with their declared dimensions.",
                        record.path,
                    )
                image.verify()
            with Image.open(BytesIO(data)) as image:
                if image.format != "PNG" or image.mode != "RGBA" or image.size != expected_size:
                    raise _mismatch(
                        "invalid_image",
                        "Body-pack images must decode as RGBA PNGs with their declared dimensions.",
                        record.path,
                    )
                image.load()
    except BodyPackMismatchError:
        raise
    except (
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
        OSError,
        ValueError,
        SyntaxError,
        UnidentifiedImageError,
    ) as error:
        raise _mismatch(
            "invalid_image",
            f"A body-pack image could not be decoded safely: {type(error).__name__}.",
            record.path,
        ) from None


def _require_contained_path(root: Path, candidate: Path, relative: str) -> None:
    if candidate.is_symlink() or candidate.is_junction():
        raise _mismatch("unsafe_path", "Body-pack assets cannot use symbolic links or junctions.", relative)
    try:
        resolved = candidate.resolve(strict=True)
    except OSError:
        raise _mismatch("missing_file", "A declared body-pack path is missing.", relative) from None
    if not resolved.is_relative_to(root):
        raise _mismatch("unsafe_path", "A body-pack path escapes the pack root.", relative)
    for ancestor in candidate.parents:
        if ancestor == root:
            break
        if ancestor.is_symlink() or ancestor.is_junction():
            raise _mismatch("unsafe_path", "Body-pack asset ancestors cannot be links.", relative)


def _require_same_file(expected: os.stat_result, actual: os.stat_result, relative: str) -> None:
    if (
        not stat.S_ISREG(actual.st_mode)
        or expected.st_dev != actual.st_dev
        or expected.st_ino != actual.st_ino
    ):
        raise _mismatch("unsafe_path", "A body-pack file changed identity while being read.", relative)


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise BodyPackError("manifest JSON object keys must be unique.")
        result[key] = value
    return result


def _reject_json_constant(value: str) -> None:
    raise BodyPackError(f"JSON constant {value} is unsupported.")


def _log_rejection(code: str, message: str, path: str | None) -> None:
    LOGGER.error("body_pack_rejected code=%s path=%s detail=%s", code, path or "<pack>", message)


def _mismatch(code: str, message: str, path: str | None = None) -> BodyPackMismatchError:
    _log_rejection(code, message, path)
    return BodyPackMismatchError(code, message, path)


__all__ = (
    "BodyPackReader",
    "CharacterBodyBinding",
    "resolve_body_pack",
    "resolve_character_body_binding",
    "validate_body_pack_binding",
)
