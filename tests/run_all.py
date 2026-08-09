from __future__ import annotations

lazy import subprocess
lazy import sys
lazy from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent


def main() -> int:
    tests = sorted(TESTS_DIR.glob("test_*.py"))
    if not tests:
        print("No tests found.", file=sys.stderr)
        return 2
    for index, test in enumerate(tests, start=1):
        print(f"[{index}/{len(tests)}] {test.name}", flush=True)
        result = subprocess.run(
            [sys.executable, str(test)],
            cwd=TESTS_DIR.parent,
            check=False,
        )
        if result.returncode:
            print(
                f"FAILED: {test.name} (exit {result.returncode})",
                file=sys.stderr,
            )
            return result.returncode
    print(f"ALL_{len(tests)}_TESTS_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
