from __future__ import annotations

lazy import os
lazy import struct
lazy import subprocess
lazy import sys
lazy from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
sys.path.insert(0, str(TOOLS))

lazy import capture_control_center_reference
lazy import capture_readme_media
lazy from PySide6.QtCore import QTimer
lazy from PySide6.QtWidgets import QApplication


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


def close_dashboard_for_test(dashboard, db) -> None:
    dashboard.flagship_center.close_services()
    for timer in dashboard.findChildren(QTimer):
        timer.stop()
    dashboard.close()
    dashboard.deleteLater()
    QApplication.processEvents()
    db.close()


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


def test_readme_capture_preserves_demo_profile_content(
    tmp_path: Path,
    monkeypatch,
) -> None:
    observed: dict[str, str] = {}

    def close_and_record(dashboard, db) -> None:
        observed.update(
            assistant_name=str(db.setting("assistant_name")),
            user_title=str(db.setting("user_title")),
            organization_name=str(db.setting("organization_name")),
            window_title_setting=str(db.setting("window_title")),
            window_title=dashboard.windowTitle(),
            header=dashboard.header_title.text(),
        )
        close_dashboard_for_test(dashboard, db)

    monkeypatch.setattr(capture_readme_media, "close_dashboard", close_and_record)
    capture_readme_media.capture_media(tmp_path / "readme", None, "tasks")

    assert observed == {
        "assistant_name": "墨寒",
        "user_title": "主上",
        "organization_name": "炎劍文化工作室",
        "window_title_setting": "墨寒．炎劍文化工作室",
        "window_title": "墨寒．炎劍文化工作室",
        "header": "<b>墨寒．炎劍文化工作室</b>",
    }


def test_control_center_security_capture_selects_security_subpage(
    tmp_path: Path,
    monkeypatch,
) -> None:
    observed: dict[str, object] = {}

    def close_and_record(dashboard, db) -> None:
        inner_index = dashboard.flagship_center.tabs.currentIndex()
        observed.update(
            outer_index=dashboard.tabs.currentIndex(),
            inner_index=inner_index,
            inner_label=dashboard.flagship_center.tabs.tabText(inner_index),
        )
        close_dashboard_for_test(dashboard, db)

    monkeypatch.setattr(
        capture_control_center_reference,
        "close_dashboard",
        close_and_record,
    )
    output = capture_control_center_reference.capture(
        tmp_path / "control-center",
        "security",
    )

    assert output.is_file()
    assert observed == {
        "outer_index": 5,
        "inner_index": 6,
        "inner_label": "安全權限",
    }


def test_control_center_capture_accepts_tasks_and_ideas_alias(
    tmp_path: Path,
    monkeypatch,
) -> None:
    observed: dict[str, int] = {}

    def close_and_record(dashboard, db) -> None:
        observed["outer_index"] = dashboard.tabs.currentIndex()
        close_dashboard_for_test(dashboard, db)

    monkeypatch.setattr(
        capture_control_center_reference,
        "close_dashboard",
        close_and_record,
    )
    output = capture_control_center_reference.capture(
        tmp_path / "control-center",
        "tasks-and-ideas",
    )

    assert output.is_file()
    assert observed == {"outer_index": 1}
