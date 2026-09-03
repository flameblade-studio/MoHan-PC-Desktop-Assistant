from __future__ import annotations

lazy import hashlib
lazy import json
lazy import os
lazy import re
lazy import struct
lazy import zipfile
lazy from dataclasses import dataclass
lazy from pathlib import Path, PurePosixPath
lazy from tempfile import NamedTemporaryFile

lazy from domain.character_body_profile import MOHAN_BODY_PROFILE
lazy from domain.character_full_body_rig import FULL_BODY_RIG_SCHEMA_VERSION

FORMAT = "mohan-pose-pack"
VERSION = 2
LEGACY_VERSION = 1
MANIFEST = "manifest.json"
BODY_PROFILE = frozendict({"id": MOHAN_BODY_PROFILE.profile_id, "version": MOHAN_BODY_PROFILE.version})
FULL_BODY_RIG_ID = "mohan-full-body-v1"
FULL_BODY_CONTRACT = "full-body-v4"
LEGACY_CONTRACT = "legacy-v3"
CANONICAL_YAWS = tuple(range(-180, 180, 15))
LEGACY_YAWS = (-30, 0, 30)
BUILTIN_POSES = frozenset({"cheek-rest", "left-neutral", "front-crossed"})
LAYER_ROLES = frozenset({
    "body", "face-alignment", "hair-alignment", "garment-alignment",
    "headwear-alignment", "weapon-alignment", "left-arm-correction",
    "right-arm-correction", "left-hand-correction", "right-hand-correction",
    "left-leg-correction", "right-leg-correction", "left-foot-correction",
    "right-foot-correction", "left-sole-correction", "right-sole-correction",
})
REQUIRED_CORRECTIONS = frozenset({
    "left-arm-correction", "right-arm-correction",
    "left-hand-correction", "right-hand-correction",
})
FULL_BODY_CORRECTIONS = frozenset({
    *REQUIRED_CORRECTIONS,
    "left-leg-correction", "right-leg-correction", "left-foot-correction",
    "right-foot-correction", "left-sole-correction", "right-sole-correction",
})
OCCLUSION_RULES = frozenset({
    "behind-body", "front-of-body", "behind-hands", "front-of-hands",
    "behind-hair", "front-of-hair", "behind-garment", "front-of-garment",
})
COMPATIBILITY_KEYS = frozenset({"face", "hair", "garment", "headwear", "weapon"})
COMPATIBILITY_VALUES = frozenset({"core-owned", "appearance-slot", "optional-slot"})
LANGUAGES = frozenset({"zh-TW", "zh-CN", "en", "ja-JP"})
MAX_ARCHIVE_BYTES = 256 * 1024 * 1024
MAX_MEMBER_BYTES = 32 * 1024 * 1024
MAX_TOTAL_BYTES = 512 * 1024 * 1024
MAX_MEMBERS = 2048
MAX_COMPRESSION_RATIO = 100
MAX_DIMENSION = 8192
MIN_ANCHOR_COORDINATE = -8192
MAX_ANCHOR_COORDINATE = 8192
MIN_DEPTH = -1000
MAX_DEPTH = 1000
MAX_NAME_LENGTH = 80
MIN_PNG_HEADER_LENGTH = 24
MIN_WEBP_HEADER_LENGTH = 30
SYMLINK_FILE_TYPE = 0o120000
ANCHOR_DIMENSIONS = 2
MAX_TEXT_FIELD_LENGTH = 240
IDENTIFIER = re.compile(r"[a-z0-9](?:[a-z0-9.-]{0,62}[a-z0-9])?\Z")
SEMVER = re.compile(r"\d+\.\d+\.\d+\Z")
APP_RANGE = re.compile(r">=\d+\.\d+\.\d+,<\d+\.\d+\.\d+\Z")
INTEGER_RANGE = re.compile(r">=\d+,<\d+\Z")
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
ASSET_PATH = re.compile(r"assets/[a-z0-9][a-z0-9_./-]{0,190}\.(?:png|webp)\Z")
LICENSE = re.compile(r"[A-Za-z0-9 .()+-]{1,120}\Z")


class PosePackError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class PoseLayer:
    role: str
    path: str
    sha256: str
    width: int
    height: int
    anchor_x: int
    anchor_y: int
    depth: int
    occlusion: str


@dataclass(frozen=True, slots=True)
class FullBodyRigContract:
    contract: str
    rig_id: str | None
    rig_version_range: str | None
    body_profile_id: str
    body_profile_version_range: str

    @property
    def complete(self) -> bool:
        return self.contract == FULL_BODY_CONTRACT


