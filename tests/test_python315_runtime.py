from __future__ import annotations

lazy import io
lazy import re
lazy import subprocess
lazy import sys
lazy from pathlib import Path
lazy from tempfile import TemporaryDirectory

lazy import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

lazy from domain.app_profile import DEFAULT_PROFILE
lazy from domain.companion_animation_contract import EXPRESSION_POSES
lazy from domain.flagship_action_models import CAPABILITY_RISK, RISK_NAMES
lazy from domain.expression_system import EMOTION_TO_EXPRESSION, EXPRESSION_RULES
lazy from infrastructure.db import DEFAULT_REMINDERS
lazy from integrations.cloud_connectors import PROVIDERS
lazy from integrations.home_assistant import ALLOWED_SERVICES
lazy from domain.language_support import TRANSCRIPTION_PROMPT_BASES
lazy from domain.lip_sync import VISEME_MIN_HOLD_SECONDS
lazy from presentation.preview_app import _TEXT
lazy from application import runtime_bootstrap
lazy from application.runtime_bootstrap import JIT_DISABLE_ENV, JIT_REEXEC_ENV
lazy from domain.time_utils import (
    local_aware_time,
    local_wall_time,
    local_wall_time_from_timestamp,
)
lazy from tools.migrate_python315_imports import inventory, python_files

EXPECTED_EXCEPTION_COUNT = 3
FROZEN_EXIT_PROBE_CODE = 7


def test_frozen_runtime_requires_jit_default_cpython(monkeypatch) -> None:
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(runtime_bootstrap, "jit_is_enabled", lambda: False)
    with pytest.raises(RuntimeError, match="launcher-enabled JIT"):
        runtime_bootstrap.ensure_default_jit(
            "application.application_bootstrap",
            "app.py",
        )


def test_frozen_jit_exit_skips_unsafe_interpreter_finalizers(monkeypatch) -> None:
    exits: list[int] = []
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(runtime_bootstrap, "jit_is_enabled", lambda: True)
    monkeypatch.setattr(runtime_bootstrap, "_process_exit", exits.append)
    assert runtime_bootstrap.finalize_process_exit(
        FROZEN_EXIT_PROBE_CODE
    ) == FROZEN_EXIT_PROBE_CODE
    assert exits == [FROZEN_EXIT_PROBE_CODE]


def assert_immutable_mapping(value: object) -> None:
    assert type(value) is frozendict
    try:
        value["__mutation_probe__"] = object()  # type: ignore[index]
    except TypeError:
        return
    raise AssertionError("configuration mapping accepted a runtime mutation")


def _assert_python315_language_features() -> None:
    assert sys.version_info[:2] == (3, 15), sys.version
    assert callable(sys.get_lazy_imports)
    assert callable(sys.set_lazy_imports)
    assert callable(sys.get_lazy_imports_filter)
    assert callable(sys.set_lazy_imports_filter)
    assert io.text_encoding(None) == "utf-8"
    assert re.prefixmatch(r"^MoHan", "MoHan Desktop Assistant") is not None
    assert JIT_DISABLE_ENV == "MOHAN_DISABLE_JIT"
    assert JIT_REEXEC_ENV == "MOHAN_JIT_REEXEC"
    aware_now = local_aware_time()
    wall_now = local_wall_time()
    assert aware_now.tzinfo is not None
    assert wall_now.tzinfo is None
    assert local_wall_time_from_timestamp(aware_now.timestamp()).tzinfo is None

    matrix = ((1, 2), (3, 4))
    assert [*row for row in matrix] == [1, 2, 3, 4]
    assert {**item for item in ({"a": 1}, {"b": 2})} == {"a": 1, "b": 2}

    packet = bytearray(b"abcdef")
    assert packet.take_bytes(4) == b"abcd"
    assert packet == b"ef"

    missing = sentinel("MISSING")
    assert repr(missing) == "MISSING"
    assert missing is not sentinel("MISSING")


def _assert_lazy_import_audit_contract() -> None:
    with TemporaryDirectory() as temp_dir:
        inventory_root = Path(temp_dir)
        project_source = inventory_root / "project_source.py"
        project_source.write_text("lazy import json\n", encoding="utf-8")
        cpython_source = inventory_root / "_python315" / "Lib"
        cpython_source.mkdir(parents=True)
        (cpython_source / "test_fixture.py").write_bytes(b"# \xe9\n")
        generated_source = (
            inventory_root
            / "native"
            / "mohan_accel"
            / "target"
            / "generated.py"
        )
        generated_source.parent.mkdir(parents=True)
        generated_source.write_text("from generated import *\n", encoding="utf-8")
        assert python_files(inventory_root) == [project_source]
        eager_source = inventory_root / "eager_source.py"
        eager_source.write_text("import json\n", encoding="utf-8")
        assert inventory(eager_source).eligible == [1]

    concurrency_inventory = inventory(
        ROOT / "domain" / "python315_concurrency.py"
    )
    assert concurrency_inventory.eligible == []
    assert len(concurrency_inventory.exceptions) == EXPECTED_EXCEPTION_COUNT


def _assert_immutable_configuration() -> None:
    for mapping in (
        DEFAULT_PROFILE,
        EXPRESSION_POSES,
        PROVIDERS,
        DEFAULT_REMINDERS,
        EMOTION_TO_EXPRESSION,
        EXPRESSION_RULES,
        CAPABILITY_RISK,
        RISK_NAMES,
        TRANSCRIPTION_PROMPT_BASES,
        VISEME_MIN_HOLD_SECONDS,
        ALLOWED_SERVICES,
        _TEXT,
    ):
        assert_immutable_mapping(mapping)
    assert type(ALLOWED_SERVICES["light"]) is frozenset
    assert type(_TEXT["zh-TW"]) is frozendict


def _run_governance_audits() -> None:
    probe = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import sys; lazy import json; "
                "assert 'json' not in sys.modules; "
                "assert json.dumps({'ok': True}) == '{\"ok\": true}'; "
                "assert 'json' in sys.modules"
            ),
        ],
        check=False,
    )
    assert probe.returncode == 0

    audit = subprocess.run(
        [
            sys.executable,
            str(ROOT / "tools" / "migrate_python315_imports.py"),
            "--check",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert audit.returncode == 0, audit.stdout + audit.stderr
    assert "pending=0" in audit.stdout
    assert "configured_exceptions=" in audit.stdout
    assert "compatibility_alias_imports=" in audit.stdout
    assert "unmatched_exceptions=0" in audit.stdout

    compatibility = subprocess.run(
        [
            sys.executable,
            str(ROOT / "tools" / "audit_python315_compatibility.py"),
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert compatibility.returncode == 0, (
        compatibility.stdout + compatibility.stderr
    )
    assert "issues=0" in compatibility.stdout

    idioms = subprocess.run(
        [
            sys.executable,
            str(ROOT / "tools" / "audit_python315_idioms.py"),
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert idioms.returncode == 0, idioms.stdout + idioms.stderr
    assert "findings=0" in idioms.stdout

    dependencies = subprocess.run(
        [
            sys.executable,
            str(ROOT / "tools" / "install_python315_dependencies.py"),
            "--verify-only",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert dependencies.returncode == 0, dependencies.stdout + dependencies.stderr
    assert "QT_STABLE_ABI_OK" in dependencies.stdout


def main() -> None:
    _assert_python315_language_features()
    _assert_lazy_import_audit_contract()
    _assert_immutable_configuration()
    _run_governance_audits()
    print("PYTHON315_AND_PEP810_IMPORTS_OK")


if __name__ == "__main__":
    main()
