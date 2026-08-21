from __future__ import annotations

lazy import ast
lazy import os
lazy import sys
lazy from contextlib import redirect_stderr, redirect_stdout
lazy from io import StringIO
lazy from pathlib import Path
lazy from tempfile import TemporaryDirectory
lazy from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))

lazy import run_all

ISOLATED_PATH_VARIABLES = (
    "LOCALAPPDATA",
    "APPDATA",
    "TEMP",
    "TMP",
    "PYTHONPYCACHEPREFIX",
)

EXPECTED_EXIT_CODE = 23


def _test_file(root: Path, name: str, source: str = "") -> None:
    (root / name).write_text(source, encoding="utf-8")


def _command_test_name(command: list[str]) -> str:
    test_argument = next(
        argument for argument in command if ".py" in argument
    )
    return Path(test_argument.partition("::")[0]).name


def test_each_child_receives_an_independent_sanitized_environment() -> None:
    calls: list[dict[str, object]] = []

    def capture_run(command, *, cwd, environment):
        calls.append({"command": command, "cwd": cwd, "env": environment})
        for variable in ISOLATED_PATH_VARIABLES:
            assert Path(environment[variable]).is_dir()
        return 0

    with TemporaryDirectory() as directory:
        tests_dir = Path(directory) / "tests"
        tests_dir.mkdir()
        _test_file(tests_dir, "test_zulu.py")
        _test_file(
            tests_dir,
            "test_alpha.py",
            'if __name__ == "__main__":\n    raise SystemExit(0)\n',
        )
        _test_file(tests_dir, "helper.py")
        inherited = {
            "MOHAN_DATA_DIR": str(Path(directory) / "real-mohan-data"),
            "OPENAI_API_KEY": "real-key-must-not-reach-tests",
            "WORDPRESS_APP_PASSWORD": "real-password-must-not-reach-tests",
            "WORDPRESS_BASE_URL": "https://private.invalid",
            "WORDPRESS_DOWNLOAD_PAGE_ID": "private-page-id",
            "WORDPRESS_USERNAME": "private-user",
            "AZURE_CLIENT_SECRET": "private-azure-secret",
            "GH_TOKEN": "private-github-token",
            "PYTHONPATH": "untrusted-inherited-path",
            "PYTEST_ADDOPTS": "--collect-only",
            "RUN_ALL_PRESERVE_ME": "preserved",
        }
        with (
            patch.object(run_all, "TESTS_DIR", tests_dir),
            patch.object(run_all, "_run_test_process", side_effect=capture_run),
            patch.dict(os.environ, inherited, clear=False),
        ):
            assert run_all.main() == 0

    assert [_command_test_name(call["command"]) for call in calls] == [
        "test_alpha.py",
        "test_zulu.py",
    ]
    assert calls[0]["command"] == [
        sys.executable,
        str(tests_dir / "test_alpha.py"),
    ]
    assert calls[1]["command"] == [
        sys.executable,
        "-m",
        "pytest",
        "-p",
        "no:cacheprovider",
        str(tests_dir / "test_zulu.py"),
        "-q",
    ]
    environments = [call["env"] for call in calls]
    for environment in environments:
        assert "MOHAN_DATA_DIR" not in environment
        assert all(
            environment[name] == "" for name in run_all.SENSITIVE_ENVIRONMENT_VARIABLES
        )
        assert "AZURE_CLIENT_SECRET" not in environment
        assert "GH_TOKEN" not in environment
        assert environment["PYTHONPATH"] == str(tests_dir.parent)
        assert "PYTEST_ADDOPTS" not in environment
        assert environment["RUN_ALL_PRESERVE_ME"] == "preserved"
    for variable in ISOLATED_PATH_VARIABLES:
        paths = [Path(environment[variable]) for environment in environments]
        assert len(set(paths)) == len(paths)
        assert all(not path.exists() for path in paths)
    assert all(call["cwd"] == tests_dir.parent for call in calls)