@dataclass(frozen=True, slots=True)
class PoseView:
    pose_id: str
    pitch_band: str
    yaw: int
    layers: tuple[PoseLayer, ...]
    rig: FullBodyRigContract


@dataclass(frozen=True, slots=True)
class PosePack:
    pack_id: str
    pack_version: str
    app_range: str
    display_names: frozendict[str, str]
    pitch_bands: tuple[str, ...]
    pose_ids: tuple[str, ...]
    compatibility: frozendict[str, str]
    author: str
    license_name: str
    provenance: str
    views: tuple[PoseView, ...]
    schema_version: int
    rig: FullBodyRigContract

    @property
    def legacy_fallback(self) -> bool:
        return self.rig.contract == LEGACY_CONTRACT


@dataclass(frozen=True, slots=True)
class RemovalResult:
    pack_id: str
    removed_path: Path


@dataclass(frozen=True, slots=True)
class _ViewContext:
    archive: zipfile.ZipFile
    names: set[str]
    pitch_bands: frozenset[str]
    pose_ids: frozenset[str]
    pack_rig: FullBodyRigContract


@dataclass(frozen=True, slots=True)
class _SourceDeclaration:
    author: str
    license_name: str
    provenance: str


def _identifier(value: object, label: str) -> str:
    if not isinstance(value, str) or not IDENTIFIER.fullmatch(value):
        raise PosePackError(f"Invalid {label} identifier.")
    return value


def _localized_names(value: object) -> frozendict[str, str]:
    if not isinstance(value, dict) or set(value) != LANGUAGES or any(not isinstance(text, str) for text in value.values()):
        raise PosePackError("All four localized names are required.")
    names = {language: text.strip() for language, text in value.items()}
    if any(not text or len(text) > MAX_NAME_LENGTH for text in names.values()):
        raise PosePackError("Invalid localized name.")
    return frozendict(names)


def _safe_member(info: zipfile.ZipInfo) -> None:
    path = PurePosixPath(info.filename)
    if info.is_dir() or path.is_absolute() or ".." in path.parts or "\\" in info.filename:
        raise PosePackError("Unsafe archive path.")
    if info.flag_bits & 1 or info.file_size > MAX_MEMBER_BYTES:
        raise PosePackError("Unsafe archive member.")
    if (info.external_attr >> 16) & 0o170000 == SYMLINK_FILE_TYPE:
        raise PosePackError("Symbolic links are forbidden.")
    if info.filename != MANIFEST and not ASSET_PATH.fullmatch(info.filename):
        raise PosePackError("Executable or unsupported member.")
    if info.file_size / max(1, info.compress_size) > MAX_COMPRESSION_RATIO:
        raise PosePackError("Suspicious compression ratio.")


def _dimensions(data: bytes, suffix: str) -> tuple[int, int]:
    if suffix == ".png":
        if len(data) < MIN_PNG_HEADER_LENGTH or data[:8] != b"\x89PNG\r\n\x1a\n" or data[12:16] != b"IHDR":
            raise PosePackError("Invalid PNG layer.")
        return struct.unpack(">II", data[16:24])
    if len(data) < MIN_WEBP_HEADER_LENGTH or data[:4] != b"RIFF" or data[8:12] != b"WEBP" or data[12:16] != b"VP8X":
        raise PosePackError("Invalid or non-extended WebP layer.")
    return int.from_bytes(data[24:27], "little") + 1, int.from_bytes(data[27:30], "little") + 1


