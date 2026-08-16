from __future__ import annotations

lazy import argparse
lazy import hashlib
lazy import json
lazy import os
lazy import re
lazy import subprocess
lazy import tomllib
lazy from collections.abc import Iterable, Mapping, Sequence
lazy from dataclasses import dataclass
lazy from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RELEASE_TAG = re.compile(
    r"^v(?P<base>[0-9]+\.[0-9]+\.[0-9]+)"
    r"(?:-rc\.(?P<rc>[1-9][0-9]*))?$"
)
PINNED_REQUIREMENT = re.compile(
    r"^(?P<name>[A-Za-z0-9][A-Za-z0-9._-]*)==(?P<version>[^\s;]+)$"
)
WINDOWS_ABSOLUTE_PATH = re.compile(
    r"(?i)(?:^|(?<=[\s\"'(]))[a-z]:[\\/]+"
)
HOME_ABSOLUTE_PATH = re.compile(
    r"(?i)(?:/home/[^/\s\"']+|/Users/[^/\s\"']+)"
)
SECRET_VALUE = re.compile(
    r"(?i)(?:api[_-]?key|access[_-]?token|client[_-]?secret|password)"
    r"[\s\"']*[:=][\s\"']*[A-Za-z0-9_./+=-]{8,}"
)
SCHEMA_VALIDATION_PROGRAM = """
lazy import sys
lazy from pathlib import Path
from cyclonedx.schema import OutputFormat, SchemaVersion
from cyclonedx.validation import make_schemabased_validator

document = Path(sys.argv[1]).read_text(encoding="utf-8")
error = make_schemabased_validator(
    OutputFormat.JSON,
    SchemaVersion.V1_7,
).validate_str(document)
if error is not None:
    print(error, file=sys.stderr)
    raise SystemExit(1)
"""

type JsonObject = dict[str, object]

ALLOWED_OUTFIT_ASSET_ROLES = frozenset({"garment", "accessory", "occlusion"})
FORBIDDEN_OUTFIT_ASSET_ROLES = frozenset(
    {"identity", "face", "skin-tone", "body-shape", "core-body-skin"}
)


@dataclass(frozen=True, slots=True)
class ComponentPolicy:
    name: str
    version: str
    license_expression: str
    scope: str
    profiles: tuple[str, ...]

    @property
    def normalized_name(self) -> str:
        return normalize_name(self.name)

    @property
    def purl(self) -> str:
        return f"pkg:pypi/{self.normalized_name}@{self.version}"


@dataclass(frozen=True, slots=True)
class AssetPolicy:
    name: str
    version: str
    component_type: str
    path: Path
    sha256: str
    source: str
    source_revision: str
    license_expression: str
    profiles: tuple[str, ...]

    @property
    def bom_ref(self) -> str:
        return f"urn:flameblade:asset:{self.sha256}"


@dataclass(frozen=True, slots=True)
class SbomEntry:
    profile: str
    path: Path
    requirements: Path
    pyproject: Path
    root_name: str


@dataclass(frozen=True, slots=True)
class InventoryResult:
    profile: str
    path: Path
    report: JsonObject


@dataclass(frozen=True, slots=True)
class InventoryRequest:
    entry: SbomEntry
    policies: tuple[ComponentPolicy, ...]
    tag: str
    version: str
    schema_python: Path
    assets: tuple[AssetPolicy, ...] = ()


