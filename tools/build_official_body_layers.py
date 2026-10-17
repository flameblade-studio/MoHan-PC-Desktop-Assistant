"""Repartition official appearance targets against the declared bald body pack."""
from __future__ import annotations

lazy import argparse
lazy import hashlib
lazy import json
lazy import shutil
lazy import sys
lazy import zipfile
lazy from copy import deepcopy
lazy from pathlib import Path
lazy from io import BytesIO

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

lazy import numpy as np
lazy from PIL import Image
lazy from domain.character_layer_plan import parse_character_layer_views
lazy from infrastructure.body_pack_reader import BodyPackReader
lazy from domain.body_pack import parse_body_pack_reference
lazy from application.outfit_pack_builder import build_outfit_pack
lazy from application.character_runtime_bootstrap import activate_product_character_runtime

OPAQUE_ALPHA = 255
REAR_HAIR_YAW = 105

KINDS = ("hair-back", "body-fix", "garment", "hair-front", "ornament")
SOURCE_KINDS = {"hair-back": "back-hair", "body-fix": "look-fix",
                "hair-front": "front-hair", "ornament": "ornaments"}
HALF_ROUNDS = {"front-eureka": "round2", "front-mock-scold": "round2",
               "left-neutral": "round3", "front-mock-hit": "round3",
               "front-exasperated": "round3", "cheek-rest": "round7-cheek"}
CHEEK_LAYER_VIEWS = (
    "cheek", "cheek-rest", "cheek-happy", "cheek-caught", "cheek-worried",
    "cheek-glance", "cheek-reminder",
)
CHEEK_EXPRESSION_ALIASES = ("happy", "caught", "worried", "glance", "reminder")
BODY_LAYER_PATH_PARTS = 4


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
                    encoding="utf-8", newline="\n")


def pixels(path: Path) -> np.ndarray:
    with Image.open(path) as image:
        return np.array(image.convert("RGBA"))


def image_record(root: Path, relative: str, data: np.ndarray) -> dict:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(data).save(path)
    return {"path": relative, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "anchor": [0, 0]}


def semantic_owners(source: Path, shape: tuple[int, ...]) -> np.ndarray:
    """Keep source hair/ornament ownership; garment owns remaining outfit changes.

    Existing look-fix pixels above the authored neck boundary retain body-fix
    ownership. The five candidate poses supply a complete semantic-owner map.
    No face-core mask participates in this partition.
    """
    owner = np.full(shape[:2], KINDS.index("garment"), np.uint8)
    owner_path = source / "semantic-owner.png"
    if owner_path.is_file():
        with Image.open(owner_path) as image:
            semantic = np.array(image.convert("L").resize((shape[1], shape[0]), Image.Resampling.NEAREST))
        mapping = {1: "hair-back", 3: "hair-front", 4: "ornament"}
        for index, kind in mapping.items():
            owner[semantic == index] = KINDS.index(kind)
    else:
        for kind in ("hair-back", "hair-front", "ornament"):
            with Image.open(source / (SOURCE_KINDS[kind] + ".png")) as image:
                mask = np.array(image.convert("RGBA").resize((shape[1], shape[0]), Image.Resampling.NEAREST))[..., 3] > 0
            owner[mask] = KINDS.index(kind)
    with Image.open(source / "look-fix.png") as image:
        look = np.array(image.convert("RGBA").resize((shape[1], shape[0]), Image.Resampling.NEAREST))[..., 3] > 0
    neck = 450 if source.name.startswith("yaw") else 600
    head = np.indices(shape[:2])[0] < neck
    owner[look & head & (owner == KINDS.index("garment"))] = KINDS.index("body-fix")
    return owner


