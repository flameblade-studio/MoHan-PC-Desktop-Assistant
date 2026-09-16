"""Build an isolated preview from pinned inputs and existing pack declarations.

The manifest describes every copied file. Protected native/body/hand inputs
are copied verbatim; only declared appearance members can be replaced.
"""

from __future__ import annotations

lazy import hashlib
lazy import json
lazy import re
lazy import zipfile
lazy from dataclasses import dataclass
lazy from pathlib import Path, PurePosixPath

SCHEMA = "mohan.source-bound-preview.v1"
VIEW_PATTERN = re.compile(r"yaw[+-]\d{3}-pitch[+-]\d{2}\Z")
SHA_PATTERN = re.compile(r"[0-9a-f]{64}\Z")
PACK_SUFFIX = ".mohan-outfit"
APPEARANCE_PREFIXES = (
    "assets/hanfu-robe-", "assets/loose-hair-", "assets/silver-hairpiece-",
)


@dataclass(frozen=True, slots=True)
class PinnedFile:
    """Repository-relative immutable input and its staging destination."""

    source: str
    sha256: str
    target: str


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def relative_path(value: str) -> PurePosixPath:
    """Require canonical portable paths, including when running on Windows."""
    path = PurePosixPath(value)
    if (
        not value or "\\" in value or ":" in value or path.is_absolute()
        or any(part in {"", ".", ".."} for part in value.split("/"))
    ):
        raise ValueError(f"Expected a canonical relative path: {value!r}")
    return path


def read_pinned(root: Path, pin: PinnedFile) -> bytes:
    relative_path(pin.source)
    if not SHA_PATTERN.fullmatch(pin.sha256):
        raise ValueError("Input requires a lowercase SHA-256 digest.")
    path = root / pin.source
    if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
        raise ValueError(f"Input escapes its repository: {pin.source}")
    data = path.read_bytes()
    if digest(data) != pin.sha256:
        raise ValueError(f"Pinned input changed: {pin.source}")
    return data


def update_declared_hashes(node: object, replacements: dict[str, bytes]) -> set[str]:
    """Refresh existing declarations without inventing layers or changing order."""
    found: set[str] = set()
    if isinstance(node, dict):
        member = node.get("path")
        if isinstance(member, str) and member in replacements:
            if "sha256" not in node:
                raise ValueError(f"Pack declaration lacks SHA-256: {member}")
            node["sha256"] = digest(replacements[member])
            found.add(member)
        for value in node.values():
            found.update(update_declared_hashes(value, replacements))
    elif isinstance(node, list):
        for value in node:
            found.update(update_declared_hashes(value, replacements))
    return found


