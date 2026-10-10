from __future__ import annotations

lazy import os
lazy import subprocess
lazy import sys
lazy from pathlib import Path

lazy import pytest

ROOT = Path(__file__).resolve().parents[1]


def _clean_environment() -> dict[str, str]:
    environment = os.environ.copy()
    environment.pop("MOHAN_ACTIVE_CHARACTER", None)
    environment.pop("MOHAN_DEV_CHARACTER_PACK_ARCHIVE", None)
    environment["QT_QPA_PLATFORM"] = "offscreen"
    return environment


def _run(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        (sys.executable, *arguments),
        cwd=ROOT,
        env=_clean_environment(),
        capture_output=True,
        check=False,
        text=True,
        timeout=30,
    )


def test_product_bootstrap_precedes_companion_window_resolution() -> None:
    completed = _run(
        "-c",
        "from application.character_runtime_bootstrap import "
        "activate_product_character_runtime; "
        "source = activate_product_character_runtime(); "
        "from presentation.companion_window import CompanionWindow; "
        "assert CompanionWindow.__name__ == 'CompanionWindow'; "
        "assert activate_product_character_runtime() is source; "
        "print('CHARACTER_ENTRYPOINT_OK')",
    )

    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.strip() == "CHARACTER_ENTRYPOINT_OK"


def test_companion_window_import_without_activation_fails_closed() -> None:
    completed = _run("-c", "import presentation.companion_window")

    assert completed.returncode != 0
    assert (
        "The composition root must activate a character source first."
        in completed.stderr
    )


@pytest.mark.parametrize(
    "arguments",
    (
        ("-m", "tools.audit_layered_full_body_semantics", "--help"),
        ("tools/benchmark_python315_hotpaths.py", "--help"),
        ("tools/build_character_pack.py", "--help"),
        ("presentation/preview_app.py", "--help"),
    ),
)
def test_character_aware_entrypoints_bootstrap_before_imports(
    arguments: tuple[str, ...],
) -> None:
    completed = _run(*arguments)

    assert completed.returncode == 0, completed.stderr
    assert "usage:" in completed.stdout.casefold()
