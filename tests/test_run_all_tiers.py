from __future__ import annotations

lazy from contextlib import redirect_stdout
lazy from io import StringIO
lazy from pathlib import Path
lazy import sys
lazy from tempfile import TemporaryDirectory
lazy from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))

lazy import run_all


def _repository_tests() -> tuple[Path, ...]:
    return tuple(sorted(run_all.TESTS_DIR.glob("test_*.py")))


def test_arguments_keep_gate_as_the_default_and_accept_both_tier_spellings() -> None:
    assert run_all._arguments(()).tier == run_all.DEFAULT_TIER
    assert run_all._arguments(()).aggregate is False
    assert run_all._arguments(("--aggregate",)).aggregate is True
    assert run_all._arguments(("--list",)).list is True
    assert run_all._arguments(("fast", "--changed-from", "main")).tier == (
        run_all.FAST_TIER
    )
    assert run_all._arguments(("--tier", "nightly")).tier == (
        run_all.NIGHTLY_TIER
    )


def test_fast_maps_a_changed_source_module_and_keeps_contract_tests() -> None:
    all_tests = _repository_tests()
    with patch.object(
        run_all,
        "_git_changed_files",
        return_value=(("domain/affective_state.py",), None),
    ):
        selected, notice, changed = run_all._tests_for_tier(
            all_tests,
            tier=run_all.FAST_TIER,
            changed_from=None,
        )

    selected_names = {test.name for test in selected}
    assert notice is None
    assert changed == ("domain/affective_state.py",)
    assert "test_affective_state.py" in selected_names
    assert "test_action_planner_contract.py" in selected_names
    assert len(selected) < len(all_tests)


def test_fast_unmapped_changed_file_falls_back_to_the_complete_suite() -> None:
    all_tests = _repository_tests()
    with patch.object(
        run_all,
        "_git_changed_files",
        return_value=(("unmapped/changed-file.txt",), None),
    ):
        selected, notice, changed = run_all._tests_for_tier(
            all_tests,
            tier=run_all.FAST_TIER,
            changed_from=None,
        )

    assert selected == all_tests
    assert changed == ("unmapped/changed-file.txt",)
    assert notice is not None
    assert "unmapped changed paths" in notice


def test_fast_runner_announces_the_safe_fallback_and_runs_every_module() -> None:
    all_tests = _repository_tests()
    with (
        patch.object(
            run_all,
            "_git_changed_files",
            return_value=(("unmapped/changed-file.txt",), None),
        ),
        patch.object(run_all, "_run_test_process", return_value=0),
        redirect_stdout(stdout := StringIO()),
    ):
        assert run_all.main(("fast",)) == 0

    output = stdout.getvalue()
    assert "FAST_FALLBACK_TO_GATE: unmapped changed paths" in output
    assert f"[1/{len(all_tests)}]" in output
    assert f"[{len(all_tests)}/{len(all_tests)}]" in output
    assert f"ALL_{len(all_tests)}_TESTS_OK" in output


def test_default_runner_keeps_gate_output_without_a_tier_banner() -> None:
    all_tests = _repository_tests()
    with (
        patch.object(run_all, "_run_test_process", return_value=0),
        redirect_stdout(stdout := StringIO()),
    ):
        assert run_all.main(()) == 0

    output = stdout.getvalue()
    assert "FAST_" not in output
    assert "NIGHTLY_" not in output
    assert f"ALL_{len(all_tests)}_TESTS_OK" in output


def test_gate_selection_remains_complete_and_nightly_is_a_subset() -> None:
    all_tests = _repository_tests()
    gate, gate_notice, _ = run_all._tests_for_tier(
        all_tests,
        tier=run_all.DEFAULT_TIER,
        changed_from=None,
    )
    nightly, nightly_notice, _ = run_all._tests_for_tier(
        all_tests,
        tier=run_all.NIGHTLY_TIER,
        changed_from=None,
    )

    nightly_names = {test.name for test in nightly}
    assert gate == all_tests
    assert gate_notice is None
    assert nightly_notice is None
    assert nightly_names < {test.name for test in all_tests}
    assert "test_preview_packaging.py" in nightly_names
    assert "test_cross_platform_core.py" in nightly_names


