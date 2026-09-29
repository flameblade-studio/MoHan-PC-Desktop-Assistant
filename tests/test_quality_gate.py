from __future__ import annotations

lazy from pathlib import Path

lazy from tools import quality_gate

EXPECTED_FAILURE_EXIT = 9
STATIC_STAGE_COUNT = 14


def test_stage_order_ends_with_aggregate_regression_suite() -> None:
    stages = quality_gate._stages()
    names = tuple(stage.name for stage in stages)

    assert names[:5] == (
        "Python 3.15 runtime",
        "compileall",
        "ruff",
        "requirements exact pins",
        "pyright (lazy-import-normalized source copy)",
    )
    assert stages[-1].command[-2:] == ("tests/run_all.py", "--aggregate")


def test_stage_selection_splits_static_work_from_sharded_tests() -> None:
    static = quality_gate._selected_stages(
        "static",
        shard_index=0,
        shard_count=1,
    )
    tests = quality_gate._selected_stages(
        "tests",
        shard_index=3,
        shard_count=8,
    )

    assert len(static) == STATIC_STAGE_COUNT
    assert all("tests/run_all.py" not in stage.command for stage in static)
    assert len(tests) == 1
    assert tests[0].command[-4:] == (
        "--shard-index",
        "3",
        "--shard-count",
        "8",
    )


def test_pin_check_rejects_unpinned_requirement(tmp_path: Path) -> None:
    (tmp_path / "requirements.txt").write_text("example>=1.0\n", encoding="utf-8")

    assert quality_gate._check_pins(tmp_path) == 1

    (tmp_path / "requirements.txt").write_text("example==1.0\n", encoding="utf-8")
    assert quality_gate._check_pins(tmp_path) == 0


def test_pyright_copy_normalizes_only_lazy_import_syntax(tmp_path: Path) -> None:
    source = tmp_path / "domain" / "sample.py"
    source.parent.mkdir()
    source.write_text(
        "lazy import json\nlazy from pathlib import Path\nvalue = 'lazy import kept'\n",
        encoding="utf-8",
    )
    temporary = quality_gate._create_temporary_directory(tmp_path, "type-")

    copied, directories = quality_gate._copy_python_sources(
        tmp_path,
        temporary,
        normalize_lazy_imports=True,
    )
    try:
        normalized = (temporary / "domain" / "sample.py").read_text(encoding="utf-8")
        assert normalized == (
            "import json\nfrom pathlib import Path\nvalue = 'lazy import kept'\n"
        )
    finally:
        quality_gate._remove_temporary_tree(temporary, copied, directories)


def test_gate_stops_after_first_failed_stage(
    tmp_path: Path,
    monkeypatch,
) -> None:
    stages = (
        quality_gate.Stage("first", ("first",)),
        quality_gate.Stage("failure", ("failure",)),
        quality_gate.Stage("not-run", ("not-run",)),
    )
    observed: list[str] = []

    monkeypatch.setattr(quality_gate, "_stages", lambda: stages)

    def run(stage: quality_gate.Stage, _root: Path) -> int:
        observed.append(stage.name)
        return EXPECTED_FAILURE_EXIT if stage.name == "failure" else 0

    monkeypatch.setattr(quality_gate, "_run_action", run)

    assert quality_gate.run_gate(tmp_path) == EXPECTED_FAILURE_EXIT
    assert observed == ["first", "failure"]
