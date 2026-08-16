from __future__ import annotations

lazy import ast
lazy import json
lazy import sys
lazy import tempfile
lazy from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from tools.check_python315_qt_release import (
    QT_DISTRIBUTIONS,
    inspect_metadata,
    main,
)

ROOT = Path(__file__).resolve().parents[1]
BLOCKER = ROOT / "docs" / "release-evidence" / "V4-PYTHON315-QT-BLOCKER.md"


def metadata(requires_python: str) -> dict[str, tuple[dict, str]]:
    return {
        distribution: (
            {
                "info": {
                    "version": "6.11.1",
                    "requires_python": requires_python,
                }
            },
            f"fixture:{distribution}",
        )
        for distribution in QT_DISTRIBUTIONS
    }


def test_official_metadata_shape_blocks_python315_rc1() -> None:
    report = inspect_metadata(metadata(">=3.10,<3.15"))
    assert not report.releasable
    assert len(report.evidence) == 4
    assert len(report.issues) == 4
    assert all(not item.target_supported for item in report.evidence)


def test_future_compatible_metadata_can_unblock_without_bypass() -> None:
    report = inspect_metadata(metadata(">=3.10,<3.16"))
    assert report.releasable
    assert not report.issues


def test_cli_fails_closed_with_reproducible_snapshots() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        requirements = root / "requirements.txt"
        requirements.write_text("PySide6==6.11.1\n", encoding="utf-8")
        for distribution, (payload, _) in metadata(">=3.10,<3.15").items():
            (root / f"{distribution}.json").write_text(
                json.dumps(payload),
                encoding="utf-8",
            )
        assert main(
            [
                "--requirements",
                str(requirements),
                "--metadata-dir",
                str(root),
            ]
        ) == 1


def test_clean_installer_has_no_requires_python_bypass_or_early_qt_import() -> None:
    installer_path = ROOT / "tools" / "install_python315_dependencies.py"
    source = installer_path.read_text(encoding="utf-8")
    assert "--ignore-requires-python" not in source
    tree = ast.parse(source, filename=str(installer_path))
    top_level_imports = [
        node
        for node in tree.body
        if isinstance(node, (ast.Import, ast.ImportFrom))
    ]
    assert not any(
        isinstance(node, ast.ImportFrom)
        and node.module
        and node.module.startswith("PySide6")
        for node in top_level_imports
    )
    assert "inspect_official_release" in source
    assert '"--only-binary=:all:"' in source


def test_blocker_is_complete_four_language_release_evidence() -> None:
    text = BLOCKER.read_text(encoding="utf-8")
    headings = ("## 繁體中文", "## 简体中文", "## English", "## 日本語")
    positions = [text.index(heading) for heading in headings]
    assert positions == sorted(positions)
    for required in (
        "3.15.0rc1",
        "PySide6 6.11.1",
        ">=3.10,<3.15",
        "--ignore-requires-python",
        "https://pypi.org/pypi/PySide6/6.11.1/json",
        "https://pypi.org/pypi/PySide6_Essentials/6.11.1/json",
        "https://pypi.org/pypi/PySide6_Addons/6.11.1/json",
        "https://pypi.org/pypi/shiboken6/6.11.1/json",
    ):
        assert required in text


def run() -> None:
    test_official_metadata_shape_blocks_python315_rc1()
    test_future_compatible_metadata_can_unblock_without_bypass()
    test_cli_fails_closed_with_reproducible_snapshots()
    test_clean_installer_has_no_requires_python_bypass_or_early_qt_import()
    test_blocker_is_complete_four_language_release_evidence()


if __name__ == "__main__":
    run()