def _layer(value: object, archive: zipfile.ZipFile, names: set[str]) -> PoseLayer:
    required = {"role", "path", "sha256", "width", "height", "anchor", "depth", "occlusion", "transparent"}
    if not isinstance(value, dict) or set(value) != required or value["transparent"] is not True:
        raise PosePackError("Invalid transparent layer declaration.")
    role, path = value["role"], value["path"]
    if role not in LAYER_ROLES or not isinstance(path, str) or not ASSET_PATH.fullmatch(path) or path not in names:
        raise PosePackError("Unknown layer role or path.")
    anchor = value["anchor"]
    integers = (value["width"], value["height"], value["depth"])
    if not isinstance(value["sha256"], str) or not SHA256.fullmatch(value["sha256"]) or not isinstance(anchor, list) or len(anchor) != ANCHOR_DIMENSIONS:
        raise PosePackError("Invalid layer hash or anchor.")
    if any(not isinstance(item, int) or isinstance(item, bool) for item in (*integers, *anchor)):
        raise PosePackError("Invalid layer geometry.")
    width, height, depth = integers
    if not (1 <= width <= MAX_DIMENSION and 1 <= height <= MAX_DIMENSION and MIN_ANCHOR_COORDINATE <= anchor[0] <= MAX_ANCHOR_COORDINATE and MIN_ANCHOR_COORDINATE <= anchor[1] <= MAX_ANCHOR_COORDINATE and MIN_DEPTH <= depth <= MAX_DEPTH):
        raise PosePackError("Layer geometry is outside the allowed range.")
    if value["occlusion"] not in OCCLUSION_RULES:
        raise PosePackError("Invalid layer occlusion rule.")
    data = archive.read(path)
    if hashlib.sha256(data).hexdigest() != value["sha256"] or _dimensions(data, Path(path).suffix) != (width, height):
        raise PosePackError("Layer integrity check failed.")
    return PoseLayer(role, path, value["sha256"], width, height, anchor[0], anchor[1], depth, value["occlusion"])


def _rig_contract(value: object, *, legacy: bool) -> FullBodyRigContract:
    if legacy:
        if value is not None:
            raise PosePackError("Legacy pose packs cannot claim a full-body rig.")
        return FullBodyRigContract(
            LEGACY_CONTRACT,
            None,
            None,
            MOHAN_BODY_PROFILE.profile_id,
            f">={MOHAN_BODY_PROFILE.version},<{MOHAN_BODY_PROFILE.version + 1}",
        )
    required = {
        "contract", "rig_id", "rig_version_range", "body_profile_id",
        "body_profile_version_range",
    }
    if not isinstance(value, dict) or set(value) != required:
        raise PosePackError("A v4 full-body rig contract is required.")
    if (
        value["contract"] != FULL_BODY_CONTRACT
        or value["rig_id"] != FULL_BODY_RIG_ID
        or value["body_profile_id"] != MOHAN_BODY_PROFILE.profile_id
        or not isinstance(value["rig_version_range"], str)
        or not INTEGER_RANGE.fullmatch(value["rig_version_range"])
        or not isinstance(value["body_profile_version_range"], str)
        or not INTEGER_RANGE.fullmatch(value["body_profile_version_range"])
        or not _range_contains(value["rig_version_range"], FULL_BODY_RIG_SCHEMA_VERSION)
        or not _range_contains(value["body_profile_version_range"], MOHAN_BODY_PROFILE.version)
    ):
        raise PosePackError("Unsupported full-body rig or body profile range.")
    return FullBodyRigContract(
        value["contract"],
        value["rig_id"],
        value["rig_version_range"],
        value["body_profile_id"],
        value["body_profile_version_range"],
    )


def _range_contains(value: str, version: int) -> bool:
    lower, upper = value.removeprefix(">=").split(",<", 1)
    return int(lower) <= version < int(upper)


def _view(
    value: object,
    context: _ViewContext,
) -> PoseView:
    expected = {"pose_id", "pitch_band", "yaw", "layers"}
    if context.pack_rig.complete:
        expected.add("full_body_rig")
    if not isinstance(value, dict) or set(value) != expected:
        raise PosePackError("Invalid pose view.")
    pose_id, pitch, yaw = value["pose_id"], value["pitch_band"], value["yaw"]
    allowed_yaws = CANONICAL_YAWS if context.pack_rig.complete else LEGACY_YAWS
    if (
        pose_id not in context.pose_ids
        or pitch not in context.pitch_bands
        or yaw not in allowed_yaws
    ):
        raise PosePackError("Unknown pose, pitch band, or canonical yaw.")
    entries = value["layers"]
    if not isinstance(entries, list) or not entries:
        raise PosePackError("A pose view requires layers.")
    layers = tuple(
        _layer(entry, context.archive, context.names) for entry in entries
    )
    roles = {layer.role for layer in layers}
    required_corrections = (
        FULL_BODY_CORRECTIONS if context.pack_rig.complete else REQUIRED_CORRECTIONS
    )
    if len(roles) != len(layers) or "body" not in roles or not required_corrections <= roles:
        raise PosePackError("Pose view lacks required body, arm, or hand layers.")
    if len({layer.depth for layer in layers}) != len(layers):
        raise PosePackError("Layer depths must be unambiguous.")
    view_rig = _rig_contract(
        value.get("full_body_rig"),
        legacy=not context.pack_rig.complete,
    )
    if view_rig != context.pack_rig:
        raise PosePackError("Pose view full-body contract differs from its pack.")
    return PoseView(pose_id, pitch, yaw, layers, view_rig)