def test_first_failure_stops_the_sorted_run_and_preserves_exit_code() -> None:
    called: list[str] = []
    # test_alpha passes (0); test_bravo fails twice in a row (23, 23) so the
    # single retry cannot rescue it and the suite stops with its exit code.
    return_codes = iter((0, 23, 23))

    def fail_second(command, **_kwargs):
        called.append(_command_test_name(command))
        return next(return_codes)

    with TemporaryDirectory() as directory:
        tests_dir = Path(directory) / "tests"
        tests_dir.mkdir()
        _test_file(tests_dir, "test_charlie.py")
        _test_file(tests_dir, "test_alpha.py")
        _test_file(tests_dir, "test_bravo.py")
        with (
            patch.object(run_all, "TESTS_DIR", tests_dir),
            patch.object(run_all, "_run_test_process", side_effect=fail_second),
            redirect_stdout(stdout := StringIO()),
            redirect_stderr(stderr := StringIO()),
        ):
            assert run_all.main() == EXPECTED_EXIT_CODE

    assert called == ["test_alpha.py", "test_bravo.py", "test_bravo.py"]
    assert stdout.getvalue().splitlines() == [
        "[1/3] test_alpha.py",
        "[2/3] test_bravo.py",
    ]
    assert stderr.getvalue().splitlines() == [
        "RETRY: test_bravo.py (attempt 1 failed, retrying in a fresh environment)",
        "FAILED: test_bravo.py (exit 23)",
    ]


def test_malformed_test_source_fails_closed_without_starting_a_child() -> None:
    with TemporaryDirectory() as directory:
        tests_dir = Path(directory) / "tests"
        tests_dir.mkdir()
        _test_file(tests_dir, "test_broken.py", "def broken(:\n")
        with (
            patch.object(run_all, "TESTS_DIR", tests_dir),
            patch.object(run_all, "_run_test_process") as child_run,
            redirect_stdout(stdout := StringIO()),
            redirect_stderr(stderr := StringIO()),
        ):
            assert run_all.main() == run_all.MALFORMED_TEST_EXIT_CODE

    child_run.assert_not_called()
    assert stdout.getvalue().splitlines() == ["[1/1] test_broken.py"]
    assert stderr.getvalue().splitlines() == ["FAILED: test_broken.py (exit 2)"]


def test_mixed_module_uses_one_process_when_main_covers_pytest_nodes() -> None:
    with TemporaryDirectory() as directory:
        test = Path(directory) / "test_mixed.py"
        _test_file(
            test.parent,
            test.name,
            "def test_collected():\n"
            "    assert True\n\n"
            "if __name__ == '__main__':\n"
            "    test_collected()\n"
            "    print('partial manual runner')\n",
        )

        assert run_all._test_commands(test) == ([sys.executable, str(test)],)


def test_mixed_module_only_collects_nodes_missing_from_main() -> None:
    with TemporaryDirectory() as directory:
        test = Path(directory) / "test_parametrized.py"
        _test_file(
            test.parent,
            test.name,
            "import pytest\n\n"
            "@pytest.mark.parametrize('value', (1, 2))\n"
            "def test_collected(value):\n"
            "    assert value\n\n"
            "if __name__ == '__main__':\n"
            "    print('manual contracts')\n",
        )

        assert run_all._test_commands(test) == (
            [sys.executable, str(test)],
            [
                sys.executable,
                "-m",
                "pytest",
                "-p",
                "no:cacheprovider",
                f"{test}::test_collected",
                "-q",
            ],
        )


def test_mixed_module_combines_missing_pytest_nodes_in_one_process() -> None:
    with TemporaryDirectory() as directory:
        test = Path(directory) / "test_partial.py"
        _test_file(
            test.parent,
            test.name,
            "def test_covered():\n"
            "    assert True\n\n"
            "def test_first_missing():\n"
            "    assert True\n\n"
            "class TestSecondMissing:\n"
            "    def test_value(self):\n"
            "        assert True\n\n"
            "if __name__ == '__main__':\n"
            "    test_covered()\n",
        )

        assert run_all._test_commands(test) == (
            [sys.executable, str(test)],
            [
                sys.executable,
                "-m",
                "pytest",
                "-p",
                "no:cacheprovider",
                f"{test}::test_first_missing",
                f"{test}::TestSecondMissing",
                "-q",
            ],
        )


def test_unittest_main_does_not_duplicate_wrapped_pytest_functions() -> None:
    with TemporaryDirectory() as directory:
        test = Path(directory) / "test_unittest_bridge.py"
        _test_file(
            test.parent,
            test.name,
            "import unittest\n\n"
            "def test_contract():\n"
            "    assert True\n\n"
            "class TestContract(unittest.TestCase):\n"
            "    def test_contract(self):\n"
            "        test_contract()\n\n"
            "if __name__ == '__main__':\n"
            "    unittest.main()\n",
        )

        assert run_all._test_commands(test) == ([sys.executable, str(test)],)