def test_changed_from_uses_the_git_reference_provider() -> None:
    all_tests = _repository_tests()
    with patch.object(
        run_all,
        "_git_changed_files",
        return_value=(("application/appearance_renderer.py",), None),
    ) as changed_files:
        run_all._tests_for_tier(
            all_tests,
            tier=run_all.FAST_TIER,
            changed_from="origin/main",
        )

    changed_files.assert_called_once_with("origin/main")


def test_changed_from_can_fall_back_to_a_remote_branch_with_a_slash() -> None:
    assert run_all._git_reference_candidates("feature/test-tier") == (
        "feature/test-tier",
        "origin/feature/test-tier",
    )
    assert run_all._git_reference_candidates("origin/feature/test-tier") == (
        "origin/feature/test-tier",
    )


def test_duration_balanced_shards_partition_the_real_test_directory() -> None:
    all_tests = _repository_tests()
    durations, default_seconds = run_all._load_test_durations()
    shards = run_all._assign_shards(
        all_tests,
        shard_count=8,
        durations=durations,
        default_seconds=default_seconds,
    )

    names_by_shard = tuple({test.name for test in shard} for shard in shards)
    assert set().union(*names_by_shard) == {test.name for test in all_tests}
    for left_index, left in enumerate(names_by_shard):
        for right in names_by_shard[left_index + 1 :]:
            assert left.isdisjoint(right)

    loads = tuple(
        sum(
            run_all._estimated_seconds(test, durations, default_seconds)
            for test in shard
        )
        for shard in shards
    )
    average = sum(loads) / len(loads)
    assert max(loads) - min(loads) <= average * 0.25


def test_list_mode_reports_shard_without_starting_test_processes() -> None:
    with (
        patch.object(run_all, "_run_test_process") as run_process,
        redirect_stdout(stdout := StringIO()),
    ):
        assert run_all.main(("--shard-count", "3", "--shard-index", "1", "--list")) == 0

    output = stdout.getvalue()
    assert "SHARD_SELECTION index=1 count=3" in output
    assert "SHARD_TEST=test_" in output
    run_process.assert_not_called()


def test_duration_writer_round_trips_measured_modules() -> None:
    temporary_root = run_all.TESTS_DIR.parent / ".test-tmp"
    temporary_root.mkdir(exist_ok=True)
    with TemporaryDirectory(
        prefix="mohan-duration-test-",
        dir=temporary_root,
    ) as temporary:
        duration_path = Path(temporary) / "durations.json"
        run_all._write_test_durations(
            duration_path,
            {"test_slow.py": 4.0, "test_fast.py": 2.0},
        )
        durations, default_seconds = run_all._load_test_durations(duration_path)

    assert durations == {"test_fast.py": 2.0, "test_slow.py": 4.0}
    assert default_seconds == (2.0 + 4.0) / 2


if __name__ == "__main__":
    test_arguments_keep_gate_as_the_default_and_accept_both_tier_spellings()
    test_fast_maps_a_changed_source_module_and_keeps_contract_tests()
    test_fast_unmapped_changed_file_falls_back_to_the_complete_suite()
    test_fast_runner_announces_the_safe_fallback_and_runs_every_module()
    test_default_runner_keeps_gate_output_without_a_tier_banner()
    test_gate_selection_remains_complete_and_nightly_is_a_subset()
    test_changed_from_uses_the_git_reference_provider()
    test_changed_from_can_fall_back_to_a_remote_branch_with_a_slash()
    test_duration_balanced_shards_partition_the_real_test_directory()
    test_list_mode_reports_shard_without_starting_test_processes()
    print("RUN_ALL_TIERS_OK")
