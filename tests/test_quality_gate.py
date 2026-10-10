from __future__ import annotations

lazy from pathlib import Path
lazy import json

lazy from tools import quality_gate

EXPECTED_FAILURE_EXIT = 9
EXPECTED_STAGE_COUNT = 16
STATIC_STAGE_COUNT = 15
MISSING_COMMAND_EXIT = 127


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
    assert len(stages) == EXPECTED_STAGE_COUNT
    assert stages[13].action == "cargo-audit"
    assert stages[-2].name == "official Qt runtime"
    assert stages[-2].command[-2:] == ("--pip-report", "qt-install-report.json")
    assert stages[-1].command[-2:] == ("tests/run_all.py", "--aggregate")


def test_missing_cargo_audit_fails_with_pinned_install_command(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    stage = quality_gate.Stage(
        "cargo audit",
        ("cargo", "audit"),
        "cargo-audit",
    )
    monkeypatch.setattr(quality_gate, "_cargo_audit_installed", lambda: False)

    assert quality_gate._run_action(stage, tmp_path) == MISSING_COMMAND_EXIT
    assert (
        "cargo install cargo-audit --version 0.22.2 --locked"
        in capsys.readouterr().err
    )


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


def test_pin_check_accepts_complete_hash_pins_and_rejects_incomplete_hashes(
    tmp_path: Path,
) -> None:
    requirements = tmp_path / "requirements-qt.txt"
    requirements.write_text(
        "example==1.0 \\\n"
        f"    --hash=sha256:{'1' * 64} \\\n"
        f"    --hash=sha256:{'2' * 64}\n",
        encoding="utf-8",
    )
    assert quality_gate._check_pins(tmp_path) == 0

    requirements.write_text("example==1.0 \\\n", encoding="utf-8")
    assert quality_gate._check_pins(tmp_path) == 1


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


def test_pyright_config_binds_current_type_environment(tmp_path: Path) -> None:
    source = tmp_path / "source.json"
    target = tmp_path / "target.json"
    source.write_text(
        json.dumps({"typeCheckingMode": "basic"}),
        encoding="utf-8",
    )

    quality_gate._write_pyright_config(source, target)

    payload = json.loads(target.read_text(encoding="utf-8"))
    environment = Path(quality_gate.sys.prefix).resolve()
    assert payload == {
        "typeCheckingMode": "basic",
        "venvPath": str(environment.parent),
        "venv": environment.name,
    }


def test_pyright_baseline_detects_per_file_increases_and_decreases() -> None:
    increases, decreases = quality_gate._pyright_baseline_changes(
        {"application/a.py": 2, "domain/b.py": 3},
        {"application/a.py": 1, "domain/b.py": 4, "presentation/c.py": 1},
    )

    assert increases == {
        "domain/b.py": (3, 4),
        "presentation/c.py": (0, 1),
    }
    assert decreases == {"application/a.py": (2, 1)}


def test_pyright_baseline_round_trip_and_rejects_inconsistent_total(
    tmp_path: Path,
) -> None:
    baseline = tmp_path / "pyright_baseline.json"
    quality_gate._write_pyright_baseline(
        baseline,
        {"domain/b.py": 2, "application/a.py": 1},
    )

    assert quality_gate._load_pyright_baseline(baseline) == {
        "application/a.py": 1,
        "domain/b.py": 2,
    }
    payload = json.loads(baseline.read_text(encoding="utf-8"))
    payload["total_warnings"] = 4
    baseline.write_text(json.dumps(payload), encoding="utf-8")

    try:
        quality_gate._load_pyright_baseline(baseline)
    except ValueError as error:
        assert "total_warnings" in str(error)
    else:
        raise AssertionError("An inconsistent Pyright baseline must be rejected.")


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