def test_pure_pytest_delegate_to_main_runner_is_not_duplicated() -> None:
    with TemporaryDirectory() as directory:
        test = Path(directory) / "test_delegate.py"
        _test_file(
            test.parent,
            test.name,
            "def run():\n"
            "    assert True\n\n"
            "def test_contract():\n"
            "    run()\n\n"
            "if __name__ == '__main__':\n"
            "    run()\n",
        )

        assert run_all._test_commands(test) == ([sys.executable, str(test)],)


def test_bare_function_reference_does_not_count_as_execution() -> None:
    with TemporaryDirectory() as directory:
        test = Path(directory) / "test_reference.py"
        _test_file(
            test.parent,
            test.name,
            "def test_contract():\n"
            "    assert True\n\n"
            "def run():\n"
            "    ignored = test_contract\n"
            "    assert ignored is test_contract\n\n"
            "if __name__ == '__main__':\n"
            "    run()\n",
        )

        commands = run_all._test_commands(test)
        assert commands[1][-2] == f"{test}::test_contract"


def test_explicit_function_collection_loop_counts_as_execution() -> None:
    with TemporaryDirectory() as directory:
        test = Path(directory) / "test_collection.py"
        _test_file(
            test.parent,
            test.name,
            "def test_first():\n"
            "    assert True\n\n"
            "def test_second():\n"
            "    assert True\n\n"
            "def run():\n"
            "    checks = (test_first, test_second)\n"
            "    for check in checks:\n"
            "        check()\n\n"
            "if __name__ == '__main__':\n"
            "    run()\n",
        )

        assert run_all._test_commands(test) == ([sys.executable, str(test)],)


def test_parametrized_delegate_is_not_assumed_to_be_covered() -> None:
    with TemporaryDirectory() as directory:
        test = Path(directory) / "test_delegate_parameters.py"
        _test_file(
            test.parent,
            test.name,
            "def run():\n"
            "    assert True\n\n"
            "def test_contract(tmp_path):\n"
            "    run()\n\n"
            "if __name__ == '__main__':\n"
            "    run()\n",
        )

        commands = run_all._test_commands(test)
        assert commands[1][-2] == f"{test}::test_contract"


def test_pure_main_script_still_runs_as_a_script() -> None:
    with TemporaryDirectory() as directory:
        test = Path(directory) / "test_script.py"
        _test_file(
            test.parent,
            test.name,
            "def main():\n"
            "    return 0\n\n"
            "if __name__ == '__main__':\n"
            "    raise SystemExit(main())\n",
        )

        assert run_all._test_commands(test) == ([sys.executable, str(test)],)


def test_shards_are_complete_disjoint_deterministic_and_balanced() -> None:
    tests = tuple(Path(f"test_{index:02d}.py") for index in range(11))
    first_pass = tuple(
        run_all._select_shard(
            tests,
            shard_index=index,
            shard_count=4,
        )
        for index in range(4)
    )
    second_pass = tuple(
        run_all._select_shard(
            tests,
            shard_index=index,
            shard_count=4,
        )
        for index in range(4)
    )

    assert first_pass == second_pass
    assert set().union(*(set(shard) for shard in first_pass)) == set(tests)
    assert sum(len(shard) for shard in first_pass) == len(tests)
    assert max(map(len, first_pass)) - min(map(len, first_pass)) <= 1


def test_main_runs_only_the_requested_shard() -> None:
    called: list[str] = []

    def capture_run(command, **_kwargs):
        called.append(_command_test_name(command))
        return 0

    with TemporaryDirectory() as directory:
        tests_dir = Path(directory) / "tests"
        tests_dir.mkdir()
        for name in (
            "test_alpha.py",
            "test_bravo.py",
            "test_charlie.py",
            "test_delta.py",
        ):
            _test_file(tests_dir, name)
        with (
            patch.object(run_all, "TESTS_DIR", tests_dir),
            patch.object(run_all, "_run_test_process", side_effect=capture_run),
        ):
            assert run_all.main(
                ("--shard-count", "2", "--shard-index", "1")
            ) == 0

    assert called == ["test_bravo.py", "test_delta.py"]


def test_timeout_fails_closed_with_stable_exit_code() -> None:
    with TemporaryDirectory() as directory:
        tests_dir = Path(directory) / "tests"
        tests_dir.mkdir()
        _test_file(tests_dir, "test_slow.py")
        with (
            patch.object(run_all, "TESTS_DIR", tests_dir),
            patch.object(
                run_all,
                "_run_test_process",
                side_effect=__import__("subprocess").TimeoutExpired("pytest", 300),
            ),
            redirect_stderr(stderr := StringIO()),
        ):
            assert run_all.main() == run_all.TEST_TIMEOUT_EXIT_CODE

    assert stderr.getvalue().splitlines() == [
        f"FAILED: test_slow.py (timeout {run_all.TEST_TIMEOUT_SECONDS}s)"
    ]