def halfbody_owner_approval(
    approved: np.ndarray,
    view: str,
    *,
    approved_path: Path | None = None,
) -> dict | None:
    """Validate owner approval only for repository-owned formal targets.

    The builder also accepts isolated authoring fixtures. Those fixtures must
    use their supplied target pixels, while the formal repository route keeps
    the hash-bound owner approval check.
    """
    formal_pose = "front-exasperated" if view == "exasperated" else view
    formal_target = (
        ROOT / "assets/official-look-targets/halfbody" / formal_pose / "R.png"
    ).resolve()
    if approved_path is not None and approved_path.resolve() != formal_target:
        return None
    approval_record = None
    approval_path = ROOT / "docs/release-evidence/mohan-official-look-halfbody-approval.json"
    if approval_path.is_file():
        approval = json.loads(approval_path.read_text(encoding="utf-8"))
        record = next((item for item in approval.get("poses", []) if item["pose"] == formal_pose), None)
        if record is not None and approval.get("approved_scope") == "appearance":
            relative = Path(record["source_path"])
            if relative.is_absolute() or ".." in relative.parts:
                raise ValueError("Owner-approved source must be repository-relative")
            original_path = ROOT / relative
            if hashlib.sha256(original_path.read_bytes()).hexdigest() != record["source_sha256"]:
                raise ValueError(f"Owner-approved source hash differs: {view}")
            original = pixels(original_path)
            original[original[..., 3] == 0] = 0
            if not np.array_equal(original, approved):
                raise ValueError(f"Approved half-body pixels differ: {view}")
            approval_record = {"path": approval_path.relative_to(ROOT).as_posix(),
                               "source_sha256": record["source_sha256"],
                               "scope": "appearance"}
    return approval_record


def approved_target_path(source: Path, view: str, *, candidate: bool) -> Path:
    """Prefer the repository snapshot of an owner-approved half-body target."""
    pose = "front-exasperated" if view == "exasperated" else view
    local = source / ("R.png" if candidate else "A.png")
    if local.is_file():
        return local
    fixed = ROOT / "assets/official-look-targets/halfbody" / pose / "R.png"
    return fixed if fixed.is_file() else local


def build_view(body: BodyPackReader, source: Path, target: Path, view: str,
               *, halfbody: bool, candidate: bool, semantic_source: Path | None = None) -> tuple[dict, dict]:
    with Image.open(BytesIO(body.load_frame(view, "neutral-rest" if halfbody else "rest",
                                           halfbody=halfbody))) as image:
        base = np.array(image.convert("RGBA"))
    approved_path = approved_target_path(source, view, candidate=candidate)
    approved = pixels(approved_path)
    if approved.shape != base.shape:
        raise ValueError(f"Native target canvas differs from the body: {view}")
    base[base[..., 3] == 0] = 0
    approved[approved[..., 3] == 0] = 0
    hide = (base[..., 3] > 0) & (approved[..., 3] < OPAQUE_ALPHA)
    changed = np.any(approved != base, axis=2)
    repaint = changed | hide
    overlay = np.zeros_like(approved)
    overlay[repaint] = approved[repaint]
    owner = semantic_owners(semantic_source or source, base.shape)
    records = []
    for index, kind in enumerate(KINDS):
        layer = np.zeros_like(approved)
        layer[owner == index] = overlay[owner == index]
        records.append({"kind": kind, **image_record(target, f"assets/body-layers/{view}/{kind}.png", layer)})
    mask = np.zeros_like(approved)
    mask[..., 3] = hide.astype(np.uint8) * 255
    mask_record = image_record(target, f"assets/body-layers/{view}/base-hide.png", mask)
    order = ["base", "hair-back", "body-fix", "garment", "hair-front", "ornament"]
    source_manifest = source / "manifest.json"
    source_order = json.loads(source_manifest.read_text(encoding="utf-8")).get("z_order", []) if source_manifest.is_file() else []
    if source.name.startswith("yaw"):
        angle = abs(int(source.name[3:]))
        if angle >= REAR_HAIR_YAW:
            order = ["base", "body-fix", "hair-back", "hair-front", "garment", "ornament"]
    plan = {"order": order, "layers": records, "base_hide": mask_record}
    parse_character_layer_views({view: plan})
    approval_record = (
        halfbody_owner_approval(approved, view, approved_path=approved_path)
        if halfbody else None
    )
    if approval_record is not None:
        candidate = False
    return plan, {"view": view, "source_target_sha256": hashlib.sha256(approved_path.read_bytes()).hexdigest(),
                  "source_order": source_order, "order": order, "candidate_owner_approval_pending": candidate,
                  "owner_approval": approval_record,
                  "changed_pixels": int(changed.sum()), "hidden_pixels": int(hide.sum()),
                  "H_definition": "B.alpha>0 and A.alpha<255", "face_core_precleared": False}


