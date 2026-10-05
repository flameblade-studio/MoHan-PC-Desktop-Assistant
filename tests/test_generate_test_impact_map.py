from __future__ import annotations

lazy import ast
lazy import json
lazy from pathlib import Path

lazy import run_all
lazy from tools import generate_test_impact_map as generator


def _write(root: Path, relative: str, content: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_derives_direct_lazy_imports_and_literal_paths(tmp_path: Path) -> None:
    paths = (
        "application/planner.py",
        "assets/policy.json",
        "tests/test_planner_contract.py",
        "tools/check_policy.py",
    )
    _write(tmp_path, "application/planner.py", "VALUE = 1\n")
    _write(tmp_path, "tools/check_policy.py", "VALUE = 2\n")
    _write(tmp_path, "assets/policy.json", "{}\n")
    _write(
        tmp_path,
        "tests/test_planner_contract.py",
        "from __future__ import annotations\n"
        "lazy from application.planner import VALUE\n"
        "lazy import tools.check_policy\n"
        "lazy from pathlib import Path\n"
        "POLICY = Path('assets') / 'policy.json'\n",
    )

    associations = generator.derive_test_associations(tmp_path, paths)

    expected = ("test_planner_contract.py",)
    assert associations["application/planner.py"] == expected
    assert associations["tools/check_policy.py"] == expected
    assert associations["assets/policy.json"] == expected


def test_derives_dependencies_through_imported_test_helpers(tmp_path: Path) -> None:
    paths = (
        "domain/state.py",
        "tests/planner_support.py",
        "tests/test_planner.py",
    )
    _write(tmp_path, "domain/state.py", "VALUE = 1\n")
    _write(
        tmp_path,
        "tests/planner_support.py",
        "lazy from domain.state import VALUE\n",
    )
    _write(
        tmp_path,
        "tests/test_planner.py",
        "lazy from tests.planner_support import VALUE\n",
    )

    associations = generator.derive_test_associations(tmp_path, paths)

    assert associations["tests/planner_support.py"] == ("test_planner.py",)
    assert associations["domain/state.py"] == ("test_planner.py",)


def test_pytest_conftest_changes_select_every_test(tmp_path: Path) -> None:
    paths = (
        "tests/conftest.py",
        "tests/test_first.py",
        "tests/test_second.py",
    )
    for path in paths:
        _write(tmp_path, path, "VALUE = 1\n")

    associations = generator.derive_test_associations(tmp_path, paths)

    assert associations["tests/conftest.py"] == (
        "test_first.py",
        "test_second.py",
    )


def test_regeneration_replaces_only_generated_rules(tmp_path: Path) -> None:
    paths = ("domain/state.py", "tests/test_state.py")
    _write(tmp_path, "domain/state.py", "VALUE = 1\n")
    _write(
        tmp_path,
        "tests/test_state.py",
        "lazy from domain.state import VALUE\n",
    )
    manual = {"paths": ["docs/**"], "tests": ["test_state.py"]}
    stale = {
        "paths": ["stale.py"],
        "tests": ["test_state.py"],
        "origin": generator.DERIVED_ORIGIN,
    }
    document: dict[str, object] = {
        "schema": "mohan.test-impact-map.v1",
        "rules": [manual, stale],
    }

    first = generator.regenerated_document(tmp_path, document, paths)
    second = generator.regenerated_document(tmp_path, first, paths)

    assert first == second
    rules = first["rules"]
    assert isinstance(rules, list)
    assert rules[0] == manual
    assert not any(
        isinstance(rule, dict) and "stale.py" in rule.get("paths", ())
        for rule in rules
    )
    assert any(
        isinstance(rule, dict)
        and rule.get("paths") == ["domain/state.py"]
        and rule.get("tests") == ["test_state.py"]
        for rule in rules
    )


def test_rendered_document_is_utf8_stable() -> None:
    document: dict[str, object] = {
        "schema": "mohan.test-impact-map.v1",
        "note": "繁體中文／简体中文／English／日本語",
        "rules": [],
    }

    rendered = generator.render_document(document)

    assert "繁體中文" in rendered
    assert json.loads(rendered) == document
    assert rendered.endswith("\n")


def test_generated_exact_paths_escape_fnmatch_metacharacters() -> None:
    rules = generator.derived_rules(
        {"assets/fonts/Cinzel/Cinzel[wght].ttf": ("test_font.py",)}
    )

    assert generator.mapped_tests_for_path(
        "assets/fonts/Cinzel/Cinzel[wght].ttf",
        rules,
        frozenset({"test_font.py"}),
    ) == ("test_font.py",)


def test_tracked_product_and_tool_sources_are_mapped() -> None:
    paths = generator.tracked_paths()
    test_names = frozenset(path.name for path in run_all.TESTS_DIR.glob("test_*.py"))
    impact_map, error = run_all._load_impact_map(test_names)

    assert error is None
    assert impact_map is not None
    exceptions = generator.SOURCE_COVERAGE_EXCEPTIONS
    assert set(exceptions) <= set(generator.product_and_tool_sources(paths))
    assert all(reason.strip() for reason in exceptions.values())
    uncovered = {
        path
        for path in generator.product_and_tool_sources(paths)
        if path not in exceptions
        and not run_all._mapped_tests_for_path(
            path,
            impact_map["rules"],
            test_names,
        )[1]
    }

    assert not uncovered, (
        "Tracked product/tool sources require an impact-map rule; "
        f"document justified exceptions in exceptions: {sorted(uncovered)}"
    )


def test_repository_impact_map_matches_deterministic_derivation() -> None:
    paths = generator.tracked_paths()
    document = json.loads(generator.DEFAULT_IMPACT_MAP.read_text(encoding="utf-8"))
    assert isinstance(document, dict)

    expected = generator.regenerated_document(generator.ROOT, document, paths)

    assert generator.render_document(expected) == generator.DEFAULT_IMPACT_MAP.read_text(
        encoding="utf-8"
    )


def test_every_derived_association_is_present_in_the_runtime_map() -> None:
    paths = generator.tracked_paths()
    test_names = frozenset(path.name for path in run_all.TESTS_DIR.glob("test_*.py"))
    impact_map, error = run_all._load_impact_map(test_names)
    assert error is None
    assert impact_map is not None

    associations = generator.derive_test_associations(generator.ROOT, paths)
    missing: dict[str, list[str]] = {}
    for path, expected_tests in associations.items():
        mapped = set(
            run_all._mapped_tests_for_path(
                path,
                impact_map["rules"],
                test_names,
            )[1]
        )
        omitted = sorted(set(expected_tests) - mapped)
        if omitted:
            missing[path] = omitted

    assert not missing


def test_generator_source_is_valid_python315() -> None:
    source = Path(generator.__file__).read_text(encoding="utf-8")
    ast.parse(source)
