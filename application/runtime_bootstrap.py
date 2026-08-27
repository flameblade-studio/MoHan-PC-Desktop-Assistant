from __future__ import annotations

lazy import os
lazy import subprocess
lazy import sys
lazy from os import _exit as _process_exit

JIT_DISABLE_ENV = "MOHAN_DISABLE_JIT"
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
    """Require frozen builds to start with JIT enabled before Python init.

    Development entry points may restart once with ``PYTHON_JIT=1``. Frozen
    applications are started by the public launcher, which removes inherited
    ``PYTHON*`` settings and supplies only ``PYTHON_JIT=1`` to the narrowly
    patched bootloader. The runtime must already have JIT enabled here.
    """
    is_frozen_entrypoint = bool(getattr(sys, "frozen", False))
    if is_frozen_entrypoint:
        if not jit_is_enabled():
            raise RuntimeError(
                "Frozen MoHan runtime requires launcher-enabled JIT"
            )
        return
    if (
        module_name != "__main__"
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
    arguments = [sys.executable, script_path, *sys.argv[1:]]
    if sys.platform == "win32":
        completed = subprocess.run(arguments, env=environment, check=False)
        raise SystemExit(completed.returncode)
    os.execve(sys.executable, arguments, environment)