def _read_manifest(
    archive: zipfile.ZipFile,
) -> tuple[dict[str, object], set[str]]:
    infos = archive.infolist()
    names = {info.filename for info in infos}
    if (
        not infos
        or len(infos) > MAX_MEMBERS
        or len(names) != len(infos)
        or MANIFEST not in names
    ):
        raise PosePackError("Invalid archive members.")
    for info in infos:
        _safe_member(info)
    if sum(info.file_size for info in infos) > MAX_TOTAL_BYTES:
        raise PosePackError("Archive expands beyond the allowed size.")
    manifest = json.loads(archive.read(MANIFEST).decode("utf-8"))
    if not isinstance(manifest, dict) or manifest.get("format") != FORMAT:
        raise PosePackError("Unsupported pose manifest.")
    return manifest, names


def _manifest_contract(
    manifest: dict[str, object],
) -> tuple[int, FullBodyRigContract]:
    common = {
        "format",
        "version",
        "id",
        "pack_version",
        "app_range",
        "display_names",
        "compatible_body_profile",
        "pitch_bands",
        "pose_ids",
        "compatibility",
        "source",
        "views",
    }
    schema_version = manifest.get("version")
    if schema_version == VERSION:
        required = {*common, "full_body_rig"}
        pack_rig = _rig_contract(manifest.get("full_body_rig"), legacy=False)
    elif schema_version == LEGACY_VERSION:
        required = common
        pack_rig = _rig_contract(None, legacy=True)
    else:
        raise PosePackError("Unsupported pose manifest.")
    if set(manifest) != required:
        raise PosePackError("Unsupported pose manifest fields.")
    return schema_version, pack_rig


