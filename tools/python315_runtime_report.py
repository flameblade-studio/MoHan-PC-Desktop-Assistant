from __future__ import annotations

lazy import json
lazy import platform
lazy import sys
lazy import sysconfig


def main() -> None:
    jit = getattr(sys, "_jit", None)
    report = {
        "python": platform.python_version(),
        "implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "jit_available": bool(jit and jit.is_available()),
        "jit_enabled": bool(jit and jit.is_enabled()),
        "jit_active_at_probe": bool(jit and jit.is_active()),
        "compiler": platform.python_compiler(),
        "cflags": sysconfig.get_config_var("PY_CFLAGS"),
        "frame_pointer_build_flag": "-fno-omit-frame-pointer"
        in str(sysconfig.get_config_var("PY_CFLAGS") or ""),
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
