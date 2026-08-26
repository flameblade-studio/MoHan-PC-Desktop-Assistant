"""Launch the embedded MoHan runtime with Python 3.15 JIT enabled."""

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
    if environment.get("MOHAN_DISABLE_JIT") != "1":
        environment["PYTHON_JIT"] = "1"
    runtime = runtime_path()
    result = subprocess.run(
        [str(runtime), *sys.argv[1:]],
        check=False,
        env=environment,
    )
    return _forward_exit(int(result.returncode))


if __name__ == "__main__":
    raise SystemExit(main())
