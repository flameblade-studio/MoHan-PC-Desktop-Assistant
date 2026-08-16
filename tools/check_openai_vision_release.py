from __future__ import annotations

lazy import argparse
lazy import json
lazy import re
lazy import tomllib
lazy from dataclasses import dataclass
lazy from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PINNED = re.compile(r"^(?P<name>[A-Za-z0-9._-]+)==(?P<version>[^\s;]+)$")


@dataclass(frozen=True, slots=True)
class GateResult:
    required: bool
    passed: bool
    issues: tuple[str, ...]

    def as_json(self) -> str:
        return json.dumps(
            {
                "issues": list(self.issues),
                "passed": self.passed,
                "required": self.required,
            },
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )


def _version_tuple(value: str) -> tuple[int, int, int]:
    match = re.fullmatch(r"v?(\d+)\.(\d+)\.(\d+)(?:-rc\.\d+)?", value)
    if match is None:
        raise ValueError("version must use N.N.N or vN.N.N[-rc.N]")
    return tuple(int(part) for part in match.groups())


def _requirements(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        match = PINNED.fullmatch(line)
        if match is None:
            continue
        name = re.sub(r"[-_.]+", "-", match.group("name")).casefold()
        result[name] = match.group("version")
    return result


def _project_dependencies(path: Path) -> dict[str, str]:
    document = tomllib.loads(path.read_text(encoding="utf-8"))
    dependencies = document["project"]["dependencies"]
    if not isinstance(dependencies, list):
        raise TypeError("project.dependencies must be a list")
    result: dict[str, str] = {}
    for dependency in dependencies:
        if not isinstance(dependency, str):
            raise TypeError("project dependency must be a string")
        match = PINNED.fullmatch(dependency)
        if match is None:
            continue
        name = re.sub(r"[-_.]+", "-", match.group("name")).casefold()
        result[name] = match.group("version")
    return result


def _components(path: Path) -> dict[str, dict[str, object]]:
    document = tomllib.loads(path.read_text(encoding="utf-8"))
    rows = document.get("component", [])
    if not isinstance(rows, list):
        raise TypeError("SBOM components must be a list")
    result: dict[str, dict[str, object]] = {}
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("name"), str):
            raise TypeError("SBOM component is malformed")
        name = re.sub(r"[-_.]+", "-", row["name"]).casefold()
        result[name] = row
    return result


def _dependency_issues(root: Path, package: str) -> list[str]:
    install = _requirements(root / "requirements.txt").get(package)
    runtime = _requirements(root / "requirements-runtime.txt").get(package)
    project = _project_dependencies(root / "pyproject.toml").get(package)
    component = _components(root / "sbom" / "components.toml").get(package)
    issues: list[str] = []
    if install is None:
        issues.append(f"{package}:missing-install-pin")
    if runtime is None:
        issues.append(f"{package}:missing-runtime-pin")
    if project is None:
        issues.append(f"{package}:missing-pyproject-pin")
    versions = {version for version in (install, runtime, project) if version}
    if len(versions) > 1:
        issues.append(f"{package}:version-drift")
    if component is None:
        issues.append(f"{package}:missing-sbom-component")
        return issues
    if component.get("version") not in versions or not versions:
        issues.append(f"{package}:sbom-version-drift")
    license_expression = component.get("license")
    if not isinstance(license_expression, str) or not license_expression.strip():
        issues.append(f"{package}:missing-verified-license")
    profiles = component.get("profiles")
    if not isinstance(profiles, list) or "windows" not in profiles:
        issues.append(f"{package}:missing-windows-profile")
    return issues


def _openai_sdk_issues(root: Path) -> list[str]:
    dependency_names = {
        *_requirements(root / "requirements.txt"),
        *_requirements(root / "requirements-runtime.txt"),
        *_project_dependencies(root / "pyproject.toml"),
        *_components(root / "sbom" / "components.toml"),
    }
    issues: list[str] = []
    if "openai" in dependency_names:
        issues.append("openai:third-party-sdk-must-not-be-required")
    build = (root / "build.ps1").read_text(encoding="utf-8")
    if re.search(r"collect-all[^\r\n]*openai", build, re.IGNORECASE):
        issues.append("openai:pyinstaller-sdk-collection-forbidden")
    return issues


def evaluate(root: Path, version: str) -> GateResult:
    required = _version_tuple(version) >= (4, 0, 0)
    if not required:
        return GateResult(False, True, ())

    issues = [
        *_dependency_issues(root, "opencv-python"),
        *_openai_sdk_issues(root),
    ]
    provider = (root / "integrations" / "openai_vision_provider.py").read_text(
        encoding="utf-8"
    )
    required_sources = (
        '"https://api.openai.com/v1/responses"',
        "urllib.request import Request, urlopen",
        "store=False",
    )
    issues.extend(
        "openai:stdlib-responses-contract-missing"
        for required_source in required_sources
        if required_source not in provider
    )
    if re.search(r"(?:^|\s)(?:lazy\s+)?import\s+openai(?:\s|$)", provider):
        issues.append("openai:provider-sdk-import-forbidden")
    if 'import_module("openai")' in provider or "openai.OpenAI(" in provider:
        issues.append("openai:provider-sdk-import-forbidden")

    preview_requirements = "\n".join(
        (root / name).read_text(encoding="utf-8")
        for name in ("requirements-preview.txt", "requirements-preview-runtime.txt")
    ).casefold()
    preview_project = (root / "sbom" / "preview.pyproject.toml").read_text(
        encoding="utf-8"
    ).casefold()
    if "openai==" in preview_requirements or '"openai==' in preview_project:
        issues.append("openai:preview-must-remain-limited")

    unique = tuple(sorted(set(issues)))
    return GateResult(True, not unique, unique)


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fail closed when a v4 OpenAI Vision release is not reproducible."
    )
    parser.add_argument("--version", required=True)
    parser.add_argument("--root", type=Path, default=ROOT)
    return parser.parse_args()


def main() -> int:
    args = arguments()
    result = evaluate(args.root.resolve(), args.version)
    print(result.as_json())
    return 0 if result.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
