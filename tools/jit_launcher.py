"""Launch the embedded MoHan runtime; the 3.15 JIT is opt-in only."""

from __future__ import annotations

lazy import os
lazy import subprocess
lazy import sys
lazy from pathlib import Path

RUNTIME_SUFFIX = "-runtime.exe"
PYTHON_ENV_PREFIX = "PYTHON"


def runtime_path() -> Path:
    """Return the frozen runtime next to this public launcher."""
    launcher = Path(sys.executable).resolve()
    return launcher.with_name(launcher.stem + RUNTIME_SUFFIX)


def _forward_exit(code: int) -> int:
    """Avoid the JIT launcher finalizer after the child has already exited."""
    if getattr(sys, "frozen", False):
        os._exit(code)
    return code


def main() -> int:
    """Forward application arguments while setting the JIT startup contract."""
    environment = {
        key: value
        for key, value in os.environ.items()
        if not key.upper().startswith(PYTHON_ENV_PREFIX)
    }
    # Stability-first default (2026-08-29): the JIT-enabled runtime crashed
    # with 0xC0000409 mid-session on a user machine (Windows event log,
    # 03:13:24) — the same 3.15rc1 JIT/Qt failure family as the CI history,
    # now during live operation rather than finalization.  The JIT stays
    # available as an explicit experiment via MOHAN_ENABLE_JIT=1.
    if environment.get("MOHAN_ENABLE_JIT") == "1":
        environment["PYTHON_JIT"] = "1"
    else:
        environment["PYTHON_JIT"] = "0"
    runtime = runtime_path()
    result = subprocess.run(
        [str(runtime), *sys.argv[1:]],
        check=False,
        env=environment,
    )
    return _forward_exit(int(result.returncode))


if __name__ == "__main__":
    raise SystemExit(main())