def resolve_semantic_source(source: Path) -> Path:
    """Follow retained source receipts to the authored semantic ownership map."""
    visited = set()
    while (source / "manifest.json").is_file() and not (source / "semantic-owner.png").is_file():
        resolved = source.resolve()
        if resolved in visited:
            raise ValueError("Semantic source receipts form a cycle")
        visited.add(resolved)
        receipt = json.loads((source / "manifest.json").read_text(encoding="utf-8"))
        prior = receipt.get("source")
        if not isinstance(prior, str):
            break
        source = Path(prior)
    return source


def established_layer_view_bindings() -> dict[str, str]:
    """Retain the Stage 1 alias contract while regenerating physical pixels.

    The body pack's fixed facial-core masks are allowed to differ between
    approved generations.  Reclassifying every existing expression alias from
    those masks would silently change the #303 product surface, so the
    repository manifest remains the authority for already-delivered bindings.
    """
    manifest_path = ROOT / "assets/characters/mohan/body/manifest.json"
    if not manifest_path.is_file():
        return {}
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    bindings = {}
    for view, plan in manifest.get("layer_views", {}).items():
        paths = [plan.get("base_hide", {}).get("path")]
        paths.extend(record.get("path") for record in plan.get("layers", []))
        physical = {
            Path(path).parts[5]
            for path in paths
            if isinstance(path, str)
            and Path(path).parts[:5] == ("assets", "characters", "mohan", "body", "views")
        }
        if len(physical) == 1:
            bindings[view] = next(iter(physical))
    return bindings


