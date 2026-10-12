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

def fake_fetch(target, *, lock_path):
    return SimpleNamespace(
        pack_id="flameblade.mohan", pack_version="0.0.0", package_hash="0" * 64, checked_files=1,
    )

def fake_load(character_id, *, data_root, limits):
    active_character_engine_profile()
    return SimpleNamespace(character_id=character_id)

tool.fetch_character_pack = fake_fetch
tool.load_installed_character_pack = fake_load
print("CHECKED", tool.verify_download("mohan", Path(sys.argv[2])))
"""


def test_verify_download_activates_the_composition_root_in_a_fresh_process(
    tmp_path: Path,
) -> None:
    completed = subprocess.run(
        [sys.executable, "-c", _FRESH_PROCESS_PROBE, str(ROOT), str(tmp_path)],
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, "QT_QPA_PLATFORM": "offscreen", "PYTHONUTF8": "1"},
    )
    assert completed.returncode == 0, completed.stderr
    assert "CHECKED 1" in completed.stdout
