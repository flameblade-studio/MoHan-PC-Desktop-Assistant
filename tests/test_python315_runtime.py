from __future__ import annotations

lazy import io
lazy import re
lazy import subprocess
lazy import sys
lazy from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

lazy from app import DEFAULT_PROFILE, EXPRESSION_POSES
lazy from cloud_connectors import PROVIDERS
lazy from db import DEFAULT_REMINDERS
lazy from expression_system import EMOTION_TO_EXPRESSION, EXPRESSION_RULES
lazy from flagship_core import CAPABILITY_RISK, RISK_NAMES
lazy from home_assistant import ALLOWED_SERVICES
lazy from language_support import TRANSCRIPTION_PROMPT_BASES
lazy from lip_sync import VISEME_MIN_HOLD_SECONDS
lazy from preview_app import _TEXT
lazy from runtime_bootstrap import JIT_DISABLE_ENV, JIT_REEXEC_ENV
lazy from time_utils import (
    local_aware_time,
    local_wall_time,
    local_wall_time_from_timestamp,
)


def assert_immutable_mapping(value: object) -> None:
    assert type(value) is frozendict
    try:
        value["__mutation_probe__"] = object()  # type: ignore[index]
    except TypeError:
        return
    raise AssertionError("configuration mapping accepted a runtime mutation")


def main() -> None:
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
    print("PYTHON315_AND_PEP810_IMPORTS_OK")


if __name__ == "__main__":
    main()
