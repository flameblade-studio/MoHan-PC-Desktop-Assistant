from __future__ import annotations

lazy import os
lazy import subprocess
lazy import sys
lazy from pathlib import Path
lazy from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]


def assert_malformed_decision_queue_json_hard_fails() -> None:
    with TemporaryDirectory() as temporary:
        root = Path(temporary)
        artifacts = root / "artifacts" / "broken-evidence"
        artifacts.mkdir(parents=True)
        broken = artifacts / "broken.json"
        broken.write_text('{"status": "PENDING"', encoding="utf-8")
        output_path = ROOT / "tools" / "second_gen_body" / "probes" / "decision-queue.tsv"
        had_output = output_path.is_file()
        previous_output = output_path.read_bytes() if had_output else None
        try:
            completed = subprocess.run(
                [sys.executable, str(ROOT / "tools/second_gen_body/probes/decision_queue.py")],
                cwd=ROOT,
                env={**os.environ, "MOHAN_VISION_ROOT": str(root)},
                capture_output=True,
                text=True,
                check=False,
            )
        finally:
            if had_output:
                output_path.write_bytes(previous_output or b"")
            else:
                output_path.unlink(missing_ok=True)
        combined = completed.stdout + completed.stderr
        assert completed.returncode != 0
        assert "broken.json" in combined
        assert "line" in combined and "column" in combined


def run() -> None:
    checks = (assert_malformed_decision_queue_json_hard_fails,)
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
