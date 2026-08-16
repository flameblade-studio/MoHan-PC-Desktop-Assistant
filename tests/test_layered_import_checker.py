from __future__ import annotations

lazy from pathlib import Path

lazy from tools.check_layered_imports import (
    RootModuleOwnership,
    inspect_layered_imports,
)

LAYERS = ("presentation", "application", "domain", "integrations", "infrastructure")


def create_packages(root: Path) -> None:
    for layer in LAYERS:
        package = root / layer
        package.mkdir()
        (package / "__init__.py").write_text("", encoding="utf-8")


def write_module(root: Path, name: str, source: str) -> None:
    path = root.joinpath(*name.split(".")).with_suffix(".py")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")


def issue_codes(root: Path) -> list[str]:
    return [
        issue.code
        for issue in inspect_layered_imports(root, root_ownership=()).issues
    ]


def test_empty_layer_packages_pass(tmp_path: Path) -> None:
    create_packages(tmp_path)
    report = inspect_layered_imports(tmp_path, root_ownership=())
    assert report.passed
    assert report.modules == LAYERS
    assert report.mapped_root_modules == ()
    assert report.format() == (
        "Layered imports passed (package_modules=5 mapped_root_modules=0 "
        "legacy_root_modules=0)."
    )


def test_legal_regular_and_lazy_imports_pass(tmp_path: Path) -> None:
    create_packages(tmp_path)
    write_module(tmp_path, "domain.model", "VALUE = 1\n")
    write_module(tmp_path, "application.use_case", "lazy from domain.model import VALUE\n")
    write_module(tmp_path, "presentation.window", "import application.use_case\n")
    write_module(tmp_path, "integrations.cloud", "lazy import application.use_case\n")
    write_module(tmp_path, "infrastructure.store", "from domain import model\n")
    assert inspect_layered_imports(tmp_path, root_ownership=()).passed


def test_reverse_dependencies_cover_import_forms(tmp_path: Path) -> None:
    create_packages(tmp_path)
    write_module(tmp_path, "presentation.bad", "lazy import infrastructure.store\n")
    write_module(tmp_path, "application.bad", "from presentation import window\n")
    write_module(tmp_path, "domain.bad", "lazy from integrations.cloud import Client\n")
    report = inspect_layered_imports(tmp_path, root_ownership=())
    reverse = [issue for issue in report.issues if issue.code == "reverse_dependency"]
    assert [(issue.module, issue.line) for issue in reverse] == [
        ("application.bad", 1),
        ("domain.bad", 1),
        ("presentation.bad", 1),
    ]
    assert all("must not import" in issue.message for issue in reverse)


def test_composition_exceptions_are_exact_targets(tmp_path: Path) -> None:
    create_packages(tmp_path)
    write_module(
        tmp_path,
        "infrastructure.flagship_windows_toolbox",
        "VALUE = 1\n",
    )
    write_module(tmp_path, "infrastructure.forbidden", "VALUE = 2\n")
    write_module(
        tmp_path,
        "presentation.flagship_core",
        "from infrastructure.flagship_windows_toolbox import VALUE\n",
    )
    assert inspect_layered_imports(tmp_path, root_ownership=()).passed
    write_module(
        tmp_path,
        "presentation.flagship_core",
        "from infrastructure.forbidden import VALUE\n",
    )
    reverse = [
        issue
        for issue in inspect_layered_imports(
            tmp_path,
            root_ownership=(),
        ).issues
        if issue.code == "reverse_dependency"
    ]
    assert [(issue.module, issue.line) for issue in reverse] == [
        ("presentation.flagship_core", 1),
    ]


def test_relative_import_cycle_is_reported_once(tmp_path: Path) -> None:
    create_packages(tmp_path)
    write_module(tmp_path, "application.alpha", "lazy from . import beta\n")
    write_module(tmp_path, "application.beta", "from .alpha import VALUE\nVALUE = 1\n")
    cycles = [
        issue
        for issue in inspect_layered_imports(tmp_path, root_ownership=()).issues
        if issue.code == "import_cycle"
    ]
    assert len(cycles) == 1
    assert cycles[0].message == (
        "application.alpha -> application.beta -> application.alpha"
    )


def test_package_relative_import_and_self_cycle_are_checked(tmp_path: Path) -> None:
    create_packages(tmp_path)
    (tmp_path / "application" / "__init__.py").write_text(
        "lazy from . import service\n",
        encoding="utf-8",
    )
    write_module(tmp_path, "application.service", "import application.service\n")
    cycles = [
        issue.message
        for issue in inspect_layered_imports(tmp_path, root_ownership=()).issues
        if issue.code == "import_cycle"
    ]
    assert cycles == ["application.service -> application.service"]


def test_output_is_deterministic(tmp_path: Path) -> None:
    create_packages(tmp_path)
    write_module(tmp_path, "domain.zed", "import presentation.window\n")
    write_module(tmp_path, "domain.alpha", "lazy import infrastructure.store\n")
    first = inspect_layered_imports(tmp_path, root_ownership=())
    second = inspect_layered_imports(tmp_path, root_ownership=())
    assert first.issues == second.issues
    assert first.format() == second.format()
    assert first.format().splitlines()[1:] == sorted(first.format().splitlines()[1:])


def test_unmapped_root_module_fails_closed(tmp_path: Path) -> None:
    create_packages(tmp_path)
    write_module(tmp_path, "legacy", "VALUE = 1\n")

    report = inspect_layered_imports(tmp_path, root_ownership=())

    assert [issue.code for issue in report.issues] == ["root_module_unmapped"]


def test_root_mapping_requires_honest_owner_and_location(tmp_path: Path) -> None:
    create_packages(tmp_path)
    write_module(tmp_path, "legacy", "VALUE = 1\n")
    ownership = (
        RootModuleOwnership("legacy", "domain", "policy", "compatibility-root"),
    )

    assert inspect_layered_imports(
        tmp_path,
        root_ownership=ownership,
    ).passed


def test_direct_and_transitive_reverse_app_imports_fail(tmp_path: Path) -> None:
    create_packages(tmp_path)
    write_module(tmp_path, "app", "VALUE = 1\n")
    write_module(tmp_path, "direct", "lazy import app\n")
    write_module(tmp_path, "transitive", "lazy import direct\n")
    ownership = tuple(
        RootModuleOwnership(
            name,
            "application",
            "test",
            "composition-root" if name == "app" else "compatibility-root",
        )
        for name in ("app", "direct", "transitive")
    )

    report = inspect_layered_imports(tmp_path, root_ownership=ownership)

    assert [(issue.code, issue.module) for issue in report.issues] == [
        ("reverse_import_app", "direct"),
        ("transitive_reverse_import_app", "transitive"),
    ]
