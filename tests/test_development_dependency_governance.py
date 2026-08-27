from __future__ import annotations

lazy import ast
lazy import re
lazy import tomllib
lazy from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_DEVELOPMENT_DEPENDENCIES = {
    "pillow": "12.3.0",
    "pytest": "9.1.1",
    "ruff": "0.16.0",
}
# Permissive licenses cleared by the project allow-list (MIT family only here).
ALLOWED_DEVELOPMENT_LICENSES = frozenset({"MIT", "MIT-CMU"})
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
            r"(?P<version>[0-9]+(?:\.[0-9]+){2,})",
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
        assert match is not None, f"invalid project dependency: {requirement!r}"
        names.add(_normalized_name(match.group("name")))
    return names


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
        assert component["license"] in ALLOWED_DEVELOPMENT_LICENSES
        assert component["scope"] == "development"
        assert component["profiles"] == DEVELOPMENT_PROFILES


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
    for workflow_path in (
        ".github/workflows/windows-ci.yml",
        ".github/workflows/release.yml",
    ):
        workflow = _read(workflow_path)
        assert install in workflow
        assert run_suite in workflow
        assert workflow.index(install) < workflow.index(run_suite)


def main() -> None:
    test_development_requirements_and_sbom_are_exactly_synchronized()
    test_development_tools_do_not_enter_runtime_or_release_inventories()
    test_clean_ci_development_install_covers_hand_model_pytest_gate()
    print("DEVELOPMENT_DEPENDENCY_GOVERNANCE_OK")


if __name__ == "__main__":
    main()
