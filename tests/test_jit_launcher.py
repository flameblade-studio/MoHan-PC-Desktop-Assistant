from __future__ import annotations

lazy import subprocess
lazy import sys
lazy from pathlib import Path
lazy from types import SimpleNamespace

lazy import pytest

lazy from tools import jit_launcher

FORWARDED_EXIT_CODE = 7


def test_launcher_disables_jit_by_default(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    launcher = tmp_path / "MoHan-Desktop-Assistant-v4.4.2.exe"
    runtime = tmp_path / "MoHan-Desktop-Assistant-v4.4.2-runtime.exe"
    captured: dict[str, object] = {}

    def run(arguments, *, check, env):
        captured.update(arguments=arguments, check=check, env=env)
        return SimpleNamespace(returncode=FORWARDED_EXIT_CODE)

    monkeypatch.setattr(sys, "executable", str(launcher))
    monkeypatch.setattr(sys, "argv", [str(launcher), "--self-test"])
    monkeypatch.setattr(subprocess, "run", run)
    monkeypatch.setenv("PYTHONHASHSEED", "unsafe-parent-value")
    monkeypatch.delenv("MOHAN_ENABLE_JIT", raising=False)

    assert jit_launcher.main() == FORWARDED_EXIT_CODE
    assert captured["arguments"] == [str(runtime), "--self-test"]
    assert captured["check"] is False
    environment = captured["env"]
    assert isinstance(environment, dict)
    # Stability-first default after the 2026-08-29 mid-session 0xC0000409
    # crash on a user machine (3.15rc1 JIT/Qt failure family).
    assert environment["PYTHON_JIT"] == "0"
    assert "PYTHONHASHSEED" not in environment


def test_launcher_honours_explicit_jit_opt_in(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    launcher = tmp_path / "MoHan.exe"
    captured: dict[str, object] = {}

    def run(arguments, *, check, env):
        captured.update(arguments=arguments, check=check, env=env)
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(sys, "executable", str(launcher))
    monkeypatch.setattr(sys, "argv", [str(launcher)])
    monkeypatch.setattr(subprocess, "run", run)
    monkeypatch.setenv("MOHAN_ENABLE_JIT", "1")

    assert jit_launcher.main() == 0
    environment = captured["env"]
    assert isinstance(environment, dict)
    assert environment["PYTHON_JIT"] == "1"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__]))
