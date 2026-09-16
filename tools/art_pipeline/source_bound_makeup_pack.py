"""Seal 30 source-pinned views while the new exasperated view uses its own runtime.

Input JSON schema ``mohan.cross-angle-native-makeup.v1``::

    {
      "schema": "mohan.cross-angle-native-makeup.v1",
      "palette_approval": {"path": "scratchpad/.../owner-approval.json", "sha256": "..."},
      "source_pack": {"path": "assets/official-packs/mohan.makeup.builtin.mohan-outfit", "sha256": "..."},
      "views": {
        "front-crossed": {
          "source": {"path": "scratchpad/.../approved.png", "sha256": "..."},
          "eye_motion": "animated",
          "layers": {
            "rest": {"eyes": {"path": "scratchpad/.../eyes.png", "sha256": "...", "nonvisible": false},
                     "cheeks": {"...": "..."}, "lips": {"...": "..."}},
            "half": {"eyes": {"...": "..."}},
            "closed": {"eyes": {"...": "..."}}
          }
        }
      }
    }

``views`` must contain the 30 silhouettes other than ``front-exasperated``.
That expression is retained byte-for-byte in the source archive because its
approved new face and four mouth states use a separate source-bound runtime.
An empty pigment layer is
accepted only when its slot has no native safe-region rectangles and the input
explicitly marks ``nonvisible``. Fixed-closed eyes may reuse their one genuine
closed-eye pigment for all three eye states. Foundation declarations and bytes
remain unchanged. The output is an isolated candidate, never the official pack.
"""

from __future__ import annotations

lazy import argparse
lazy import hashlib
lazy import json
lazy import zipfile
lazy from io import BytesIO
lazy from pathlib import Path

lazy from PIL import Image

lazy from application.outfit_pack_builder import build_outfit_pack
lazy from domain.outfit_pack import (
    BUILTIN_MAKEUP_PACK_ID,
    MAKEUP_CANVASES,
    POSE_ATLAS_SILHOUETTES,
    REQUIRED_SILHOUETTES,
    inspect_outfit_pack,
)
lazy from domain.outfit_pack_makeup import load_makeup_safe_regions, verify_makeup_layers


SCHEMA = "mohan.cross-angle-native-makeup.v1"
APPROVAL_SCHEMA = "mohan.cross-angle-makeup-owner-approval.v1"
SOURCE_PACK_PATH = "assets/official-packs/mohan.makeup.builtin.mohan-outfit"
SAFE_REGIONS_PATH = "assets/makeup-safe-regions.json"
REST_SLOTS = frozenset({"eyes", "cheeks", "lips"})
STATES = {"rest": REST_SLOTS, "half": frozenset({"eyes"}), "closed": frozenset({"eyes"})}
VARIANTS = frozenset({"classic", "light"})
LIGHT_INTENSITY = 0.55
EXTERNAL_VIEW = "front-exasperated"
PACK_VIEWS = tuple(view for view in REQUIRED_SILHOUETTES if view != EXTERNAL_VIEW)
SHA_LENGTH = 64


