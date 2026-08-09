from __future__ import annotations

lazy import argparse
lazy import json
lazy import os
lazy import platform
lazy import subprocess
lazy from pathlib import Path

CPYTHON_VERSION = "3.15.0rc1"
CPYTHON_COMMIT = "37e98da7c19a9e5892ee756d6dee08225422cd49"


def _run(command: list[str], *, cwd: Path, env: dict[str, str] | None = None) -> None:
    subprocess.run(command, cwd=cwd, env=env, check=True)


def _output(command: list[str], *, cwd: Path) -> str:
    return subprocess.check_output(command, cwd=cwd, text=True).strip()


def verify_source(source: Path) -> None:
    actual = _output(["git", "rev-parse", "HEAD"], cwd=source)
    if actual != CPYTHON_COMMIT:
        raise RuntimeError(
            f"CPython source mismatch: expected {CPYTHON_COMMIT}, found {actual}"
        )


def runtime_path(source: Path, prefix: Path) -> Path:
    if os.name == "nt":
        return source / "PCbuild" / "amd64" / "python.exe"
    return prefix / "bin" / "python3.15"


def build(source: Path, prefix: Path) -> Path:
    verify_source(source)
    if os.name == "nt":
        _run(
            [
                "cmd.exe",
                "/d",
                "/c",
                r"PCbuild\build.bat",
                "-p",
                "x64",
                "-c",
                "Release",
                "--experimental-jit",
            ],
            cwd=source,
        )
    else:
        prefix.mkdir(parents=True, exist_ok=True)
        environment = os.environ.copy()
        _run(
            [
                str(source / "configure"),
                f"--prefix={prefix}",
                "--enable-experimental-jit=yes",
                "--with-ensurepip=install",
            ],
            cwd=source,
            env=environment,
        )
        jobs = max(1, os.cpu_count() or 1)
        _run(["make", "-j", str(jobs)], cwd=source, env=environment)
        _run(["make", "install"], cwd=source, env=environment)

    python = runtime_path(source, prefix)
    if not python.is_file():
        raise RuntimeError(f"JIT-default Python runtime was not created: {python}")
    _run([str(python), "-m", "ensurepip", "--upgrade"], cwd=source)
    verify_runtime(python)
    return python


def _probe(python: Path, value: str | None) -> dict[str, object]:
    environment = os.environ.copy()
    environment.pop("MOHAN_DISABLE_JIT", None)
    if value is None:
        environment.pop("PYTHON_JIT", None)
    else:
        environment["PYTHON_JIT"] = value
    completed = subprocess.run(
        [
            str(python),
            "-c",
            (
                "import json, platform, sys; "
                "print(json.dumps({'version': platform.python_version(), "
                "'available': sys._jit.is_available(), "
                "'enabled': sys._jit.is_enabled()}))"
            ),
        ],
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(completed.stdout)


def verify_runtime(python: Path) -> None:
    default = _probe(python, None)
    disabled = _probe(python, "0")
    if default != {
        "version": CPYTHON_VERSION,
        "available": True,
        "enabled": True,
    }:
        raise RuntimeError(f"CPython JIT-default contract failed: {default}")
    if disabled != {
        "version": CPYTHON_VERSION,
        "available": True,
        "enabled": False,
    }:
        raise RuntimeError(f"CPython PYTHON_JIT=0 contract failed: {disabled}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--prefix", type=Path, required=True)
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    source = args.source.resolve()
    prefix = args.prefix.resolve()
    verify_source(source)
    python = runtime_path(source, prefix)
    if args.verify_only:
        verify_runtime(python)
    else:
        python = build(source, prefix)
    print(
        json.dumps(
            {
                "result": "PYTHON315_JIT_DEFAULT_RUNTIME_OK",
                "python": str(python),
                "version": CPYTHON_VERSION,
                "source_commit": CPYTHON_COMMIT,
                "platform": platform.platform(),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