def test_github_governance_helpers_are_safe_for_pytest_collection() -> None:
    governance_path = Path(__file__).with_name("test_github_governance.py")
    tree = ast.parse(governance_path.read_text(encoding="utf-8"))
    functions = {
        node.name: node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    required_helpers = {
        "_assert_release_supply_chain",
        "_assert_release_runtime_and_packages",
        "_assert_release_publication_boundary",
        "_assert_release_preflight_precedes_packaging",
    }

    assert required_helpers <= functions.keys()
    for name, function in functions.items():
        if not name.startswith("test_"):
            continue
        positional = [*function.args.posonlyargs, *function.args.args]
        required_count = len(positional) - len(function.args.defaults)
        assert required_count == 0, (
            f"{name} exposes required parameters that pytest will treat as fixtures"
        )

    release_workflow = functions["test_release_workflow"]
    called_names = {
        call.func.id
        for call in ast.walk(release_workflow)
        if isinstance(call, ast.Call) and isinstance(call.func, ast.Name)
    }
    assert required_helpers <= called_names

    main = functions["main"]
    main_calls = {
        call.func.id
        for call in ast.walk(main)
        if isinstance(call, ast.Call) and isinstance(call.func, ast.Name)
    }
    assert "test_release_workflow" in main_calls
    assert run_all._test_commands(governance_path) == (
        [sys.executable, str(governance_path)],
    )


def test_repository_inventory_includes_native_vision_and_architecture_suites() -> None:
    names = {
        test.name for test in run_all.TESTS_DIR.glob("test_*.py")
    }
    required = {
        "test_architecture_contracts.py",
        "test_flagship_ui_decoupling_contract.py",
        "test_native_acceleration.py",
        "test_native_build_contract.py",
        "test_native_equivalence.py",
        "test_native_packaging_contract.py",
        "test_native_product_integration.py",
        "test_native_release_evidence.py",
        "test_native_rgba_equivalence.py",
        "test_opencv_vision.py",
        "test_v4_vision_architecture_contracts.py",
        "test_vision_controller.py",
        "test_vision_runtime.py",
    }

    assert required <= names
    assert all(run_all._test_commands(run_all.TESTS_DIR / name) for name in required)


def test_repository_never_runs_the_same_whole_test_file_twice() -> None:
    for test in run_all.TESTS_DIR.glob("test_*.py"):
        commands = run_all._test_commands(test)
        whole_file_runs = [
            command
            for command in commands
            if any(argument == str(test) for argument in command)
        ]
        assert len(whole_file_runs) <= 1, test.name
        for command in commands[1:]:
            pytest_targets = [
                argument
                for argument in command
                if argument.startswith(f"{test}::")
            ]
            assert pytest_targets, (
                f"{test.name} repeats a whole-file command instead of selecting "
                "only the missing pytest nodes"
            )


if __name__ == "__main__":
    test_each_child_receives_an_independent_sanitized_environment()
    test_first_failure_stops_the_sorted_run_and_preserves_exit_code()
    test_malformed_test_source_fails_closed_without_starting_a_child()
    test_mixed_module_uses_one_process_when_main_covers_pytest_nodes()
    test_mixed_module_only_collects_nodes_missing_from_main()
    test_mixed_module_combines_missing_pytest_nodes_in_one_process()
    test_unittest_main_does_not_duplicate_wrapped_pytest_functions()
    test_pure_pytest_delegate_to_main_runner_is_not_duplicated()
    test_bare_function_reference_does_not_count_as_execution()
    test_explicit_function_collection_loop_counts_as_execution()
    test_parametrized_delegate_is_not_assumed_to_be_covered()
    test_pure_main_script_still_runs_as_a_script()
    test_shards_are_complete_disjoint_deterministic_and_balanced()
    test_main_runs_only_the_requested_shard()
    test_timeout_fails_closed_with_stable_exit_code()
    test_github_governance_helpers_are_safe_for_pytest_collection()
    test_repository_inventory_includes_native_vision_and_architecture_suites()
    test_repository_never_runs_the_same_whole_test_file_twice()
    print("RUN_ALL_ISOLATION_OK")