def build(  # ruff: ignore[too-many-branches] - ordered build orchestration
        body_root: Path, official_root: Path, half_root: Path, output: Path,
        semantic_root: Path | None = None) -> dict:
    if output.exists():
        raise ValueError("Use a fresh output directory to preserve existing evidence")
    manifest = json.loads((body_root / "manifest.json").read_text(encoding="utf-8"))
    body = BodyPackReader(body_root, parse_body_pack_reference({key: manifest[key] for key in ("id", "version", "fingerprint")}))
    output.mkdir(parents=True)
    plans = {}
    receipts = []
    for source in sorted(official_root.iterdir()):
        if not source.is_dir():
            continue
        if source.name == "cheek-rest":
            # The product cheek source is the posture-B fixed-frame input below;
            # never consume the retained stage-one exact-delivery cheek source.
            continue
        view = source.name + "-pitch+00" if source.name.startswith("yaw") else source.name
        plan, receipt = build_view(body, source, output, view,
                                   halfbody=not view.startswith("yaw"), candidate=False,
                                   semantic_source=(resolve_semantic_source(semantic_root / source.name)
                                                    if semantic_root else None))
        plans[view] = plan
        receipts.append(receipt)
    for pose, round_name in HALF_ROUNDS.items():
        view = "exasperated" if pose == "front-exasperated" else pose
        plan, receipt = build_view(body, half_root / round_name / pose, output, view,
                                   halfbody=True, candidate=True)
        plans[view] = plan
        receipts.append(receipt)
    # Identical body-frame bindings identify shared gesture/expression geometry.
    for selected in body.manifest.half_body:
        for pose in body.manifest.half_body:
            if (pose.view_id in plans
                    and dict(body.manifest.face_core_masks).get(selected.view_id)
                    == dict(body.manifest.face_core_masks).get(pose.view_id)):
                plans[selected.view_id] = plans[pose.view_id]
                break
    for view, physical in established_layer_view_bindings().items():
        if physical in plans:
            plans[view] = plans[physical]
    cheek_plan = plans.get("cheek-rest")
    if cheek_plan is None:
        raise ValueError("The posture-B cheek-rest target did not produce a layer plan")
    half_views = {view.view_id for view in body.manifest.half_body}
    for view in (*CHEEK_LAYER_VIEWS, *CHEEK_EXPRESSION_ALIASES):
        if view in half_views:
            plans[view] = cheek_plan
    reference = {"id": body.manifest.id, "version": body.manifest.version,
                 "fingerprint": body.manifest.fingerprint}
    preserved_physical_views = []
    existing_root = ROOT / "assets/characters/mohan/body"
    existing_manifest_path = existing_root / "manifest.json"
    if existing_manifest_path.is_file():
        existing_manifest = json.loads(existing_manifest_path.read_text(encoding="utf-8"))
        if existing_manifest.get("body_pack") == reference:
            seen_plans: set[int] = set()
            for plan in plans.values():
                if not plan.get("layers"):
                    continue
                physical = Path(plan["layers"][0]["path"]).parts[2]
                if physical == "cheek-rest" or id(plan) in seen_plans:
                    continue
                seen_plans.add(id(plan))
                source_dir = existing_root / "views" / physical
                if not source_dir.is_dir():
                    continue
                for record in [*plan["layers"], plan["base_hide"]]:
                    filename = Path(record["path"]).name
                    source_name = "base-hide-mask.png" if filename == "base-hide.png" else filename
                    source_path = source_dir / source_name
                    destination = output / record["path"]
                    if not source_path.is_file():
                        raise FileNotFoundError(source_path)
                    shutil.copyfile(source_path, destination)
                    record["sha256"] = hashlib.sha256(destination.read_bytes()).hexdigest()
                preserved_physical_views.append(physical)
    result = {"body_pack": reference, "layer_views": plans}
    write_json(output / "layers.json", result)
    write_json(output / "build-receipt.json", {"views": receipts, "physical_views": len(receipts),
                                               "declared_views": len(plans),
                                               "excluded_product_layer_views": [],
                                               "cheek_shared_layer_views": [
                                                   view for view in (*CHEEK_LAYER_VIEWS,
                                                                     *CHEEK_EXPRESSION_ALIASES)
                                                   if view in plans
                                               ],
                                               "preserved_existing_physical_views": sorted(
                                                   preserved_physical_views
                                               )})
    return result


def assemble_character_body_layers(layer_root: Path, output: Path) -> dict:
    """Write the layer plans and PNGs as a character-owned scattered body tree.

    ``layer_root`` is the reproducible builder output containing ``layers.json``
    and ``assets/body-layers/<physical-view>/``.  The resulting paths mirror
    the Lin Keyun character-pack contract and never create a large outfit ZIP.
    """

    if output.exists():
        raise ValueError("Use a fresh character body output directory")
    declarations = json.loads((layer_root / "layers.json").read_text(encoding="utf-8"))
    parse_character_layer_views(declarations.get("layer_views"))
    output.mkdir(parents=True)
    copied: set[str] = set()
    physical_views: set[str] = set()

    def relocate(record: dict) -> dict:
        source = Path(record["path"])
        if source.parts[:2] != ("assets", "body-layers") or len(source.parts) != BODY_LAYER_PATH_PARTS:
            raise ValueError(f"Unexpected builder layer path: {record['path']}")
        physical = source.parts[2]
        filename = "base-hide-mask.png" if source.name == "base-hide.png" else source.name
        relative = f"assets/characters/mohan/body/views/{physical}/{filename}"
        physical_views.add(physical)
        if relative not in copied:
            destination = output / Path(*relative.split("/"))
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(layer_root / source, destination)
            copied.add(relative)
        return {**record, "path": relative}

    layer_views = {}
    for view, plan in declarations["layer_views"].items():
        layer_views[view] = {
            "base_hide": relocate(plan["base_hide"]),
            "layers": [relocate(record) for record in plan["layers"]],
            "order": list(plan["order"]),
        }
    result = {"body_pack": declarations["body_pack"], "layer_views": layer_views}
    write_json(output / "manifest.json", result)
    write_json(output / "build-receipt.json", {
        "source": str((layer_root / "layers.json").as_posix()),
        "layer_png_files": len(copied),
        "layer_png_bytes": sum((output / Path(*path.split("/"))).stat().st_size for path in copied),
        "declared_layer_views": len(layer_views),
        "physical_views": len(physical_views),
        "excluded_product_layer_views": [],
    })
    return result


