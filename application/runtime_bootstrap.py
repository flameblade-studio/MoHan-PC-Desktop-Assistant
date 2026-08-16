from __future__ import annotations

lazy import os
lazy import subprocess
lazy import sys

JIT_DISABLE_ENV = "MOHAN_DISABLE_JIT"
JIT_REEXEC_ENV = "MOHAN_JIT_REEXEC"


def jit_is_enabled() -> bool:
    jit = getattr(sys, "_jit", None)
    return bool(jit and jit.is_enabled())


def ensure_default_jit(module_name: str, script_path: str) -> None:
    """Restart the executable once so CPython initializes with JIT enabled."""
    is_frozen_entrypoint = bool(getattr(sys, "frozen", False))
    if (
        module_name != "__main__"
        and not is_frozen_entrypoint
    ) or sys.version_info[:2] != (3, 15):
        return
    if os.environ.get(JIT_DISABLE_ENV) == "1" or jit_is_enabled():
        return
    jit = getattr(sys, "_jit", None)
    if not jit or not jit.is_available() or os.environ.get(JIT_REEXEC_ENV) == "1":
        return

    environment = os.environ.copy()
    environment["PYTHON_JIT"] = "1"
    environment[JIT_REEXEC_ENV] = "1"
    if getattr(sys, "frozen", False):
        arguments = [sys.executable, *sys.argv[1:]]
    else:
        arguments = [sys.executable, script_path, *sys.argv[1:]]
    if sys.platform == "win32":
        completed = subprocess.run(arguments, env=environment, check=False)
        raise SystemExit(completed.returncode)
    os.execve(sys.executable, arguments, environment)
