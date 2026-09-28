"""Audit quality-tool licenses and write a machine-readable inventory."""

from __future__ import annotations

lazy import argparse
lazy import json
lazy import re
lazy import shutil
lazy import subprocess
lazy import sys
lazy import tomllib
lazy from importlib import metadata
lazy from pathlib import Path
lazy from typing import Any

ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / "tools" / "quality_licenses.json"
SBOM_PATH = ROOT / "sbom" / "components.toml"
DEFAULT_OUTPUT = ROOT / ".quality-tmp" / "python-license-inventory.json"
REQUIREMENT_NAME = re.compile(r"\s*([A-Za-z0-9][A-Za-z0-9._-]*)")
LICENSE_SEPARATOR = re.compile(r"\s+(?:AND|OR|WITH)\s+|[;,]", re.IGNORECASE)
LICENSE_ALIASES = {
    "apache 2.0": "Apache-2.0",
    "apache license 2.0": "Apache-2.0",
    "apache software license": "Apache-2.0",
    "apache-2.0": "Apache-2.0",
    "bsd": "BSD",
    "bsd license": "BSD",
    "bsd-2-clause": "BSD-2-Clause",
    "bsd 2-clause license": "BSD-2-Clause",
    "bsd-3-clause": "BSD-3-Clause",
    "bsd 3-clause license": "BSD-3-Clause",
    "isc": "ISC",
    "isc license": "ISC",
    "mit": "MIT",
    "mit license": "MIT",
    "mpl 2.0": "MPL-2.0",
    "mpl-2.0": "MPL-2.0",
    "mozilla public license 2.0": "MPL-2.0",
    "mozilla public license 2.0 mpl 2.0": "MPL-2.0",
    "mozilla public license 2.0 (mpl 2.0)": "MPL-2.0",
    "psf": "PSF",
    "psf-2.0": "PSF",
    "python software foundation license": "PSF",
    "python software foundation license 2.0": "PSF",
}


def normalize_name(name: str) -> str:
    """Normalize a distribution name according to PEP 503."""
    return re.sub(r"[-_.]+", "-", name).casefold()


def normalize_license_expression(expression: str) -> tuple[str, ...]:
    """Return canonical license atoms; preserve unknown values for fail-closed checks."""
    atoms: list[str] = []
    normalized_expression = expression.replace("(", "").replace(")", "").strip()
    for raw_atom in LICENSE_SEPARATOR.split(normalized_expression):
        atom = " ".join(raw_atom.strip().strip("() ").casefold().split())
        if not atom:
            continue
        atoms.append(LICENSE_ALIASES.get(atom, f"UNRECOGNIZED:{atom}"))
    return tuple(sorted(set(atoms)))


def _load_policy() -> dict[str, Any]:
    policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    if policy.get("schema") != 1:
        raise ValueError("quality license policy schema must be 1")
    allowed = policy.get("allowed_licenses")
    tools = policy.get("quality_tools")
    if not isinstance(allowed, list) or not isinstance(tools, dict):
        raise ValueError("quality license policy is missing its allow-list or tools")
    for name, record in tools.items():
        if (
            not isinstance(record, dict)
            or not isinstance(record.get("version"), str)
            or not isinstance(record.get("license"), str)
        ):
            raise ValueError(f"invalid quality tool policy entry: {name}")
    return policy


def _installed_distributions() -> dict[str, metadata.Distribution]:
    grouped: dict[str, list[metadata.Distribution]] = {}
    for distribution in metadata.distributions():
        name = distribution.metadata.get("Name")
        if name:
            grouped.setdefault(normalize_name(name), []).append(distribution)

    prefix = Path(sys.prefix).resolve()
    installed: dict[str, metadata.Distribution] = {}
    for name, candidates in grouped.items():
        active = [
            distribution
            for distribution in candidates
            if _distribution_is_within(distribution, prefix)
        ]
        # A venv can expose system-site-packages too. Prefer its own metadata and
        # leave unrelated system duplicates out of the audit decision.
        selected = active or candidates
        installed[name] = sorted(
            selected,
            key=lambda distribution: (
                distribution.version,
                distribution.metadata.get("Name", "").casefold(),
            ),
        )[-1]
    return installed


def _distribution_is_within(
    distribution: metadata.Distribution, directory: Path
) -> bool:
    try:
        location = Path(distribution.locate_file("")).resolve()
        return location.is_relative_to(directory)
    except (OSError, TypeError, ValueError):
        return False


def _dependency_names(
    installed: dict[str, metadata.Distribution],
    roots: set[str],
) -> set[str]:
    pending = list(roots)
    found: set[str] = set()
    while pending:
        name = pending.pop()
        if name in found:
            continue
        distribution = installed.get(name)
        if distribution is None:
            raise ValueError(f"required quality tool is not installed: {name}")
        found.add(name)
        for raw_requirement in distribution.requires or ():
            match = REQUIREMENT_NAME.match(raw_requirement)
            if match is None:
                raise ValueError(
                    f"cannot read dependency metadata for {distribution.metadata['Name']}: "
                    f"{raw_requirement}"
                )
            dependency = normalize_name(match.group(1))
            if dependency in installed and dependency not in found:
                pending.append(dependency)
    return found


def _license_command() -> list[str]:
    executable_names = ("pip-licenses.exe", "pip-licenses")
    script_directories = (Path(sys.prefix) / "Scripts", Path(sys.prefix) / "bin")
    for directory in script_directories:
        for executable_name in executable_names:
            executable = directory / executable_name
            if executable.is_file():
                return [str(executable), "--format=json", "--with-system"]
    executable = shutil.which("pip-licenses")
    if executable is None:
        raise FileNotFoundError(
            "pip-licenses is not installed in the active Python environment"
        )
    return [executable, "--format=json", "--with-system"]


