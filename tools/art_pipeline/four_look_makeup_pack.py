"""Seal the owner-approved four-look makeup stage into a canonical outfit pack.

The stage is deliberately separate from the pack authoring document.  It pins
every source PNG and reads the current metadata from the official built-in
archive before creating a fresh authoring tree for
``application.outfit_pack_builder.build_outfit_pack``.

Stage JSON schema ``mohan.four-look-makeup-stage.v1``::

    {
      "schema": "mohan.four-look-makeup-stage.v1",
      "source_pack": {"path": "assets/official-packs/...", "sha256": "..."},
      "approval": {"path": "scratchpad/.../owner-approval.json", "sha256": "..."},
      "views": {
        "front-crossed": {
          "variants": {
            "light": {
              "states": {
                "rest": {
                  "eyes": {"path": "scratchpad/...png", "sha256": "...", "nonvisible": false},
                  "cheeks": {"path": "scratchpad/...png", "sha256": "...", "nonvisible": false},
                  "lips": {"path": "scratchpad/...png", "sha256": "...", "nonvisible": false},
                  "foundation": {"path": "scratchpad/...png", "sha256": "...", "nonvisible": false}
                },
                "half": {"eyes": {}, "cheeks": {}, "lips": {}, "foundation": {}},
                "closed": {"eyes": {}, "cheeks": {}, "lips": {}, "foundation": {}}
              }
            }
          }
        }
      }
    }

The stage requires four slots for ``rest``.  For ``half`` and ``closed`` it
accepts the canonical ``eyes`` plus ``foundation`` pair, and also accepts four
slots when an upstream producer uses one uniform shape.  The sealed pack
always follows the canonical contract: ``rest`` carries all four slots and
``half``/``closed`` carry only ``eyes`` and ``foundation``.  Thus the three
looks and 31 silhouettes produce exactly 744 declared PNG members.  Source
files may be reused by the stage; each output declaration receives its own
archive member path.
"""

from __future__ import annotations

lazy import argparse
lazy import copy
lazy import hashlib
lazy import json
lazy import os
lazy import re
lazy import shutil
lazy import zipfile
lazy from collections.abc import Callable, Mapping
lazy from dataclasses import dataclass
lazy from pathlib import Path, PurePosixPath
lazy from tempfile import TemporaryDirectory
lazy from PySide6.QtGui import QImage

lazy from application.outfit_pack_builder import build_outfit_pack
lazy from domain.outfit_pack import (
    BUILTIN_MAKEUP_ITEM_ID,
    BUILTIN_MAKEUP_PACK_ID,
    FORMAT,
    MAKEUP_CANVASES,
    REQUIRED_SILHOUETTES,
    VERSION,
    OutfitPackError,
    inspect_outfit_pack,
)
lazy from domain.outfit_pack_makeup import (
    MakeupSafeRegion,
    alpha_plane,
    load_makeup_safe_regions,
    verify_makeup_layers,
)


SCHEMA = "mohan.four-look-makeup-stage.v1"
RECEIPT_SCHEMA = "mohan.four-look-makeup-pack-build.v1"
APPROVAL_SCHEMA = "mohan.four-look-owner-approved-installation.v1"
SOURCE_PACK_PATH = "assets/official-packs/mohan.makeup.builtin.mohan-outfit"
LOOKS = ("light", "classic", "glamorous")
STATES = ("rest", "half", "closed")
SLOTS = ("eyes", "cheeks", "lips", "foundation")
COMPACT_EYE_STATE_SLOTS = ("eyes", "foundation")
REST_OUTPUT_SLOTS = ("foundation", "cheeks", "eyes", "lips")
EYE_STATE_OUTPUT_SLOTS = ("foundation", "eyes")
STATE_OUTPUT_SLOTS = {
    "rest": REST_OUTPUT_SLOTS,
    "half": EYE_STATE_OUTPUT_SLOTS,
    "closed": EYE_STATE_OUTPUT_SLOTS,
}
SLOT_Z_ORDER = {"foundation": -1, "cheeks": 0, "eyes": 1, "lips": 2}
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
PIN_FIELDS = frozenset({"path", "sha256"})
LAYER_FIELDS = frozenset({"path", "sha256", "nonvisible"})
APPROVED_SCOPE = frozenset({
    "bare light classic glamorous",
    "detachable native runtime integration",
})
GLAMOROUS_NAMES = {
    "zh-TW": "華麗妝",
    "zh-CN": "华丽妆",
    "en": "Glamorous",
    "ja-JP": "華やかメイク",
}
PNG_SIGNATURE_LENGTH = 8
PNG_HEADER_LENGTH = 26
PNG_BIT_DEPTH_OFFSET = 24
PNG_COLOR_TYPE_OFFSET = 25
PNG_BIT_DEPTH = 8
PNG_RGBA_COLOR_TYPE = 6
EXPECTED_DECLARATIONS = 744


