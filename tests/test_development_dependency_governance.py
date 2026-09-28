from __future__ import annotations

lazy import ast
lazy import json
lazy import re
lazy import tomllib
lazy from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_DEVELOPMENT_DEPENDENCIES = {
    "deptry": "0.25.1",
    "pip-audit": "2.10.1",
    "pip-licenses": "5.5.5",
    "pyright": "1.1.414",
    "pytest": "9.1.1",
    "ruff": "0.16.0",
    "vulture": "2.16",
}
# New gate tools must use the owner-approved permissive allow-list.
ALLOWED_QUALITY_TOOL_LICENSES = frozenset({"Apache-2.0", "BSD-2-Clause", "MIT"})
DEVELOPMENT_PROFILES = ["ci", "local"]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _normalized_name(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).casefold()


def _pinned_requirements(relative: str) -> dict[str, str]:
    requirements: dict[str, str] = {}
    for raw_line in _read(relative).splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        match = re.fullmatch(
            r"(?P<name>[A-Za-z0-9][A-Za-z0-9._-]*)=="
            r"(?P<version>[0-9]+(?:\.[0-9]+)+)",
            line,
        )
        assert match is not None, (
            f"{relative} must use stable exact pins only: {line!r}"
        )
        name = _normalized_name(match.group("name"))
        assert name not in requirements, f"duplicate dependency in {relative}: {name}"
        requirements[name] = match.group("version")
    return requirements


def _project_dependency_names() -> set[str]:
    project = tomllib.loads(_read("pyproject.toml"))["project"]
    names: set[str] = set()
    for requirement in project["dependencies"]:
        match = re.fullmatch(
            r"(?P<name>[A-Za-z0-9][A-Za-z0-9._-]*).*",
            requirement,
        )
        assert match is not None, f'project dependency requires correction: {requirement!r}'
        names.add(_normalized_name(match.group("name")))
    return names


def _project_dependency_versions() -> dict[str, str]:
    project = tomllib.loads(_read("pyproject.toml"))["project"]
    dependencies: dict[str, str] = {}
    for requirement in project["dependencies"]:
        match = re.fullmatch(
            r"(?P<name>[A-Za-z0-9][A-Za-z0-9._-]*)=="
            r"(?P<version>[0-9]+(?:\.[0-9]+)+)",
            requirement,
        )
        assert match is not None, f"project dependency is not exactly pinned: {requirement!r}"
        name = _normalized_name(match.group("name"))
        assert name not in dependencies, f"duplicate project dependency: {name}"
        dependencies[name] = match.group("version")
    return dependencies


def _release_sbom_component_names() -> set[str]:
    document = tomllib.loads(_read("sbom/components.toml"))
    return {
        _normalized_name(component["name"])
        for component in document["component"]
    }


def _development_sbom_components() -> dict[str, dict[str, object]]:
    document = tomllib.loads(_read("sbom/development-components.toml"))
    assert document["schema"] == 1
    assert document["profile"] == "development"
    components = {
        _normalized_name(component["name"]): component
        for component in document["component"]
    }
    assert len(components) == len(document["component"]), (
        "development SBOM component names must be unique"
    )
    return components


def _imported_roots(relative: str) -> set[str]:
    tree = ast.parse(_read(relative), filename=relative)
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.partition(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.partition(".")[0])
    return imported


def _has_main_guard(relative: str) -> bool:
    tree = ast.parse(_read(relative), filename=relative)
    for node in tree.body:
        if not isinstance(node, ast.If):
            continue
        test = node.test
        if (
            isinstance(test, ast.Compare)
            and isinstance(test.left, ast.Name)
            and test.left.id == "__name__"
            and len(test.ops) == 1
            and isinstance(test.ops[0], ast.Eq)
            and len(test.comparators) == 1
            and isinstance(test.comparators[0], ast.Constant)
            and test.comparators[0].value == "__main__"
        ):
            return True
    return False


def test_development_requirements_and_sbom_are_exactly_synchronized() -> None:
    requirements = _pinned_requirements("requirements-dev.txt")
    assert requirements == EXPECTED_DEVELOPMENT_DEPENDENCIES

    components = _development_sbom_components()
    assert set(components) == set(requirements)
    for name, version in requirements.items():
        component = components[name]
        assert component["version"] == version
        assert component["license"] in ALLOWED_QUALITY_TOOL_LICENSES
        assert component["scope"] == "development"
        assert component["profiles"] == DEVELOPMENT_PROFILES

    policy = json.loads(_read("tools/quality_licenses.json"))
    assert policy["quality_tools"] == {
        "deptry": {"license": "MIT", "version": "0.25.1"},
        "pip-audit": {"license": "Apache-2.0", "version": "2.10.1"},
        "pip-licenses": {"license": "MIT", "version": "5.5.5"},
        "pyright": {"license": "MIT", "version": "1.1.414"},
        "vulture": {"license": "MIT", "version": "2.16"},
    }
    assert set(policy["allowed_licenses"]) == {
        "Apache-2.0",
        "BSD",
        "BSD-2-Clause",
        "BSD-3-Clause",
        "ISC",
        "MIT",
        "MPL-2.0",
        "PSF",
    }