def assemble_official_body_pack(base_pack: Path, layer_root: Path,
                                authoring: Path, output: Path) -> Path:
    """Add an explicit candidate ensemble while retaining all legacy declarations."""
    if authoring.exists() or output.exists():
        raise ValueError("Use fresh candidate authoring and archive paths")
    authoring.mkdir(parents=True)
    with zipfile.ZipFile(base_pack) as archive:
        manifest = json.loads(archive.read("manifest.json"))
        for entry in archive.infolist():
            if entry.filename == "manifest.json":
                continue
            relative = Path(entry.filename)
            if relative.is_absolute() or ".." in relative.parts or "\\" in entry.filename:
                raise ValueError("Official source archive contains an unsafe member")
            path = authoring / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(archive.read(entry))
    declarations = json.loads((layer_root / "layers.json").read_text(encoding="utf-8"))
    ensemble = deepcopy(next(item for item in manifest["ensembles"] if item["id"] == "blue-white-hanfu"))
    ensemble["id"] = "official-body-pack"
    ensemble["display_names"] = {
        "zh-TW": "官方造型（素體包候選）", "zh-CN": "官方造型（素体包候选）",
        "en": "Official Look (Body Pack Candidate)", "ja-JP": "公式衣装（素体パック候補）",
    }
    ensemble["render"] = {"type": "body_pack", **declarations}
    manifest["ensembles"].append(ensemble)
    for plan in declarations["layer_views"].values():
        for record in [*plan["layers"], plan["base_hide"]]:
            relative = Path(record["path"])
            flat = f"assets/body-layer-{relative.parent.name}-{relative.name}"
            (authoring / flat).write_bytes((layer_root / relative).read_bytes())
            record["path"] = flat
    manifest_path = authoring / "manifest.json"
    write_json(manifest_path, manifest)
    return build_outfit_pack(manifest_path, authoring, output)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--body-root", type=Path, required=True)
    parser.add_argument("--official-root", type=Path, required=True)
    parser.add_argument("--half-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--semantic-root", type=Path)
    parser.add_argument(
        "--character-body-output", type=Path,
        help="Also emit the character-owned scattered body tree at this path.",
    )
    parser.add_argument("--base-pack", type=Path)
    parser.add_argument("--pack-output", type=Path)
    args = parser.parse_args()
    if (args.base_pack is None) != (args.pack_output is None):
        parser.error("Provide --base-pack and --pack-output together")
    result = build(args.body_root, args.official_root, args.half_root, args.output, args.semantic_root)
    print(f"Built {len(result['layer_views'])} declared views")
    if args.character_body_output is not None:
        scattered = assemble_character_body_layers(args.output, args.character_body_output)
        print(f"Wrote {len(scattered['layer_views'])} character layer views to {args.character_body_output}")
    if args.base_pack is not None:
        activate_product_character_runtime(ROOT, character_id="mohan")
        assemble_official_body_pack(args.base_pack, args.output,
                                    args.output / "outfit-authoring", args.pack_output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