class FourLookStageError(ValueError):
    """The stage cannot be sealed without inventing or weakening a contract."""


class _LayerPin:
    __slots__ = ("path", "relative", "sha256", "visible")

    def __init__(self, path: Path, relative: str, sha256: str, visible: bool) -> None:
        self.path = path
        self.relative = relative
        self.sha256 = sha256
        self.visible = visible


@dataclass(frozen=True, slots=True)
class _ValidatedStage:
    stage_bytes: bytes
    source_path: str
    source_sha256: str
    source_manifest: dict
    approval_path: str
    approval_sha256: str
    layers: dict[tuple[str, str, str, str], _LayerPin]
    source_pins: dict[str, str]
    records: int


def digest(payload: bytes) -> str:
    """Return one reproducible SHA-256 digest."""
    return hashlib.sha256(payload).hexdigest()


def _within(root: Path, value: Path, label: str) -> Path:
    resolved = value.resolve()
    if not resolved.is_relative_to(root):
        raise FourLookStageError(f"{label} must remain inside the project.")
    return resolved


def _path_from(root: Path, value: Path, label: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = root / path
    return _within(root, path, label)


def _relative_path(value: object, label: str) -> str:
    if not isinstance(value, str) or not value or "\\" in value:
        raise FourLookStageError(f"{label} requires a portable project-relative path.")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or "." in path.parts:
        raise FourLookStageError(f"{label} must not escape the project.")
    return value


def _pin(root: Path, record: object, *, label: str, prefix: str | None = None) -> tuple[str, Path, bytes]:
    if not isinstance(record, dict) or set(record) != PIN_FIELDS:
        raise FourLookStageError(f"{label} requires exactly path and sha256.")
    relative = _relative_path(record["path"], label)
    if prefix is not None and not relative.startswith(prefix):
        raise FourLookStageError(f"{label} must stay under {prefix}.")
    expected = record["sha256"]
    if not isinstance(expected, str) or SHA256.fullmatch(expected) is None:
        raise FourLookStageError(f"{label} requires a lowercase SHA-256 pin.")
    path = _within(root, root / Path(*PurePosixPath(relative).parts), label)
    try:
        payload = path.read_bytes()
    except OSError as exc:
        raise FourLookStageError(f"{label} asset is unavailable: {relative}") from exc
    if digest(payload) != expected:
        raise FourLookStageError(f"{label} SHA-256 mismatch: {relative}")
    return relative, path, payload


def _read_json(path: Path, label: str) -> tuple[dict, bytes]:
    try:
        payload = path.read_bytes()
        value = json.loads(payload)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise FourLookStageError(f"{label} must be valid UTF-8 JSON.") from exc
    if not isinstance(value, dict):
        raise FourLookStageError(f"{label} must be a JSON object.")
    return value, payload


def _load_stage(root: Path, stage_path: Path) -> tuple[dict, bytes]:
    stage, payload = _read_json(stage_path, "Four-look stage")
    if stage.get("schema") != SCHEMA:
        raise FourLookStageError("Unsupported four-look makeup stage schema.")
    required = {"schema", "source_pack", "approval", "views"}
    if set(stage) != required:
        raise FourLookStageError("Four-look stage has unsupported top-level fields.")
    return stage, payload


def _load_source_manifest(root: Path, record: object) -> tuple[str, str, dict]:
    relative, path, payload = _pin(
        root,
        record,
        label="Source pack",
        prefix="assets/official-packs/",
    )
    if relative != SOURCE_PACK_PATH:
        raise FourLookStageError("The four-look stage must use the canonical built-in makeup archive.")
    try:
        inspect_outfit_pack(path)
        with zipfile.ZipFile(path) as archive:
            manifest = json.loads(archive.read("manifest.json"))
    except (OSError, zipfile.BadZipFile, KeyError, UnicodeError, json.JSONDecodeError, OutfitPackError) as exc:
        raise FourLookStageError("The canonical source pack could not be inspected.") from exc
    if (
        not isinstance(manifest, dict)
        or manifest.get("format") != FORMAT
        or manifest.get("version") != VERSION
        or manifest.get("id") != BUILTIN_MAKEUP_PACK_ID
    ):
        raise FourLookStageError("The source pack metadata is not the canonical built-in pack.")
    makeup = manifest.get("makeup")
    if (
        not isinstance(makeup, list)
        or len(makeup) != 1
        or not isinstance(makeup[0], dict)
        or makeup[0].get("id") != BUILTIN_MAKEUP_ITEM_ID
        or not isinstance(makeup[0].get("variants"), list)
    ):
        raise FourLookStageError("The canonical source pack has no built-in makeup item.")
    source_variants = {variant.get("id") for variant in makeup[0]["variants"] if isinstance(variant, dict)}
    if not set(LOOKS[:2]).issubset(source_variants):
        raise FourLookStageError("The source pack must provide classic and light metadata.")
    return relative, digest(payload), manifest


def _load_approval(root: Path, record: object) -> tuple[str, str]:
    relative, path, payload = _pin(root, record, label="Owner approval", prefix="scratchpad/")
    approval, _ = _read_json(path, "Owner approval")
    scope = approval.get("authorized_scope")
    looks = approval.get("looks")
    if (
        approval.get("schema") != APPROVAL_SCHEMA
        or approval.get("owner_appearance_approved") is not True
        or not isinstance(scope, list)
        or not APPROVED_SCOPE.issubset(scope)
        or not isinstance(looks, list)
        or not set(("bare", *LOOKS)).issubset(looks)
    ):
        raise FourLookStageError("Owner approval does not authorize the four-look replacement scope.")
    return relative, digest(payload)


def _rgba_layer(path: Path, payload: bytes, canvas: tuple[int, int], label: str) -> bool:
    if (
        len(payload) < PNG_HEADER_LENGTH
        or payload[:PNG_SIGNATURE_LENGTH] != b"\x89PNG\r\n\x1a\n"
        or payload[PNG_BIT_DEPTH_OFFSET] != PNG_BIT_DEPTH
        or payload[PNG_COLOR_TYPE_OFFSET] != PNG_RGBA_COLOR_TYPE
    ):
        raise FourLookStageError(f"{label} must be an 8-bit RGBA PNG: {path.name}")
    image = QImage.fromData(payload, "PNG")
    if image.isNull() or not image.hasAlphaChannel() or image.size().toTuple() != canvas:
        raise FourLookStageError(f"{label} must cover the native {canvas[0]}x{canvas[1]} canvas.")
    try:
        plane, width, height = alpha_plane(payload)
    except OutfitPackError as exc:
        raise FourLookStageError(f"{label} has an invalid alpha plane.") from exc
    if (width, height) != canvas:
        raise FourLookStageError(f"{label} must cover the native {canvas[0]}x{canvas[1]} canvas.")
    return any(plane)


def _layer(
    root: Path,
    record: object,
    canvas: tuple[int, int],
    label: str,
    cache: dict[Path, tuple[str, bool]],
) -> _LayerPin:
    if not isinstance(record, dict) or set(record) != LAYER_FIELDS or not isinstance(record.get("nonvisible"), bool):
        raise FourLookStageError(f"{label} requires path, sha256 and explicit nonvisible.")
    relative = _relative_path(record["path"], label)
    if not relative.startswith("scratchpad/"):
        raise FourLookStageError(f"{label} must stay under scratchpad/.")
    expected = record["sha256"]
    if not isinstance(expected, str) or SHA256.fullmatch(expected) is None:
        raise FourLookStageError(f"{label} requires a lowercase SHA-256 pin.")
    path = _within(root, root / Path(*PurePosixPath(relative).parts), label)
    cached = cache.get(path)
    if cached is None:
        try:
            payload = path.read_bytes()
        except OSError as exc:
            raise FourLookStageError(f"{label} asset is unavailable: {relative}") from exc
        actual = digest(payload)
        visible = _rgba_layer(path, payload, canvas, label)
        cache[path] = (actual, visible)
    else:
        actual, visible = cached
    if actual != expected:
        raise FourLookStageError(f"{label} SHA-256 mismatch: {relative}")
    if bool(record["nonvisible"]) == visible:
        raise FourLookStageError(f"{label} nonvisible disagrees with the PNG alpha.")
    return _LayerPin(path, relative, expected, visible)


def _names(source_variant: object, variant_id: str) -> dict[str, str]:
    if variant_id == "glamorous":
        return copy.deepcopy(GLAMOROUS_NAMES)
    if not isinstance(source_variant, dict) or not isinstance(source_variant.get("display_names"), dict):
        raise FourLookStageError(f"Source metadata has no localized names for {variant_id}.")
    names = source_variant["display_names"]
    if set(names) != {"zh-TW", "zh-CN", "en", "ja-JP"} or any(not isinstance(value, str) for value in names.values()):
        raise FourLookStageError(f"Source metadata has incomplete localized names for {variant_id}.")
    return copy.deepcopy(names)


def _metadata(source_manifest: dict) -> dict[str, object]:
    """Clone official metadata while replacing only the makeup declarations."""
    manifest = copy.deepcopy(source_manifest)
    source_item = source_manifest["makeup"][0]
    source_variants = {variant["id"]: variant for variant in source_item["variants"]}
    variants = []
    for look in LOOKS:
        base = source_variants.get(look, {})
        variant: dict[str, object] = {
            "id": look,
            "display_names": _names(base, look),
            "intensity": float(base.get("intensity", 1.0)),
            "foundation_silhouettes": list(REQUIRED_SILHOUETTES),
            "poses": {},
            "eye_states": {"half": {}, "closed": {}},
        }
        variants.append(variant)
    manifest["makeup"] = [{
        "id": source_item["id"],
        "display_names": copy.deepcopy(source_item["display_names"]),
        "variants": variants,
    }]
    return manifest


def _output_path(look: str, silhouette: str, state: str, slot: str) -> str:
    return f"assets/mohan-four-look-{look}-{silhouette}-{state}-{slot}.png"


def _asset_declaration(path: str, slot: str, canvas: tuple[int, int], sha256: str) -> dict[str, object]:
    return {
        "slot": slot,
        "path": path,
        "sha256": sha256,
        "width": canvas[0],
        "height": canvas[1],
        "anchor": [0, 0],
        "z_order": SLOT_Z_ORDER[slot],
    }


def _validate_views(
    root: Path,
    views: object,
) -> tuple[dict[tuple[str, str, str, str], _LayerPin], dict[str, str], int]:
    if not isinstance(views, dict) or set(views) != set(REQUIRED_SILHOUETTES):
        raise FourLookStageError("Four-look stage must cover all 31 canonical silhouettes.")
    layers: dict[tuple[str, str, str, str], _LayerPin] = {}
    source_pins: dict[str, str] = {}
    cache: dict[Path, tuple[str, bool]] = {}
    records = 0
    for silhouette in REQUIRED_SILHOUETTES:
        view = views[silhouette]
        if not isinstance(view, dict) or set(view) != {"variants"} or not isinstance(view["variants"], dict):
            raise FourLookStageError(f"View {silhouette} requires its variants map.")
        variants = view["variants"]
        if set(variants) != set(LOOKS):
            raise FourLookStageError(f"View {silhouette} must declare light, classic and glamorous.")
        canvas = MAKEUP_CANVASES["full-body" if silhouette.startswith("yaw") else "half-body"]
        for look in LOOKS:
            variant = variants[look]
            if not isinstance(variant, dict) or set(variant) != {"states"} or not isinstance(variant["states"], dict):
                raise FourLookStageError(f"View {silhouette}/{look} requires its states map.")
            states = variant["states"]
            if set(states) != set(STATES):
                raise FourLookStageError(f"View {silhouette}/{look} must declare rest, half and closed states.")
            for state in STATES:
                state_layers = states[state]
                provided_slots = set(state_layers) if isinstance(state_layers, dict) else set()
                valid_slots = (
                    provided_slots == set(SLOTS)
                    if state == "rest"
                    else provided_slots in (set(SLOTS), set(COMPACT_EYE_STATE_SLOTS))
                )
                if not valid_slots:
                    required = (
                        "all four makeup slots"
                        if state == "rest"
                        else "all four makeup slots or the canonical eyes and foundation pair"
                    )
                    raise FourLookStageError(f"View {silhouette}/{look}/{state} must carry {required}.")
                for slot in SLOTS:
                    if slot not in state_layers:
                        continue
                    label = f"Layer {silhouette}/{look}/{state}/{slot}"
                    pin = _layer(root, state_layers[slot], canvas, label, cache)
                    layers[(look, silhouette, state, slot)] = pin
                    source_pins[pin.relative] = pin.sha256
                    records += 1
    return layers, source_pins, records


def _validate_stage_document(root: Path, stage_path: Path) -> _ValidatedStage:
    stage, stage_bytes = _load_stage(root, stage_path)
    source_path, source_sha256, source_manifest = _load_source_manifest(root, stage["source_pack"])
    approval_path, approval_sha256 = _load_approval(root, stage["approval"])
    layers, source_pins, records = _validate_views(root, stage["views"])
    return _ValidatedStage(
        stage_bytes,
        source_path,
        source_sha256,
        source_manifest,
        approval_path,
        approval_sha256,
        layers,
        source_pins,
        records,
    )


def _target_paths(
    root: Path,
    output: Path,
    receipt_path: Path | None,
) -> tuple[Path, Path | None]:
    output_path = _path_from(root, output, "Output pack")
    if output_path.suffix != ".mohan-outfit":
        raise FourLookStageError("The output must use the .mohan-outfit extension.")
    if output_path.exists():
        raise FourLookStageError("Refusing to overwrite an existing outfit pack.")
    if receipt_path is None:
        return output_path, None
    receipt = _path_from(root, receipt_path, "Build receipt")
    if receipt.exists():
        raise FourLookStageError("Refusing to overwrite an existing build receipt.")
    return output_path, receipt


def _regions(
    root: Path,
    makeup_regions: Mapping[str, MakeupSafeRegion] | None,
    safe_regions_path: Path | None,
) -> Mapping[str, MakeupSafeRegion] | None:
    if makeup_regions is not None and safe_regions_path is not None:
        raise FourLookStageError("Provide makeup regions or a safe-region path, not both.")
    if safe_regions_path is None:
        return makeup_regions
    return load_makeup_safe_regions(_path_from(root, safe_regions_path, "Safe-region document"))


def _seal(
    output_path: Path,
    source_manifest: dict,
    layers: dict[tuple[str, str, str, str], _LayerPin],
    regions: Mapping[str, MakeupSafeRegion] | None,
    builder: Callable[..., Path],
) -> int:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    declarations = 0
    try:
        with TemporaryDirectory(prefix=".four-look-", dir=output_path.parent) as temporary_name:
            temporary = Path(temporary_name)
            manifest = _metadata(source_manifest)
            authoring, asset_root, declarations = _authoring(manifest, layers, temporary)
            builder(authoring, asset_root, output_path, makeup_regions=regions)
            inspect_outfit_pack(output_path)
            verify_makeup_layers(output_path, regions)
    except (FourLookStageError, OutfitPackError):
        if output_path.is_file():
            output_path.unlink()
        raise
    except BaseException as exc:
        if output_path.is_file():
            output_path.unlink()
        raise FourLookStageError("The canonical four-look pack build failed safely.") from exc
    if not output_path.is_file():
        raise FourLookStageError("The sealed pack did not produce an output file.")
    return declarations


def _receipt_payload(
    root: Path,
    stage_path: Path,
    stage: _ValidatedStage,
    output_path: Path,
    declarations: int,
) -> dict[str, object]:
    return {
        "schema": RECEIPT_SCHEMA,
        "status": "sealed",
        "formal_pack": True,
        "installed": False,
        "formal_assets_written": False,
        "stage_manifest_path": stage_path.relative_to(root).as_posix(),
        "stage_manifest_sha256": digest(stage.stage_bytes),
        "source_pack_path": stage.source_path,
        "source_pack_sha256": stage.source_sha256,
        "owner_approval_path": stage.approval_path,
        "owner_approval_sha256": stage.approval_sha256,
        "stage_layer_source_pins": dict(sorted(stage.source_pins.items())),
        "looks": list(LOOKS),
        "states": list(STATES),
        "input_slots": list(SLOTS),
        "silhouettes": len(REQUIRED_SILHOUETTES),
        "stage_records": stage.records,
        "output_png_declarations": declarations,
        "expected_output_png_declarations": EXPECTED_DECLARATIONS,
        "output_pack_path": output_path.relative_to(root).as_posix(),
        "output_pack_sha256": digest(output_path.read_bytes()),
        "canonical_builder": "application.outfit_pack_builder.build_outfit_pack",
        "canonical_inspection": True,
        "canonical_makeup_pixel_gate": True,
    }


def _authoring(
    manifest: dict[str, object],
    layers: dict[tuple[str, str, str, str], _LayerPin],
    temporary: Path,
) -> tuple[Path, Path, int]:
    asset_root = temporary / "asset-root"
    asset_root.mkdir()
    item = manifest["makeup"][0]
    declarations = 0
    for variant in item["variants"]:
        look = variant["id"]
        poses = {}
        eye_states = {"half": {}, "closed": {}}
        for silhouette in REQUIRED_SILHOUETTES:
            canvas = MAKEUP_CANVASES["full-body" if silhouette.startswith("yaw") else "half-body"]
            entries = []
            for slot in REST_OUTPUT_SLOTS:
                pin = layers[(look, silhouette, "rest", slot)]
                path = _output_path(look, silhouette, "rest", slot)
                target = asset_root / Path(*PurePosixPath(path).parts)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(pin.path, target)
                entries.append(_asset_declaration(path, slot, canvas, pin.sha256))
                declarations += 1
            poses[silhouette] = entries
            for state in ("half", "closed"):
                entries = []
                for slot in EYE_STATE_OUTPUT_SLOTS:
                    pin = layers[(look, silhouette, state, slot)]
                    path = _output_path(look, silhouette, state, slot)
                    target = asset_root / Path(*PurePosixPath(path).parts)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(pin.path, target)
                    entries.append(_asset_declaration(path, slot, canvas, pin.sha256))
                    declarations += 1
                eye_states[state][silhouette] = entries
        variant["poses"] = poses
        variant["eye_states"] = eye_states
    manifest_path = temporary / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest_path, asset_root, declarations


def _write_receipt(path: Path, payload: dict[str, object]) -> None:
    if path.exists():
        raise FourLookStageError("Refusing to overwrite an existing build receipt.")
    temporary = path.with_name(f".{path.name}.writing")
    if temporary.exists():
        raise FourLookStageError("A prior build receipt has not completed safely.")
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.replace(temporary, path)
    except BaseException:
        if temporary.is_file():
            temporary.unlink()
        raise


def prepare_four_look_pack(
    project_root: Path,
    stage_manifest: Path,
    output: Path,
    *,
    receipt_path: Path | None = None,
    makeup_regions: Mapping[str, MakeupSafeRegion] | None = None,
    safe_regions_path: Path | None = None,
    builder: Callable[..., Path] | None = None,
) -> dict[str, object]:
    """Validate and seal one stage, returning the machine-readable receipt."""
    root = Path(project_root).resolve()
    stage_path = _path_from(root, stage_manifest, "Stage manifest")
    output_path, receipt = _target_paths(root, output, receipt_path)
    stage = _validate_stage_document(root, stage_path)
    regions = _regions(root, makeup_regions, safe_regions_path)
    build = build_outfit_pack if builder is None else builder
    declarations = _seal(output_path, stage.source_manifest, stage.layers, regions, build)
    if declarations != EXPECTED_DECLARATIONS:
        output_path.unlink()
        raise FourLookStageError("The sealed pack did not produce the expected declarations.")
    receipt_payload = _receipt_payload(root, stage_path, stage, output_path, declarations)
    if receipt is not None:
        try:
            _write_receipt(receipt, receipt_payload)
        except BaseException:
            if output_path.is_file():
                output_path.unlink()
            raise
    return receipt_payload


def build_four_look_pack(
    stage_manifest: Path,
    output: Path,
    *,
    project_root: Path | None = None,
    receipt_path: Path | None = None,
    makeup_regions: Mapping[str, MakeupSafeRegion] | None = None,
    safe_regions_path: Path | None = None,
    builder: Callable[..., Path] | None = None,
) -> Path:
    """Seal a stage and return the new pack path."""
    root = Path(project_root).resolve() if project_root is not None else Path.cwd().resolve()
    prepare_four_look_pack(
        root,
        stage_manifest,
        output,
        receipt_path=receipt_path,
        makeup_regions=makeup_regions,
        safe_regions_path=safe_regions_path,
        builder=builder,
    )
    return _path_from(root, output, "Output pack")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("project_root", type=Path)
    parser.add_argument("stage_manifest", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--receipt", dest="receipt_path", type=Path)
    parser.add_argument("--safe-regions", dest="safe_regions_path", type=Path)
    args = parser.parse_args(argv)
    receipt = prepare_four_look_pack(
        args.project_root,
        args.stage_manifest,
        args.output,
        receipt_path=args.receipt_path,
        safe_regions_path=args.safe_regions_path,
    )
    print(receipt["output_pack_sha256"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