def test_every_requirements_profile_and_project_dependency_is_exactly_pinned() -> None:
    requirement_paths = (
        "requirements.txt",
        "requirements-runtime.txt",
        "requirements-preview.txt",
        "requirements-preview-runtime.txt",
        "requirements-dev.txt",
    )
    version_by_name: dict[str, str] = {}
    for relative in requirement_paths:
        for name, version in _pinned_requirements(relative).items():
            previous = version_by_name.setdefault(name, version)
            assert previous == version, (
                f"conflicting pins for {name}: {previous} and {version} in {relative}"
            )

    assert _project_dependency_versions() == _pinned_requirements(
        "requirements-runtime.txt"
    )
    assert _pinned_requirements("requirements-runtime.txt")["pillow"] == "12.3.0"
    assert "pillow" not in _pinned_requirements("requirements-dev.txt")

    components = tomllib.loads(_read("sbom/components.toml"))["component"]
    runtime_components = {
        _normalized_name(component["name"]): component
        for component in components
        if component.get("scope") == "runtime"
    }
    assert runtime_components["pillow"]["version"] == "12.3.0"
    assert runtime_components["pillow"]["license"] == "MIT-CMU"
    assert "certifi" in runtime_components


def test_deptry_covers_all_runtime_profiles_and_development_requirements() -> None:
    configuration = tomllib.loads(_read("pyproject.toml"))["tool"]["deptry"]
    assert configuration["requirements_files"] == [
        "requirements.txt",
        "requirements-runtime.txt",
        "requirements-preview.txt",
        "requirements-preview-runtime.txt",
    ]
    assert configuration["requirements_files_dev"] == ["requirements-dev.txt"]
    assert configuration.get("ignore", []) == []
    assert configuration["per_rule_ignores"] == {"DEP002": ["certifi"]}
    assert "certifi is pinned for the Azure Speech TLS dependency chain" in _read(
        "pyproject.toml"
    )
    assert configuration["package_module_name_map"] == {
        "azure-cognitiveservices-speech": "azure",
        "opencc-python-reimplemented": "opencc",
        "opencv-python": "cv2",
        "websocket-client": "websocket",
    }


def test_development_tools_do_not_enter_runtime_or_release_inventories() -> None:
    development_names = set(EXPECTED_DEVELOPMENT_DEPENDENCIES)
    assert development_names.isdisjoint(
        _pinned_requirements("requirements-runtime.txt")
    )
    assert development_names.isdisjoint(
        _pinned_requirements("requirements-preview-runtime.txt")
    )
    assert development_names.isdisjoint(_project_dependency_names())
    assert development_names.isdisjoint(_release_sbom_component_names())


def test_clean_ci_development_install_covers_hand_model_pytest_gate() -> None:
    test_path = "tests/test_hand_model_provenance.py"
    assert "pytest" in _imported_roots(test_path)
    assert not _has_main_guard(test_path), (
        "the provenance test must continue through run_all.py's pytest path"
    )
    assert _pinned_requirements("requirements-dev.txt")["pytest"] == "9.1.1"

    runner = _read("tests/run_all.py")
    assert '"pytest",\n                "-p",\n                "no:cacheprovider",' in runner
    assert 'str(test),\n                "-q",' in runner
    install = "python -m pip install --only-binary=:all: -r requirements-dev.txt"
    run_suite = "python tests/run_all.py"
    windows_ci = _read(".github/workflows/windows-ci.yml")
    assert install in windows_ci
    assert "python tools/quality_gate.py" in windows_ci
    assert windows_ci.index(install) < windows_ci.index("python tools/quality_gate.py")

    quality_gate = _read("tools/quality_gate.py")
    assert '"full regression suite (aggregate)"' in quality_gate
    assert '(python, "tests/run_all.py", "--aggregate")' in quality_gate

    release_workflow = _read(".github/workflows/release.yml")
    assert install in release_workflow
    assert run_suite in release_workflow
    assert release_workflow.index(install) < release_workflow.index(run_suite)


def main() -> None:
    test_development_requirements_and_sbom_are_exactly_synchronized()
    test_every_requirements_profile_and_project_dependency_is_exactly_pinned()
    test_deptry_covers_all_runtime_profiles_and_development_requirements()
    test_development_tools_do_not_enter_runtime_or_release_inventories()
    test_clean_ci_development_install_covers_hand_model_pytest_gate()
    print("DEVELOPMENT_DEPENDENCY_GOVERNANCE_OK")


if __name__ == "__main__":
    main()