@dataclass(frozen=True, slots=True)
class ValidatedInventory:
    bom: JsonObject
    components: Mapping[str, JsonObject]
    expected_refs: set[str]
    generators: Mapping[str, str]


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Finalize and validate reproducible CycloneDX release SBOMs."
        )
    )
    parser.add_argument("--tag", required=True)
    parser.add_argument(
        "--policy",
        type=Path,
        default=ROOT / "sbom" / "components.toml",
    )
    parser.add_argument(
        "--entry",
        action="append",
        nargs=5,
        required=True,
        metavar=(
            "PROFILE",
            "SBOM",
            "REQUIREMENTS",
            "PYPROJECT",
            "ROOT_NAME",
        ),
    )
    parser.add_argument("--schema-python", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def normalize_name(value: str) -> str:
    return re.sub(r"[-_.]+", "-", value).casefold()


def _json_object(value: object, context: str) -> JsonObject:
    if not isinstance(value, dict):
        raise TypeError(f"{context} must be an object.")
    if not all(isinstance(key, str) for key in value):
        raise TypeError(f"{context} contains a non-string key.")
    return value


def _object_list(value: object, context: str) -> list[JsonObject]:
    if not isinstance(value, list):
        raise TypeError(f"{context} must be an array.")
    return [
        _json_object(item, f"{context}[{index}]")
        for index, item in enumerate(value)
    ]


def _required_string(
    value: Mapping[str, object],
    key: str,
    context: str,
) -> str:
    candidate = value.get(key)
    if not isinstance(candidate, str) or not candidate:
        raise ValueError(f"{context}.{key} must be a non-empty string.")
    return candidate


def _string_list(value: object, context: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not all(
        isinstance(item, str) and item for item in value
    ):
        raise TypeError(f"{context} must be an array of strings.")
    return tuple(value)


def _load_toml(path: Path) -> JsonObject:
    return _json_object(
        tomllib.loads(path.read_text(encoding="utf-8")),
        str(path),
    )


def _load_json(path: Path) -> JsonObject:
    return _json_object(
        json.loads(path.read_text(encoding="utf-8")),
        str(path),
    )


def _write_json(path: Path, value: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _release_version(tag: str) -> str:
    match = RELEASE_TAG.fullmatch(tag)
    if match is None:
        raise ValueError("SBOM validation requires a vN.N.N or vN.N.N-rc.N tag.")
    rc_number = match.group("rc")
    return (
        match.group("base")
        if rc_number is None
        else f"{match.group('base')}rc{rc_number}"
    )


def _policy_from_row(row: JsonObject, index: int) -> ComponentPolicy:
    context = f"SBOM policy component {index}"
    scope = _required_string(row, "scope", context)
    if scope not in {"runtime", "build"}:
        raise ValueError(f"{context}.scope must be runtime or build.")
    return ComponentPolicy(
        name=_required_string(row, "name", context),
        version=_required_string(row, "version", context),
        license_expression=_required_string(row, "license", context),
        scope=scope,
        profiles=_string_list(row.get("profiles"), f"{context}.profiles"),
    )


def load_policies(path: Path) -> tuple[ComponentPolicy, ...]:
    document = _load_toml(path.resolve())
    if document.get("schema") != 1:
        raise ValueError("Unsupported SBOM component policy schema.")
    policies = tuple(
        _policy_from_row(row, index)
        for index, row in enumerate(
            _object_list(document.get("component"), "SBOM policy components"),
            start=1,
        )
    )
    normalized = [policy.normalized_name for policy in policies]
    if len(normalized) != len(set(normalized)):
        raise ValueError("SBOM component policy contains duplicate names.")
    return policies


def _asset_from_row(row: JsonObject, index: int) -> AssetPolicy:
    context = f"SBOM policy asset {index}"
    component_type = _required_string(row, "type", context)
    if component_type not in {"file", "machine-learning-model"}:
        raise ValueError(f"{context}.type is unsupported.")
    relative_path = Path(_required_string(row, "path", context))
    if relative_path.is_absolute() or ".." in relative_path.parts:
        raise ValueError(f"{context}.path must stay inside the package root.")
    sha256 = _required_string(row, "sha256", context).casefold()
    if re.fullmatch(r"[0-9a-f]{64}", sha256) is None:
        raise ValueError(f"{context}.sha256 must be a SHA-256 digest.")
    source = _required_string(row, "source", context)
    if not source.startswith("https://"):
        raise ValueError(f"{context}.source must use HTTPS.")
    return AssetPolicy(
        name=_required_string(row, "name", context),
        version=_required_string(row, "version", context),
        component_type=component_type,
        path=relative_path,
        sha256=sha256,
        source=source,
        source_revision=_required_string(row, "source_revision", context),
        license_expression=_required_string(row, "license", context),
        profiles=_string_list(row.get("profiles"), f"{context}.profiles"),
    )


def load_asset_policies(path: Path) -> tuple[AssetPolicy, ...]:
    document = _load_toml(path.resolve())
    assets = tuple(
        _asset_from_row(row, index)
        for index, row in enumerate(
            _object_list(document.get("asset", []), "SBOM policy assets"),
            start=1,
        )
    )
    paths = [asset.path.as_posix().casefold() for asset in assets]
    if len(paths) != len(set(paths)):
        raise ValueError("SBOM asset policy contains duplicate paths.")
    return assets


def _required_bool(
    value: Mapping[str, object],
    key: str,
    context: str,
) -> bool:
    candidate = value.get(key)
    if not isinstance(candidate, bool):
        raise TypeError(f"{context}.{key} must be a boolean.")
    return candidate


def _asset_package_identity(document: JsonObject) -> tuple[str, str]:
    package = _json_object(document.get("package"), "asset package")
    package_id = _required_string(package, "id", "asset package")
    version = _required_string(package, "version", "asset package")
    provenance = _required_string(package, "provenance", "asset package")
    if provenance != "original-derivative-design":
        raise ValueError("Asset package provenance must be original-derivative-design.")
    reference_policy = _required_string(
        package,
        "reference_policy",
        "asset package",
    )
    if reference_policy != "design-reference-only":
        raise ValueError("Asset package references must be design-reference-only.")
    return package_id, version


def _approved_core_body_skin(
    document: JsonObject,
    official_core_body_skin: Mapping[str, str],
) -> tuple[str, str]:
    core = _json_object(document.get("core_body_skin"), "core_body_skin reference")
    core_id = _required_string(core, "id", "core_body_skin reference")
    core_hash = _required_string(
        core,
        "sha256",
        "core_body_skin reference",
    ).casefold()
    if re.fullmatch(r"[0-9a-f]{64}", core_hash) is None:
        raise ValueError("core_body_skin reference must use SHA-256.")
    if official_core_body_skin.get(core_id) != core_hash:
        raise ValueError("Asset package must reference an approved core_body_skin hash.")
    return core_id, core_hash


def _asset_package_variant_ids(document: JsonObject) -> set[str]:
    variants = _object_list(document.get("variant"), "asset package variants")
    variant_ids = {
        _required_string(variant, "id", "asset package variant")
        for variant in variants
    }
    if not variant_ids or len(variant_ids) != len(variants):
        raise ValueError("Asset package variants must have unique IDs.")
    return variant_ids


def _asset_package_reference_ids(document: JsonObject) -> tuple[set[str], int]:
    references = _object_list(document.get("reference", []), "design references")
    reference_ids: set[str] = set()
    for reference in references:
        reference_id = _required_string(reference, "id", "design reference")
        if reference_id in reference_ids:
            raise ValueError("Design reference IDs must be unique.")
        reference_ids.add(reference_id)
        source = _required_string(reference, "source", "design reference")
        if not source.startswith("https://"):
            raise ValueError("Design reference source must use HTTPS.")
        _required_string(reference, "license", "design reference")
        policy = _required_string(reference, "policy", "design reference")
        if policy != "design-reference-only":
            raise ValueError("Reality-photo references must be design-reference-only.")
        if _required_bool(reference, "redistributable", "design reference"):
            raise ValueError("Design references must not be redistributable by default.")
        if _required_bool(reference, "packaged", "design reference"):
            raise ValueError("Design references must not be included in the package.")
    return reference_ids, len(references)


def _governed_asset(
    asset: JsonObject,
    variant_ids: set[str],
    reference_ids: set[str],
) -> JsonObject:
    context = "asset package item"
    role = _required_string(asset, "role", context)
    if role in FORBIDDEN_OUTFIT_ASSET_ROLES or role not in ALLOWED_OUTFIT_ASSET_ROLES:
        raise ValueError(f"Asset package role is forbidden: {role}.")
    if _required_string(asset, "provenance", context) != "original-derivative-design":
        raise ValueError("Packaged outfit assets must be original derivative designs.")
    if not _required_bool(asset, "redistributable", context):
        raise ValueError("Packaged outfit assets must have redistribution permission.")
    license_expression = _required_string(asset, "license", context)
    asset_hash = _required_string(asset, "sha256", context).casefold()
    if re.fullmatch(r"[0-9a-f]{64}", asset_hash) is None:
        raise ValueError("Asset package item must use SHA-256.")
    asset_variants = set(_string_list(asset.get("variants"), f"{context}.variants"))
    if not asset_variants or not asset_variants.issubset(variant_ids):
        raise ValueError("Asset package item references an unknown variant.")
    asset_references = set(
        _string_list(asset.get("references", []), f"{context}.references")
    )
    if not asset_references.issubset(reference_ids):
        raise ValueError("Asset package item references unknown provenance.")
    return {
        "license": license_expression,
        "name": _required_string(asset, "name", context),
        "role": role,
        "sha256": asset_hash,
        "variants": sorted(asset_variants),
    }


def validate_asset_package_manifest(
    path: Path,
    *,
    official_core_body_skin: Mapping[str, str],
) -> JsonObject:
    """Validate a multi-variant theme/outfit package without loading its code."""

    document = _load_toml(path.resolve())
    if document.get("schema") != 1:
        raise ValueError("Unsupported asset package manifest schema.")
    package_id, version = _asset_package_identity(document)
    core_id, core_hash = _approved_core_body_skin(document, official_core_body_skin)
    variant_ids = _asset_package_variant_ids(document)
    reference_ids, reference_count = _asset_package_reference_ids(document)
    assets = _object_list(document.get("asset"), "asset package assets")
    if not assets:
        raise ValueError("Asset package must contain at least one governed asset.")
    governed_assets = [
        _governed_asset(asset, variant_ids, reference_ids)
        for asset in assets
    ]
    return {
        "asset_count": len(governed_assets),
        "assets": governed_assets,
        "core_body_skin": {"id": core_id, "sha256": core_hash},
        "package_id": package_id,
        "reference_count": reference_count,
        "status": "pass",
        "variant_count": len(variant_ids),
        "version": version,
    }


def _profile_assets(
    assets: tuple[AssetPolicy, ...],
    profile: str,
) -> tuple[AssetPolicy, ...]:
    return tuple(asset for asset in assets if profile in asset.profiles)


def _entry(raw: Sequence[str]) -> SbomEntry:
    profile, path, requirements, pyproject, root_name = raw
    return SbomEntry(
        profile=profile,
        path=Path(path).resolve(),
        requirements=Path(requirements).resolve(),
        pyproject=Path(pyproject).resolve(),
        root_name=root_name,
    )


def _entries(raw_entries: Iterable[Sequence[str]]) -> tuple[SbomEntry, ...]:
    entries = tuple(_entry(raw) for raw in raw_entries)
    profiles = [entry.profile for entry in entries]
    if len(profiles) != len(set(profiles)):
        raise ValueError("Each SBOM profile must appear exactly once.")
    return entries


def _profile_policies(
    policies: tuple[ComponentPolicy, ...],
    profile: str,
) -> tuple[ComponentPolicy, ...]:
    selected = tuple(
        policy
        for policy in policies
        if policy.scope == "runtime" and profile in policy.profiles
    )
    if not selected:
        raise ValueError(f"No runtime component policy for {profile!r}.")
    return selected


def _pinned_requirements(path: Path) -> dict[str, str]:
    requirements: dict[str, str] = {}
    for line_number, raw_line in enumerate(
        path.read_text(encoding="utf-8").splitlines(),
        start=1,
    ):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        match = PINNED_REQUIREMENT.fullmatch(line)
        if match is None:
            raise ValueError(
                f"{path.name}:{line_number} is not an exact name==version pin."
            )
        name = normalize_name(match.group("name"))
        if name in requirements:
            raise ValueError(f"Duplicate requirement {name!r} in {path.name}.")
        requirements[name] = match.group("version")
    return requirements


def _expected_versions(
    policies: tuple[ComponentPolicy, ...],
) -> dict[str, str]:
    return {
        policy.normalized_name: policy.version
        for policy in policies
    }


def _project_metadata(
    entry: SbomEntry,
    expected_version: str,
    policies: tuple[ComponentPolicy, ...],
) -> None:
    document = _load_toml(entry.pyproject)
    project = _json_object(document.get("project"), "PEP 621 project")
    if _required_string(project, "name", "project") != entry.root_name:
        raise ValueError(f"{entry.pyproject.name} root component name drifted.")
    if _required_string(project, "version", "project") != expected_version:
        raise ValueError(f"{entry.pyproject.name} release version drifted.")
    if project.get("license") != "MIT":
        raise ValueError(f"{entry.pyproject.name} must declare MIT.")
    dependencies = _string_list(
        project.get("dependencies"),
        f"{entry.pyproject.name} project.dependencies",
    )
    parsed: dict[str, str] = {}
    for dependency in dependencies:
        match = PINNED_REQUIREMENT.fullmatch(dependency)
        if match is None:
            raise ValueError(
                f"{entry.pyproject.name} has an unpinned dependency."
            )
        parsed[normalize_name(match.group("name"))] = match.group("version")
    if parsed != _expected_versions(policies):
        raise ValueError(f"{entry.pyproject.name} dependency policy drifted.")


def _metadata_and_root(bom: JsonObject) -> tuple[JsonObject, JsonObject]:
    metadata = _json_object(bom.get("metadata"), "CycloneDX metadata")
    root = _json_object(
        metadata.get("component"),
        "CycloneDX root component",
    )
    return metadata, root


def _license_values(component: Mapping[str, object]) -> tuple[str, ...]:
    values: list[str] = []
    for choice in _object_list(
        component.get("licenses"),
        f"{component.get('name', 'component')} licenses",
    ):
        expression = choice.get("expression")
        if isinstance(expression, str):
            values.append(expression)
            continue
        license_data = _json_object(
            choice.get("license"),
            "CycloneDX license choice",
        )
        values.append(
            _required_string(license_data, "id", "CycloneDX license")
        )
    return tuple(values)


def _component_index(
    bom: JsonObject,
) -> tuple[dict[str, JsonObject], set[str]]:
    index: dict[str, JsonObject] = {}
    bom_refs: set[str] = set()
    for component in _object_list(
        bom.get("components"),
        "CycloneDX components",
    ):
        name = normalize_name(
            _required_string(component, "name", "CycloneDX component")
        )
        bom_ref = _required_string(
            component,
            "bom-ref",
            f"CycloneDX component {name}",
        )
        if name in index:
            raise ValueError(f"Duplicate CycloneDX component name: {name}.")
        if bom_ref in bom_refs:
            raise ValueError(f"Duplicate CycloneDX bom-ref: {bom_ref}.")
        index[name] = component
        bom_refs.add(bom_ref)
    return index, bom_refs


def _validate_header(bom: JsonObject) -> None:
    if bom.get("bomFormat") != "CycloneDX":
        raise ValueError("Release inventory is not CycloneDX.")
    if bom.get("specVersion") != "1.7":
        raise ValueError("Release SBOM must use CycloneDX 1.7.")
    if bom.get("version") != 1:
        raise ValueError("Release SBOM document version must be 1.")
    if "serialNumber" in bom:
        raise ValueError("Reproducible SBOM must not contain a random serial number.")


def _validate_reproducible_metadata(metadata: JsonObject) -> None:
    if "timestamp" in metadata:
        raise ValueError("Reproducible SBOM must not contain a timestamp.")
    properties = _object_list(
        metadata.get("properties"),
        "CycloneDX metadata properties",
    )
    property_values = {
        _required_string(item, "name", "CycloneDX metadata property"): (
            _required_string(item, "value", "CycloneDX metadata property")
        )
        for item in properties
    }
    if property_values.get("cdx:reproducible") != "true":
        raise ValueError("CycloneDX output is not marked reproducible.")


def _tool_versions(metadata: JsonObject) -> dict[str, str]:
    tools = _json_object(metadata.get("tools"), "CycloneDX metadata.tools")
    versions = {
        _required_string(tool, "name", "CycloneDX generator"): (
            _required_string(tool, "version", "CycloneDX generator")
        )
        for tool in _object_list(
            tools.get("components"),
            "CycloneDX generator components",
        )
    }
    if versions.get("cyclonedx-py") != "7.3.0":
        raise ValueError("Release SBOM was not generated by cyclonedx-py 7.3.0.")
    return dict(sorted(versions.items()))


def _validate_root(
    root: JsonObject,
    entry: SbomEntry,
    expected_version: str,
) -> str:
    if _required_string(root, "name", "CycloneDX root") != entry.root_name:
        raise ValueError(f"{entry.profile} SBOM root name drifted.")
    if _required_string(root, "version", "CycloneDX root") != expected_version:
        raise ValueError(f"{entry.profile} SBOM root version drifted.")
    if root.get("type") != "application":
        raise ValueError(f"{entry.profile} SBOM root must be an application.")
    if set(_license_values(root)) != {"MIT"}:
        raise ValueError(f"{entry.profile} SBOM root license must be MIT.")
    external_references = _object_list(
        root.get("externalReferences"),
        "CycloneDX root external references",
    )
    reference_types = {
        _required_string(reference, "type", "external reference")
        for reference in external_references
    }
    if not {"issue-tracker", "vcs", "website"}.issubset(reference_types):
        raise ValueError(f"{entry.profile} SBOM root references are incomplete.")
    return _required_string(root, "bom-ref", "CycloneDX root")


def _set_component_license(
    component: JsonObject,
    policy: ComponentPolicy,
) -> None:
    component["licenses"] = [
        {
            "expression": policy.license_expression,
            "acknowledgement": "declared",
        }
    ]


def _validate_components(
    components: dict[str, JsonObject],
    policies: tuple[ComponentPolicy, ...],
) -> dict[str, str]:
    expected_names = {policy.normalized_name for policy in policies}
    if set(components) != expected_names:
        missing = sorted(expected_names - set(components))
        unexpected = sorted(set(components) - expected_names)
        raise ValueError(
            f"CycloneDX component set drifted; missing={missing}, "
            f"unexpected={unexpected}."
        )
    refs: dict[str, str] = {}
    for policy in policies:
        component = components[policy.normalized_name]
        if component.get("type") != "library":
            raise ValueError(f"{policy.name} must be a CycloneDX library.")
        if component.get("version") != policy.version:
            raise ValueError(f"{policy.name} SBOM version drifted.")
        if component.get("purl") != policy.purl:
            raise ValueError(f"{policy.name} SBOM PURL drifted.")
        _set_component_license(component, policy)
        refs[policy.normalized_name] = _required_string(
            component,
            "bom-ref",
            policy.name,
        )
    return refs


def _asset_component(asset: AssetPolicy) -> JsonObject:
    source_revision = asset.source_revision
    properties = [
        {
            "name": "com.flamebladestudio.asset.package-path",
            "value": asset.path.as_posix(),
        },
        {
            "name": "com.flamebladestudio.asset.source-revision",
            "value": source_revision,
        },
    ]
    return {
        "type": asset.component_type,
        "name": asset.name,
        "version": asset.version,
        "bom-ref": asset.bom_ref,
        "hashes": [{"alg": "SHA-256", "content": asset.sha256}],
        "licenses": [
            {
                "expression": asset.license_expression,
                "acknowledgement": "declared",
            }
        ],
        "externalReferences": [
            {"type": "distribution", "url": asset.source}
        ],
        "properties": properties,
    }


def _add_and_validate_assets(
    bom: JsonObject,
    assets: tuple[AssetPolicy, ...],
    *,
    package_root: Path = ROOT,
) -> set[str]:
    components = _object_list(bom.get("components"), "CycloneDX components")
    existing_refs = {
        _required_string(component, "bom-ref", "CycloneDX component")
        for component in components
    }
    refs: set[str] = set()
    for asset in assets:
        path = package_root / asset.path
        if not path.is_file():
            raise FileNotFoundError(f"SBOM asset is not packaged: {asset.path.as_posix()}")
        if _sha256(path) != asset.sha256:
            raise ValueError(f"SBOM asset hash drifted: {asset.path.as_posix()}")
        if asset.bom_ref in existing_refs or asset.bom_ref in refs:
            raise ValueError(f"Duplicate CycloneDX asset bom-ref: {asset.bom_ref}.")
        components.append(_asset_component(asset))
        refs.add(asset.bom_ref)
    bom["components"] = components
    dependencies = _object_list(bom.get("dependencies"), "CycloneDX dependencies")
    dependencies.extend({"ref": reference, "dependsOn": []} for reference in sorted(refs))
    bom["dependencies"] = dependencies
    return refs


def _set_root_properties(
    root: JsonObject,
    entry: SbomEntry,
    tag: str,
) -> None:
    managed = {
        "com.flamebladestudio.sbom.inventory-basis": (
            "pinned-runtime-requirements-and-packaged-assets"
        ),
        "com.flamebladestudio.sbom.profile": entry.profile,
        "com.flamebladestudio.sbom.release-tag": tag,
        "com.flamebladestudio.sbom.python": "3.15",
    }
    existing = _object_list(
        root.get("properties", []),
        "CycloneDX root properties",
    )
    preserved = [
        item
        for item in existing
        if item.get("name") not in managed
    ]
    root["properties"] = [
        *preserved,
        *(
            {"name": name, "value": value}
            for name, value in sorted(managed.items())
        ),
    ]


def _dependency_index(bom: JsonObject) -> dict[str, JsonObject]:
    dependencies: dict[str, JsonObject] = {}
    for dependency in _object_list(
        bom.get("dependencies"),
        "CycloneDX dependencies",
    ):
        reference = _required_string(
            dependency,
            "ref",
            "CycloneDX dependency",
        )
        if reference in dependencies:
            raise ValueError(f"Duplicate CycloneDX dependency ref: {reference}.")
        dependencies[reference] = dependency
    return dependencies


def _finalize_dependency_graph(
    bom: JsonObject,
    root_ref: str,
    component_refs: set[str],
) -> None:
    dependencies = _dependency_index(bom)
    valid_refs = {root_ref, *component_refs}
    if set(dependencies) != valid_refs:
        raise ValueError("CycloneDX dependency node set is incomplete.")
    dependencies[root_ref]["dependsOn"] = sorted(component_refs)
    for reference, dependency in dependencies.items():
        depends_on = _string_list(
            dependency.get("dependsOn", []),
            f"CycloneDX dependency {reference}.dependsOn",
        )
        if len(depends_on) != len(set(depends_on)):
            raise ValueError(f"Duplicate dependency edge from {reference}.")
        if not set(depends_on).issubset(valid_refs):
            raise ValueError(f"Dangling dependency edge from {reference}.")


def _privacy_content_gate(content: str, label: str) -> None:
    if WINDOWS_ABSOLUTE_PATH.search(content):
        raise ValueError(f"{label} contains a Windows absolute path.")
    if HOME_ABSOLUTE_PATH.search(content):
        raise ValueError(f"{label} contains a home-directory path.")
    if "file://" in content.casefold():
        raise ValueError(f"{label} contains a local file URI.")
    if SECRET_VALUE.search(content):
        raise ValueError(f"{label} contains a secret-like value.")


def _privacy_gate(path: Path) -> None:
    _privacy_content_gate(path.read_text(encoding="utf-8"), path.name)


def _schema_gate(schema_python: Path, path: Path) -> None:
    if not schema_python.is_file():
        raise FileNotFoundError(f"Schema Python not found: {schema_python}")
    environment = os.environ.copy()
    environment["PYTHONUTF8"] = "1"
    completed = subprocess.run(
        [
            str(schema_python),
            "-c",
            SCHEMA_VALIDATION_PROGRAM,
            str(path),
        ],
        cwd=ROOT,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if completed.returncode:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise RuntimeError(
            f"CycloneDX 1.7 schema validation failed for {path.name}: {detail}"
        )


def _component_report(
    policies: tuple[ComponentPolicy, ...],
) -> list[JsonObject]:
    return [
        {
            "license": policy.license_expression,
            "name": policy.name,
            "purl": policy.purl,
            "version": policy.version,
        }
        for policy in sorted(
            policies,
            key=lambda item: item.normalized_name,
        )
    ]


def _asset_report(assets: tuple[AssetPolicy, ...]) -> list[JsonObject]:
    return [
        {
            "license": asset.license_expression,
            "name": asset.name,
            "package_path": asset.path.as_posix(),
            "sha256": asset.sha256,
            "source": asset.source,
            "source_revision": asset.source_revision,
            "type": asset.component_type,
            "version": asset.version,
        }
        for asset in sorted(assets, key=lambda item: item.path.as_posix())
    ]


def _validated_component_refs(
    bom: JsonObject,
    request: InventoryRequest,
) -> tuple[Mapping[str, JsonObject], set[str]]:
    asset_refs = _add_and_validate_assets(bom, request.assets)
    components, component_refs = _component_index(bom)
    asset_names = {normalize_name(asset.name) for asset in request.assets}
    python_components = {
        name: component
        for name, component in components.items()
        if name not in asset_names
    }
    expected_refs = {
        *_validate_components(python_components, request.policies).values(),
        *asset_refs,
    }
    if component_refs != expected_refs:
        raise ValueError(f"{request.entry.profile} SBOM component references drifted.")
    return components, expected_refs


def _validated_inventory(request: InventoryRequest) -> ValidatedInventory:
    entry = request.entry
    requirements = _pinned_requirements(entry.requirements)
    expected = _expected_versions(request.policies)
    if requirements != expected:
        raise ValueError(f"{entry.requirements.name} dependency policy drifted.")
    _project_metadata(entry, request.version, request.policies)

    bom = _load_json(entry.path)
    _validate_header(bom)
    metadata, root = _metadata_and_root(bom)
    _validate_reproducible_metadata(metadata)
    generators = _tool_versions(metadata)
    root_ref = _validate_root(root, entry, request.version)
    components, expected_refs = _validated_component_refs(bom, request)
    _set_root_properties(root, entry, request.tag)
    _finalize_dependency_graph(bom, root_ref, expected_refs)
    return ValidatedInventory(bom, components, expected_refs, generators)


def finalize_inventory(request: InventoryRequest) -> InventoryResult:
    entry = request.entry
    validated = _validated_inventory(request)

    _write_json(entry.path, validated.bom)
    _privacy_gate(entry.path)
    _schema_gate(request.schema_python, entry.path)
    report: JsonObject = {
        "artifact": entry.path.name,
        "asset_count": len(request.assets),
        "assets": _asset_report(request.assets),
        "component_count": len(validated.components),
        "components": _component_report(request.policies),
        "dependency_edge_count": len(validated.expected_refs),
        "dependency_node_count": len(validated.expected_refs) + 1,
        "generator_versions": validated.generators,
        "inventory_basis": "pinned-runtime-requirements-and-packaged-assets",
        "license_coverage_percent": 100.0,
        "profile": entry.profile,
        "purl_coverage_percent": 100.0,
        "requirements": entry.requirements.name,
        "reproducible": True,
        "root_component": entry.root_name,
        "schema_validation": "pass",
        "sha256": _sha256(entry.path),
        "spec_version": "1.7",
        "status": "pass",
        "version": request.version,
    }
    return InventoryResult(entry.profile, entry.path, report)


def _build_policy_report(
    policies: tuple[ComponentPolicy, ...],
) -> JsonObject:
    build_components = [
        {
            "license": policy.license_expression,
            "name": policy.name,
            "profiles": list(policy.profiles),
            "version": policy.version,
        }
        for policy in policies
        if policy.scope == "build"
    ]
    return {
        "build_components_tracked_separately": build_components,
        "component_count": len(policies),
        "runtime_component_count": sum(
            policy.scope == "runtime" for policy in policies
        ),
    }


def main() -> int:
    args = arguments()
    version = _release_version(args.tag)
    policies = load_policies(args.policy)
    assets = load_asset_policies(args.policy)
    entries = _entries(args.entry)
    results = tuple(
        finalize_inventory(
            InventoryRequest(
                entry=entry,
                policies=_profile_policies(policies, entry.profile),
                tag=args.tag,
                version=version,
                schema_python=args.schema_python.resolve(),
                assets=_profile_assets(assets, entry.profile),
            )
        )
        for entry in entries
    )
    report: JsonObject = {
        "cyclonedx_spec": "1.7",
        "inventories": [result.report for result in results],
        "policy": _build_policy_report(policies),
        "release_tag": args.tag,
        "release_version": version,
        "schema": "mohan.sbom.validation.v1",
        "status": "pass",
    }
    _write_json(args.output.resolve(), report)
    _privacy_gate(args.output.resolve())
    print(f"MOHAN_RELEASE_SBOM_VALIDATION_OK={args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