def _validated_license_records(rows: object) -> list[dict[str, str]]:
    if not isinstance(rows, list):
        raise ValueError("pip-licenses JSON output must be a list")
    records: list[dict[str, str]] = []
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("pip-licenses returned a malformed package row")
        name = row.get("Name")
        version = row.get("Version")
        license_name = row.get("License")
        if not all(
            isinstance(value, str) and value.strip()
            for value in (name, version, license_name)
        ):
            raise ValueError(f"pip-licenses omitted name, version, or license: {row!r}")
        records.append({"name": name, "version": version, "license": license_name})
    return sorted(
        records,
        key=lambda record: (normalize_name(record["name"]), record["version"]),
    )


def _license_records() -> list[dict[str, str]]:
    result = subprocess.run(
        _license_command(),
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return _validated_license_records(json.loads(result.stdout))


def _runtime_sbom_components() -> dict[str, dict[str, str]]:
    document = tomllib.loads(SBOM_PATH.read_text(encoding="utf-8"))
    return {
        normalize_name(component["name"]): {
            "name": component["name"],
            "version": component["version"],
            "license": component["license"],
        }
        for component in document.get("component", [])
        if component.get("scope") == "runtime"
    }


def _same_license(actual: tuple[str, ...], expected: tuple[str, ...]) -> bool:
    if actual == expected:
        return True
    return (
        len(expected) == 1
        and expected[0].startswith("BSD-")
        and actual == ("BSD",)
    )


def build_report(
    policy: dict[str, Any],
    installed: dict[str, metadata.Distribution],
    license_rows: list[dict[str, str]],
) -> dict[str, Any]:
    """Validate the quality-tool dependency closure and prepare JSON output."""
    tool_policy: dict[str, dict[str, str]] = {
        normalize_name(name): record for name, record in policy["quality_tools"].items()
    }
    allowed = set(policy["allowed_licenses"])
    roots = set(tool_policy)
    dependency_names = _dependency_names(installed, roots)
    license_by_name: dict[str, list[dict[str, str]]] = {}
    for row in license_rows:
        license_by_name.setdefault(normalize_name(row["name"]), []).append(row)
    release_components = _runtime_sbom_components()
    issues: list[str] = []
    checked: list[dict[str, Any]] = []

    for name in sorted(dependency_names):
        distribution = installed[name]
        candidates = license_by_name.get(name, [])
        matching_rows = [
            row for row in candidates if row["version"] == distribution.version
        ]
        if not matching_rows:
            issues.append(f"pip-licenses omitted quality tool dependency: {name}")
            continue
        row = matching_rows[0]
        matching_licenses = {
            normalize_license_expression(candidate["license"])
            for candidate in matching_rows
        }
        if len(matching_licenses) > 1:
            issues.append(f"pip-licenses returned conflicting licenses for {name}")
        atoms = normalize_license_expression(row["license"])
        tool = tool_policy.get(name)
        expected = tool["license"] if tool is not None else None
        if tool is not None and distribution.version != tool["version"]:
            issues.append(
                f"{row['name']} version {distribution.version} does not match pinned "
                f"version {tool['version']}"
            )
        if tool is not None and expected is not None:
            expected_atoms = normalize_license_expression(expected)
            if not _same_license(atoms, expected_atoms):
                issues.append(
                    f"{row['name']} license {row['license']!r} does not match "
                    f"the reviewed license {expected!r}"
                )
        existing_component = release_components.get(name)
        release_match = False
        if existing_component is not None:
            release_match = (
                row["version"] == existing_component["version"]
                and _same_license(
                    atoms,
                    normalize_license_expression(existing_component["license"]),
                )
            )
        if not set(atoms).issubset(allowed) and not (tool is None and release_match):
            issues.append(f"{row['name']} has a non-allow-listed license: {row['license']}")
        checked.append(
            {
                **row,
                "normalized_licenses": list(atoms),
                "quality_tool": tool is not None,
                "existing_runtime_component": release_match,
                "allow_listed": set(atoms).issubset(allowed),
            }
        )

    return {
        "schema": 1,
        "policy": str(POLICY_PATH.relative_to(ROOT)),
        "generator": "pip-licenses --format=json --with-system",
        "allowed_licenses": sorted(allowed),
        "quality_tools": [
            {
                "name": policy_name,
                "version": tool_policy[normalize_name(policy_name)]["version"],
                "license": tool_policy[normalize_name(policy_name)]["license"],
            }
            for policy_name in sorted(policy["quality_tools"])
        ],
        "all_installed_distributions": license_rows,
        "checked_quality_tool_dependency_closure": checked,
        "issues": issues,
    }


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check quality-tool licenses and write a JSON inventory."
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> int:
    args = arguments()
    output_path = args.output.resolve()
    if not output_path.is_relative_to(ROOT.resolve()):
        raise SystemExit("license inventory output must remain inside the worktree")
    if (ROOT / "artifacts").resolve() in output_path.parents:
        raise SystemExit("license inventory output cannot be written under artifacts/")

    try:
        policy = _load_policy()
        report = build_report(policy, _installed_distributions(), _license_records())
    except (OSError, subprocess.CalledProcessError, ValueError) as error:
        print(f"PYTHON_LICENSE_AUDIT_ERROR: {error}", file=sys.stderr)
        return 1

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    if report["issues"]:
        for issue in report["issues"]:
            print(f"LICENSE_POLICY_FAILURE: {issue}", file=sys.stderr)
        return 1
    print(
        "PYTHON_LICENSES_OK "
        f"checked={len(report['checked_quality_tool_dependency_closure'])} "
        f"inventory={output_path.relative_to(ROOT.resolve())}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