def digest(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _pin(root: Path, record: object, *, prefix: str | None = None) -> tuple[str, bytes]:
    if not isinstance(record, dict) or not isinstance(record.get("path"), str):
        raise ValueError("Source-bound makeup requires a file path and SHA.")
    relative = record["path"]
    expected = record.get("sha256")
    if (
        not isinstance(expected, str) or len(expected) != SHA_LENGTH
        or any(char not in "0123456789abcdef" for char in expected)
        or Path(relative).is_absolute() or ".." in Path(relative).parts
        or (prefix is not None and not relative.startswith(prefix))
    ):
        raise ValueError(f"Invalid source-bound makeup pin: {relative}")
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError("Source-bound makeup path escapes the project.")
    payload = path.read_bytes()
    if digest(payload) != expected:
        raise ValueError(f"Source-bound makeup SHA mismatch: {relative}")
    return relative, payload


def _image(payload: bytes, canvas: tuple[int, int], *, rgba: bool) -> Image.Image:
    with Image.open(BytesIO(payload)) as opened:
        if opened.format != "PNG" or opened.size != canvas or (rgba and opened.mode != "RGBA"):
            raise ValueError("Makeup source must be a native-canvas PNG with its declared mode.")
        return opened.copy()


def _light_pigment(payload: bytes) -> bytes:
    """Keep pigment color and support, reducing only visible alpha to 55%."""
    with Image.open(BytesIO(payload)) as opened:
        if opened.format != "PNG" or opened.mode != "RGBA":
            raise ValueError("Light pigment needs a native RGBA PNG.")
        image = opened.copy()
    alpha = image.getchannel("A")
    image.putalpha(alpha.point(lambda value: max(1, round(value * LIGHT_INTENSITY)) if value else 0))
    output = BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def _palette_approval(root: Path, record: object) -> tuple[str, dict]:
    path, payload = _pin(root, record, prefix="scratchpad/")
    approval = json.loads(payload)
    expected_scope = {
        "cross-angle eyes cheeks lips palette",
        "native per-view layer integration",
        "optional strength and removal",
    }
    if (
        not isinstance(approval, dict) or approval.get("schema") != APPROVAL_SCHEMA
        or set(approval.get("approved_scope", ())) != expected_scope
        or approval.get("not_authorized_as_replacement_face") is not True
    ):
        raise ValueError("Palette approval does not authorize native optional pigment layers.")
    reference = (root / path).parent / approval["reference"]
    if not reference.resolve().is_relative_to(root.resolve()) or digest(reference.read_bytes()) != approval["sha256"]:
        raise ValueError("Approved palette reference changed.")
    return path, approval


def _manifest_variants(manifest: dict, views: set[str]) -> dict[str, dict]:
    if manifest.get("id") != BUILTIN_MAKEUP_PACK_ID or not isinstance(manifest.get("makeup"), list) or len(manifest["makeup"]) != 1:
        raise ValueError("Source archive is not the built-in makeup item.")
    variants = {variant["id"]: variant for variant in manifest["makeup"][0]["variants"]}
    if set(variants) != VARIANTS:
        raise ValueError("Built-in makeup must retain classic and light variants.")
    for variant in variants.values():
        if set(variant.get("poses", {})) != views or set(variant.get("eye_states", {})) != {"half", "closed"}:
            raise ValueError("Built-in makeup must cover every view and eye state.")
        if any(set(variant["eye_states"][state]) != views for state in ("half", "closed")):
            raise ValueError("Built-in makeup eye states must cover every view.")
    return variants


def _entry(variant: dict, view: str, state: str, slot: str) -> dict:
    group = variant["poses"] if state == "rest" else variant["eye_states"][state]
    matches = [entry for entry in group[view] if entry.get("slot") == slot]
    if len(matches) != 1:
        raise ValueError(f"Missing or repeated makeup slot: {view}/{state}/{slot}")
    return matches[0]


def _foundation_snapshot(manifest: dict, archive: zipfile.ZipFile) -> dict[str, tuple[dict, str]]:
    found = {}
    for variant in manifest["makeup"][0]["variants"]:
        for state, group in (("rest", variant["poses"]), *variant["eye_states"].items()):
            for view, entries in group.items():
                for entry in entries:
                    if entry.get("slot") == "foundation":
                        found[f"{variant['id']}/{state}/{view}"] = (entry.copy(), digest(archive.read(entry["path"])))
    return found


def _validate_layers(
    root: Path, views: dict, regions: dict, required: tuple[str, ...],
) -> tuple[dict[tuple[str, str, str], bytes], dict[str, str]]:
    if set(views) != set(required):
        raise ValueError("Source-bound makeup requires every non-exasperated silhouette.")
    pigments = {}
    pins = {}
    for view in required:
        declaration = views[view]
        canvas = MAKEUP_CANVASES["full-body" if view in POSE_ATLAS_SILHOUETTES else "half-body"]
        source_path, source = _pin(root, declaration["source"])
        _image(source, canvas, rgba=False)
        pins[source_path] = digest(source)
        states = declaration.get("layers")
        if not isinstance(states, dict) or set(states) != set(STATES):
            raise ValueError(f"Missing eye or rest makeup state: {view}")
        for state, slots in STATES.items():
            entries = states[state]
            if not isinstance(entries, dict) or set(entries) != slots:
                raise ValueError(f"Missing native makeup slot: {view}/{state}")
            for slot in slots:
                record = entries[slot]
                if not isinstance(record, dict) or set(record) != {"path", "sha256", "nonvisible"} or not isinstance(record["nonvisible"], bool):
                    raise ValueError(f"Makeup layer requires explicit visibility: {view}/{state}/{slot}")
                path, payload = _pin(root, record, prefix="scratchpad/")
                image = _image(payload, canvas, rgba=True)
                visible_alpha = image.getchannel("A").getbbox() is not None
                native_visible = bool(regions[view].rects(slot))
                if record["nonvisible"] != (not native_visible) or visible_alpha != native_visible:
                    raise ValueError(f"Makeup pigment visibility disagrees with native feature: {view}/{state}/{slot}")
                pigments[(view, state, slot)] = payload
                pins[path] = digest(payload)
        eye_motion = declaration.get("eye_motion", "animated")
        if eye_motion not in {"animated", "fixed_closed"}:
            raise ValueError(f"Unsupported eye motion: {view}")
        if eye_motion == "fixed_closed" and len({
            pigments[(view, state, "eyes")] for state in STATES
        }) != 1:
            raise ValueError(f"Fixed-closed eyes must reuse one native pigment: {view}")
    return pigments, pins


def _pigment_replacements(
    variants: dict[str, dict], pigments: dict[tuple[str, str, str], bytes],
) -> dict[str, bytes]:
    replacements = {}
    for variant_id, variant in variants.items():
        if variant.get("intensity", 1.0) != 1.0:
            raise ValueError("Built-in variant strength changed; refusing double attenuation.")
        for (view, state, slot), payload in pigments.items():
            path = _entry(variant, view, state, slot)["path"]
            if path in replacements:
                raise ValueError(f"Built-in pigment archive member is shared: {path}")
            replacements[path] = payload if variant_id == "classic" else _light_pigment(payload)
    return replacements


def _external_snapshot(variants: dict[str, dict], archive: zipfile.ZipFile) -> dict:
    return {
        f"{variant_id}/{state}": [
            (entry.copy(), digest(archive.read(entry["path"])))
            for entry in (variant["poses"] if state == "rest" else variant["eye_states"][state])[EXTERNAL_VIEW]
        ]
        for variant_id, variant in variants.items()
        for state in STATES
    }


def _stage_source_pack(
    pack_bytes: bytes, output: Path, required: tuple[str, ...],
    pigments: dict[tuple[str, str, str], bytes],
) -> tuple[Path, Path, dict, dict, dict[str, str]]:
    stage = output.parent / f".{output.stem}.authoring"
    if stage.exists():
        raise ValueError("A prior source-bound makeup stage already exists.")
    with zipfile.ZipFile(BytesIO(pack_bytes)) as archive:
        manifest = json.loads(archive.read("manifest.json"))
        variants = _manifest_variants(manifest, set(required) | {EXTERNAL_VIEW})
        foundation_before = _foundation_snapshot(manifest, archive)
        external_before = _external_snapshot(variants, archive)
        replacements = _pigment_replacements(variants, pigments)
        foundation_paths = {entry[0]["path"] for entry in foundation_before.values()}
        if foundation_paths & replacements.keys():
            raise ValueError("Foundation is not an editable pigment slot.")
        unchanged = {
            name: digest(archive.read(name))
            for name in archive.namelist()
            if name != "manifest.json" and name not in replacements
        }
        stage.mkdir(parents=True, exist_ok=False)
        asset_root = stage / "asset-root"
        for name in archive.namelist():
            if name == "manifest.json":
                continue
            relative = Path(*name.split("/"))
            if relative.is_absolute() or ".." in relative.parts:
                raise ValueError("Built-in archive has an unsafe member path.")
            target = asset_root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(replacements.get(name, archive.read(name)))
    authoring = stage / "manifest.json"
    authoring.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return authoring, asset_root, foundation_before, external_before, unchanged


def _verify_preserved_members(
    output: Path, required: tuple[str, ...], foundation_before: dict,
    external_before: dict, unchanged: dict[str, str],
) -> None:
    with zipfile.ZipFile(output) as sealed:
        manifest = json.loads(sealed.read("manifest.json"))
        foundation_after = _foundation_snapshot(manifest, sealed)
        variants = _manifest_variants(manifest, set(required) | {EXTERNAL_VIEW})
        external_after = _external_snapshot(variants, sealed)
        unchanged_after = {name: digest(sealed.read(name)) for name in unchanged}
    if (
        foundation_after != foundation_before or external_after != external_before
        or unchanged_after != unchanged
    ):
        raise ValueError("Out-of-scope makeup assets changed while sealing pigments.")


def prepare_candidate(
    root: Path, request_path: Path, output: Path, *, regions: dict | None = None,
    required: tuple[str, ...] = PACK_VIEWS,
    build=build_outfit_pack,
) -> dict:
    """Validate every source before staging; seal only to scratchpad output."""
    root = Path(root).resolve()
    request_path = Path(request_path).resolve()
    output = Path(output).resolve()
    if not request_path.is_relative_to(root) or not output.is_relative_to(root / "scratchpad"):
        raise ValueError("Request and candidate output must remain in the project and scratchpad.")
    if output.exists() or output.with_suffix(output.suffix + ".receipt.json").exists():
        raise ValueError("Candidate output already exists.")
    request_bytes = request_path.read_bytes()
    request = json.loads(request_bytes)
    if not isinstance(request, dict) or request.get("schema") != SCHEMA:
        raise ValueError("Unsupported source-bound makeup request.")
    approval_path, approval = _palette_approval(root, request.get("palette_approval"))
    pack_path, pack_bytes = _pin(root, request.get("source_pack"))
    if pack_path != SOURCE_PACK_PATH:
        raise ValueError("Source-bound makeup must start from the canonical built-in archive.")
    safe_bytes = (root / SAFE_REGIONS_PATH).read_bytes()
    regions = load_makeup_safe_regions(root / SAFE_REGIONS_PATH) if regions is None else regions
    pigments, pins = _validate_layers(root, request.get("views", {}), regions, required)
    authoring, asset_root, foundation_before, external_before, unchanged = _stage_source_pack(
        pack_bytes, output, required, pigments,
    )
    build(authoring, asset_root, output, makeup_regions=regions)
    inspect_outfit_pack(output)
    verify_makeup_layers(output, regions)
    _verify_preserved_members(output, required, foundation_before, external_before, unchanged)
    receipt = {
        "schema": "mohan.cross-angle-native-makeup-candidate.v1",
        "candidate_only": True,
        "request_sha256": digest(request_bytes),
        "palette_approval_path": approval_path,
        "palette_approval_sha256": request["palette_approval"]["sha256"],
        "palette_reference_sha256": approval["sha256"],
        "source_pack_sha256": digest(pack_bytes),
        "safe_regions_sha256": digest(safe_bytes),
        "source_and_layer_sha256": pins,
        "pigment_layers_per_view": 5,
        "builtin_pack_views_replaced": len(required),
        "builtin_pack_views_total": len(required) + 1,
        "front_exasperated_external_runtime": True,
        "front_exasperated_archive_members_preserved": True,
        "full_31_view_runtime_approval": False,
        "classic_variant_intensity": 1.0,
        "light_variant_intensity": 1.0,
        "light_pigment_alpha_factor": LIGHT_INTENSITY,
        "foundation_members_preserved": len(foundation_before),
        "out_of_scope_members_preserved": len(unchanged),
        "candidate_pack_sha256": digest(output.read_bytes()),
        "formal_pack_modified": False,
    }
    receipt_path = output.with_suffix(output.suffix + ".receipt.json")
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("project_root", type=Path)
    parser.add_argument("request", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    receipt = prepare_candidate(args.project_root, args.request, args.output)
    print(receipt["candidate_pack_sha256"])


if __name__ == "__main__":
    main()
