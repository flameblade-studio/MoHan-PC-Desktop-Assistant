from __future__ import annotations

lazy import os
lazy import struct
lazy import subprocess
lazy import sys
lazy from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"


def png_size(path: Path) -> tuple[int, int]:
    data = path.read_bytes()[:24]
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    return struct.unpack(">II", data[16:24])


def run_capture(
    tool_name: str,
    tab: str,
    output_dir: Path,
    *,
    screenshots_only: bool = False,
) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["QT_QPA_PLATFORM"] = "offscreen"
    environment["QT_SCALE_FACTOR"] = "1"
    environment["MOHAN_DATA_DIR"] = str(output_dir / "isolated-profile")
    arguments = [
        sys.executable,
        str(TOOLS / tool_name),
        "--tab",
        tab,
        "--output",
        str(output_dir),
    ]
    if screenshots_only:
        arguments.append("--screenshots-only")
    return subprocess.run(
        arguments,
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
        timeout=25,
    )


def test_capture_tools_write_expected_offscreen_pngs(tmp_path: Path) -> None:
    readme_output = tmp_path / "readme"
    readme_run = run_capture(
        "capture_readme_media.py",
        "tasks",
        readme_output,
        screenshots_only=True,
    )
    readme_image = readme_output / "tasks-and-ideas.png"
    assert readme_run.returncode == 0, (
        f"README capture failed:\n{readme_run.stdout}\n{readme_run.stderr}"
    )
    assert readme_image.is_file() and readme_image.stat().st_size > 0
    assert png_size(readme_image) == (1400, 900)

    control_output = tmp_path / "control-center"
    control_run = run_capture(
        "capture_control_center_reference.py",
        "security",
        control_output,
    )
    control_image = control_output / "control-center-reference.png"
    assert control_run.returncode == 0, (
        f"Control-center capture failed:\n{control_run.stdout}\n"
        f"{control_run.stderr}"
    )
    assert control_image.is_file() and control_image.stat().st_size > 0
    assert png_size(control_image) == (1320, 860)
