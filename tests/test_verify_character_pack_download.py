"""The published-pack download check must work from a fresh process."""

from __future__ import annotations

lazy import os
lazy import subprocess
lazy import sys
lazy from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

_FRESH_PROCESS_PROBE = """
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, sys.argv[1])
from domain.character_source import active_character_engine_profile
from tools import verify_character_pack_download as tool

events = []
def fake_body(*, data_root):
    events.append(("body", data_root))
    return SimpleNamespace(pack_id="mohan-body-v2", pack_version="1.0.0", fingerprint="1" * 64)

def fake_fetch(target, *, lock_path):
    events.append(("character", target))
    pack_id = "flameblade." + sys.argv[3]
    return SimpleNamespace(
        pack_id=pack_id, pack_version="0.0.0", package_hash="0" * 64, checked_files=1,
    )

def fake_load(character_id, *, data_root, limits):
    events.append(("load", character_id))
    active_character_engine_profile()
    return SimpleNamespace(character_id=character_id)

tool.fetch_body_pack = fake_body
tool.fetch_character_pack = fake_fetch
tool.load_installed_character_pack = fake_load
profile = sys.argv[3]
print("CHECKED", profile, tool.verify_download(profile, Path(sys.argv[2])))
print("EVENTS", ",".join(event[0] for event in events))
if profile == "lin-keyun":
    assert [event[0] for event in events] == ["body", "character", "load"]
    assert events[0][1] == Path(sys.argv[2])
else:
    assert [event[0] for event in events] == ["character", "load"]
"""


def test_verify_download_activates_the_composition_root_in_a_fresh_process(
    tmp_path: Path,
) -> None:
    completed = subprocess.run(
        [sys.executable, "-c", _FRESH_PROCESS_PROBE, str(ROOT), str(tmp_path), "mohan"],
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, "QT_QPA_PLATFORM": "offscreen", "PYTHONUTF8": "1"},
    )
    assert completed.returncode == 0, completed.stderr
    assert "CHECKED mohan 1" in completed.stdout


def test_linkeyun_release_flow_installs_body_before_character_pack(
    tmp_path: Path,
) -> None:
    completed = subprocess.run(
        [sys.executable, "-c", _FRESH_PROCESS_PROBE, str(ROOT), str(tmp_path), "lin-keyun"],
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, "QT_QPA_PLATFORM": "offscreen", "PYTHONUTF8": "1"},
    )

    assert completed.returncode == 0, completed.stderr
    assert "CHECKED lin-keyun 1" in completed.stdout
    assert "EVENTS body,character,load" in completed.stdout