def _declarations(
    manifest: dict[str, object],
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    if manifest["compatible_body_profile"] != dict(BODY_PROFILE):
        raise PosePackError("Unsupported body profile.")
    pitch_bands = manifest["pitch_bands"]
    pose_ids = manifest["pose_ids"]
    if (
        not isinstance(pitch_bands, list)
        or not pitch_bands
        or not isinstance(pose_ids, list)
        or not pose_ids
    ):
        raise PosePackError("Pose and pitch declarations are required.")
    parsed_pitches = tuple(_identifier(item, "pitch band") for item in pitch_bands)
    parsed_poses = tuple(_identifier(item, "pose") for item in pose_ids)
    if (
        len(set(parsed_pitches)) != len(parsed_pitches)
        or len(set(parsed_poses)) != len(parsed_poses)
    ):
        raise PosePackError("Duplicate pose or pitch declaration.")
    return parsed_pitches, parsed_poses


def _compatibility(value: object) -> frozendict[str, str]:
    if (
        not isinstance(value, dict)
        or set(value) != COMPATIBILITY_KEYS
        or any(item not in COMPATIBILITY_VALUES for item in value.values())
        or value["face"] != "core-owned"
    ):
        raise PosePackError("Invalid appearance compatibility declaration.")
    return frozendict(value)


def _source_declaration(value: object) -> _SourceDeclaration:
    required = {"kind", "author", "license", "provenance", "reference_included"}
    if (
        not isinstance(value, dict)
        or set(value) != required
        or value["kind"] not in {"original", "concept", "reference-derived"}
        or value["reference_included"] is not False
    ):
        raise PosePackError("Invalid source declaration.")
    text_fields = (value["author"], value["provenance"])
    if (
        any(
            not isinstance(item, str) or not item.strip() or len(item) > MAX_TEXT_FIELD_LENGTH
            for item in text_fields
        )
        or not isinstance(value["license"], str)
        or not LICENSE.fullmatch(value["license"])
    ):
        raise PosePackError("Invalid author, license, or provenance.")
    return _SourceDeclaration(
        value["author"].strip(),
        value["license"],
        value["provenance"].strip(),
    )


def _pose_views(
    value: object,
    context: _ViewContext,
) -> tuple[PoseView, ...]:
    if not isinstance(value, list) or not value:
        raise PosePackError("Pose views are required.")
    views = tuple(_view(entry, context) for entry in value)
    identities = {(view.pose_id, view.pitch_band, view.yaw) for view in views}
    required_yaws = CANONICAL_YAWS if context.pack_rig.complete else LEGACY_YAWS
    expected = {
        *(
            *(
                (pose, pitch, yaw)
                for yaw in required_yaws
            )
            for pitch in context.pitch_bands
        )
        for pose in context.pose_ids
    }
    if len(identities) != len(views) or identities != expected:
        raise PosePackError("Pose views do not match their declared rig contract.")
    paths = [*(layer.path for layer in view.layers) for view in views]
    if len(paths) != len(set(paths)) or context.names != {MANIFEST, *paths}:
        raise PosePackError("Every layer must be declared exactly once.")
    return views


def _versions(manifest: dict[str, object]) -> tuple[str, str, str]:
    pack_id = _identifier(manifest["id"], "pack")
    pack_version = manifest["pack_version"]
    app_range = manifest["app_range"]
    if (
        not isinstance(pack_version, str)
        or not SEMVER.fullmatch(pack_version)
        or not isinstance(app_range, str)
        or not APP_RANGE.fullmatch(app_range)
    ):
        raise PosePackError("Invalid version or app range.")
    return pack_id, pack_version, app_range


def _inspect_archive(archive: zipfile.ZipFile) -> PosePack:
    manifest, names = _read_manifest(archive)
    schema_version, pack_rig = _manifest_contract(manifest)
    parsed_pitches, parsed_poses = _declarations(manifest)
    compatibility = _compatibility(manifest["compatibility"])
    source = _source_declaration(manifest["source"])
    context = _ViewContext(
        archive,
        names,
        frozenset(parsed_pitches),
        frozenset(parsed_poses),
        pack_rig,
    )
    views = _pose_views(manifest["views"], context)
    pack_id, pack_version, app_range = _versions(manifest)
    return PosePack(
        pack_id,
        pack_version,
        app_range,
        _localized_names(manifest["display_names"]),
        parsed_pitches,
        parsed_poses,
        compatibility,
        source.author,
        source.license_name,
        source.provenance,
        views,
        schema_version,
        pack_rig,
    )


def inspect_pose_pack(source: Path) -> PosePack:
    path = Path(source)
    if not path.is_file() or path.stat().st_size > MAX_ARCHIVE_BYTES:
        raise PosePackError("Pose archive size is invalid.")
    try:
        with zipfile.ZipFile(path) as archive:
            return _inspect_archive(archive)
    except (OSError, zipfile.BadZipFile, UnicodeError, json.JSONDecodeError, KeyError, TypeError, ValueError, struct.error, IndexError):
        raise PosePackError("Invalid pose archive.") from None


def install_pose_pack(source: Path, store: Path) -> PosePack:
    pack = inspect_pose_pack(source)
    packages = Path(store) / "packages"
    packages.mkdir(parents=True, exist_ok=True)
    destination = packages / f"{pack.pack_id}.mohan-pose"
    with NamedTemporaryFile("wb", dir=packages, delete=False) as temporary:
        temporary.write(Path(source).read_bytes())
        temporary.flush()
        os.fsync(temporary.fileno())
        temporary_path = Path(temporary.name)
    try:
        os.replace(temporary_path, destination)
    finally:
        temporary_path.unlink(missing_ok=True)
    return pack


def list_installed_pose_packs(store: Path) -> tuple[PosePack, ...]:
    packages = Path(store) / "packages"
    return () if not packages.is_dir() else tuple(inspect_pose_pack(path) for path in sorted(packages.glob("*.mohan-pose")))


def _references(path: Path, pack_id: str) -> bool:
    if not path.is_file():
        return False
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        raise PosePackError("Invalid pose state.") from None
    return isinstance(value, dict) and value.get("pack_id") == pack_id


def remove_pose_pack(store: Path, pack_id: str) -> RemovalResult:
    validated_id = _identifier(pack_id, "pack")
    if validated_id == "builtin":
        raise PosePackError("Built-in poses cannot be removed.")
    target = Path(store) / "packages" / f"{validated_id}.mohan-pose"
    if not target.is_file():
        raise PosePackError("Pose pack is not installed.")
    pack = inspect_pose_pack(target)
    if pack.pack_id != validated_id:
        raise PosePackError("Archive identity does not match its filename.")
    if any(_references(Path(store) / name, validated_id) for name in ("active.json", "preview.json")):
        raise PosePackError("An active or previewed pose pack cannot be removed.")
    try:
        target.unlink()
    except OSError:
        raise PosePackError("Unable to remove pose pack.") from None
    return RemovalResult(validated_id, target)
