from __future__ import annotations

lazy import os
lazy import shutil
lazy import subprocess
lazy import sys
lazy from pathlib import Path
lazy from tempfile import TemporaryDirectory
lazy from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ROOT = PROJECT_ROOT
DECISION_QUEUE_SCRIPT = Path("tools/second_gen_body/probes/decision_queue.py")


def assert_malformed_decision_queue_json_hard_fails() -> None:
    with TemporaryDirectory() as temporary:
        root = Path(temporary)
        artifacts = root / "artifacts" / "broken-evidence"
        artifacts.mkdir(parents=True)
        broken = artifacts / "broken.json"
        broken.write_text('{"status": "PENDING"', encoding="utf-8")
        script_path = root / DECISION_QUEUE_SCRIPT
        script_path.parent.mkdir(parents=True)
        shutil.copyfile(PROJECT_ROOT / DECISION_QUEUE_SCRIPT, script_path)
        completed = subprocess.run(
            [sys.executable, str(script_path)],
            cwd=root,
            env={**os.environ, "MOHAN_VISION_ROOT": str(root)},
            capture_output=True,
            text=True,
            check=False,
        )
        combined = completed.stdout + completed.stderr
        assert completed.returncode != 0
        assert "broken.json" in combined
        assert "line" in combined and "column" in combined


def test_runner_preserves_a_concurrent_queue_result() -> None:
    with TemporaryDirectory() as temporary:
        root = Path(temporary) / "project"
        script_path = root / DECISION_QUEUE_SCRIPT
        script_path.parent.mkdir(parents=True)
        shutil.copyfile(PROJECT_ROOT / DECISION_QUEUE_SCRIPT, script_path)
        output_path = script_path.with_name("decision-queue.tsv")
        output_path.write_bytes(b"old queue result")
        invoked_scripts: list[Path] = []

        def another_process_writes_result(
            command: list[str], **kwargs: object
        ) -> subprocess.CompletedProcess[str]:
            del kwargs
            invoked_scripts.append(Path(command[1]))
            output_path.write_bytes(b"new queue result")
            return subprocess.CompletedProcess(
                command,
                1,
                stdout="broken.json",
                stderr="line 1, column 1",
            )

        with patch.object(sys.modules[__name__], "ROOT", root), patch.object(
            subprocess, "run", another_process_writes_result
        ):
            assert_malformed_decision_queue_json_hard_fails()

        assert output_path.read_bytes() == b"new queue result"
        assert len(invoked_scripts) == 1
        assert invoked_scripts[0] != script_path


def run() -> None:
    checks = (
        assert_malformed_decision_queue_json_hard_fails,
        test_runner_preserves_a_concurrent_queue_result,
    )
    failures: list[str] = []
    for check in checks:
        try:
            check()
        except Exception as error:
            failures.append(f"{check.__name__}: {type(error).__name__}: {error}")
    if failures:
        raise AssertionError("\n".join(failures))
    print("D07_DECISION_QUEUE_OK")


if __name__ == "__main__":
    run()