def rebuild_pack(source: bytes, replacements: dict[str, bytes]) -> bytes:
    """Keep all unmodified members and declaration properties intact."""
    from io import BytesIO

    with zipfile.ZipFile(BytesIO(source)) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)):
            raise ValueError("Duplicate archive member.")
        contents = {name: archive.read(name) for name in names}
        infos = archive.infolist()
    if not replacements:
        return source
    if not replacements.keys() <= contents.keys():
        raise ValueError("Replacement must name an existing archive member.")
    manifest = json.loads(contents["manifest.json"])
    if update_declared_hashes(manifest, replacements) != replacements.keys():
        raise ValueError("Replacement must have an existing layer declaration.")
    contents.update(replacements)
    contents["manifest.json"] = (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode()
    output = BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        for info in infos:
            archive.writestr(info, contents[info.filename])
    return output.getvalue()


def pinned_file(value: dict[str, str]) -> PinnedFile:
    return PinnedFile(value["source"], value["sha256"], value["target"])


def collect_inputs(root: Path, manifest: dict) -> dict[str, bytes]:
    if manifest.get("schema") != SCHEMA or not VIEW_PATTERN.fullmatch(manifest["view_id"]):
        raise ValueError("Unsupported source-bound preview contract.")
    files: dict[str, bytes] = {}
    for declaration in manifest["files"]:
        pin = pinned_file(declaration)
        relative_path(pin.target)
        if not pin.target.startswith("assets/") or pin.target in files:
            raise ValueError(f"Invalid or repeated asset target: {pin.target}")
        if pin.source != pin.target:
            raise ValueError("Native authority and base assets require their canonical source paths.")
        files[pin.target] = read_pinned(root, pin)
    return files


def verify_material_scopes(
    root: Path, source_pack: bytes, declarations: list[dict], replacements: dict[str, bytes],
) -> dict:
    from io import BytesIO

    from tools.art_pipeline.source_bound_material_guard import verify_material_change

    report: dict[str, dict] = {}
    with zipfile.ZipFile(BytesIO(source_pack)) as archive:
        for declaration in declarations:
            member = declaration["target"]
            mask = pinned_file(declaration["allowed_change_mask"])
            facts = verify_material_change(
                archive.read(member), replacements[member], read_pinned(root, mask),
            )
            report[member] = {
                **facts, "source": declaration["source"], "sha256": declaration["sha256"],
                "allowed_change_mask": {"source": mask.source, "sha256": mask.sha256},
            }
    return report


def apply_pack_updates(root: Path, manifest: dict, files: dict[str, bytes]) -> dict:
    from io import BytesIO

    from tools.art_pipeline.source_bound_pack_scope import verify_pack_scope

    seen: set[str] = set()
    report: dict[str, dict] = {}
    for pack in manifest.get("pack_updates", []):
        target = pack["target"]
        if target in seen or target not in files or not target.endswith(PACK_SUFFIX):
            raise ValueError("Pack update requires a unique pinned pack target.")
        if target != f"assets/official-packs/{manifest['pack_id']}{PACK_SUFFIX}":
            raise ValueError("Replacement pack must be the selected ensemble pack.")
        seen.add(target)
        replacements: dict[str, bytes] = {}
        for value in pack["members"]:
            pin = pinned_file(value)
            relative_path(pin.target)
            if (
                pin.target in replacements or manifest["view_id"] not in pin.target
                or not pin.target.startswith(APPEARANCE_PREFIXES)
                or not pin.target.endswith(".png")
                or not pin.source.startswith("scratchpad/") or not pin.source.endswith(".png")
            ):
                raise ValueError(f"Out-of-scope appearance member: {pin.target}")
            replacements[pin.target] = read_pinned(root, pin)
        with zipfile.ZipFile(BytesIO(files[target])) as archive:
            pack_manifest = json.loads(archive.read("manifest.json"))
        verify_pack_scope(pack_manifest, manifest, set(replacements))
        report[target] = verify_material_scopes(root, files[target], pack["members"], replacements)
        files[target] = rebuild_pack(files[target], replacements)
    return report


def stage_preview(root: Path, manifest: dict, output: Path) -> dict:
    """Validate every input before creating a new, isolated output directory."""
    root = root.resolve()
    output = output.resolve()
    scratch_root = root / "scratchpad"
    if not output.is_relative_to(scratch_root) or output == scratch_root:
        raise ValueError("Preview output must be a new directory under scratchpad.")
    if output.exists():
        raise FileExistsError(output)
    files = collect_inputs(root, manifest)
    native = manifest["native"]
    native_bytes = read_pinned(root, pinned_file(native))
    native_target = f"assets/pose-atlas/v5-base/{manifest['view_id']}.png"
    if (
        native["source"] != native_target or native["target"] != native_target
        or files.get(native_target) != native_bytes
    ):
        raise ValueError("Native authority must be included verbatim at its canonical target.")
    from tools.art_pipeline.source_bound_reference import verify_reference_binding

    verify_reference_binding(root, manifest)
    for provenance in manifest.get("material_provenance", []):
        read_pinned(root, PinnedFile(provenance["path"], provenance["sha256"], "provenance"))
    from tools.art_pipeline.source_bound_identity import verify_native_layers

    identity = verify_native_layers(root, manifest, files)
    materials = apply_pack_updates(root, manifest, files)
    makeup_changes = {}
    if manifest.get("makeup_updates"):
        from tools.art_pipeline.source_bound_makeup import apply_makeup_updates

        makeup_changes = apply_makeup_updates(root, manifest, files)
    output.mkdir(parents=True)
    for relative, data in files.items():
        target = output / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    report = {
        "schema": SCHEMA, "view_id": manifest["view_id"],
        "status": "staged-awaiting-runtime-preview", "formal_integrated": False,
        "native_identity": identity,
        "material_changes": materials,
        "files": {name: digest(data) for name, data in sorted(files.items())},
    }
    if makeup_changes:
        report["makeup_changes"] = makeup_changes
    (output / "input-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    (output / "stage.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report
