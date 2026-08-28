from __future__ import annotations

lazy import os
lazy import subprocess
lazy import sys
lazy from os import _exit as _process_exit

JIT_ENABLE_ENV = "MOHAN_ENABLE_JIT"
JIT_REEXEC_ENV = "MOHAN_JIT_REEXEC"


def jit_is_enabled() -> bool:
    jit = getattr(sys, "_jit", None)
    return bool(jit and jit.is_enabled())


def finalize_process_exit(code: int) -> int:
    """Avoid CPython JIT finalizers after the frozen Qt app has cleaned up.

    ``run_application`` returns only after the companion window, dashboard,
    timers, database, and Qt event loop have completed their owned shutdown.
    The remaining interpreter finalization path is where the Python 3.15rc1
    JIT runtime can corrupt Qt-owned heaps on Windows. A frozen JIT build exits
    at that boundary; development and non-JIT processes keep normal semantics.
    """

    if bool(getattr(sys, "frozen", False)) and jit_is_enabled():
        _process_exit(int(code))
    return int(code)


def ensure_default_jit(module_name: str, script_path: str) -> None:
    """Require the runtime JIT state to match the shipped policy.

    Stability-first since 2026-08-29: a JIT-enabled runtime crashed with
    0xC0000409 mid-session on a user machine, so the launcher now supplies
    ``PYTHON_JIT=0`` by default and ``MOHAN_ENABLE_JIT=1`` opts back in as an
    explicit experiment. Frozen builds assert the state matches that policy;
    development entry points restart once only when the experiment asks for
    a JIT the current process does not have.
    """
    expect_jit = os.environ.get(JIT_ENABLE_ENV) == "1"
    is_frozen_entrypoint = bool(getattr(sys, "frozen", False))
    if is_frozen_entrypoint:
        if jit_is_enabled() != expect_jit:
            raise RuntimeError(
                "Frozen MoHan runtime JIT state does not match the "
                "launcher policy"
            )
        return
    if (
        module_name != "__main__"
    ) or sys.version_info[:2] != (3, 15):
        return
    if not expect_jit or jit_is_enabled():
        return
    jit = getattr(sys, "_jit", None)
    if not jit or not jit.is_available() or os.environ.get(JIT_REEXEC_ENV) == "1":
        return

    environment = os.environ.copy()
    environment["PYTHON_JIT"] = "1"
    environment[JIT_REEXEC_ENV] = "1"
    arguments = [sys.executable, script_path, *sys.argv[1:]]
    if sys.platform == "win32":
        completed = subprocess.run(arguments, env=environment, check=False)
        raise SystemExit(completed.returncode)
    os.execve(sys.executable, arguments, environment)
