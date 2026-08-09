from __future__ import annotations

lazy import argparse
lazy import re
lazy import subprocess
lazy import sys
lazy from importlib.metadata import distribution as metadata_distribution
lazy from pathlib import Path

lazy from PySide6.QtCore import qVersion

ROOT = Path(__file__).resolve().parents[1]
QT_DISTRIBUTIONS = (
    "PySide6",
    "PySide6_Addons",
    "PySide6_Essentials",
    "shiboken6",
)
ABI3_TAG = re.compile(r"^Tag:\s+cp3\d+-abi3-", re.MULTILINE)


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Install and verify MoHan dependencies on Python 3.15."
    )
    parser.add_argument(
        "--requirements",
        type=Path,
        default=ROOT / "requirements.txt",
    )
    parser.add_argument("--verify-only", action="store_true")
    return parser.parse_args()


def requirement_lines(path: Path) -> list[str]:
    return [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]


def verify_qt_stable_abi() -> None:
    for distribution_name in QT_DISTRIBUTIONS:
        distribution = metadata_distribution(distribution_name)
        wheel = distribution.read_text("WHEEL") or ""
        if not ABI3_TAG.search(wheel):
            raise RuntimeError(
                f"{distribution_name} is not installed from a CPython stable-ABI wheel"
            )
    if not qVersion():
        raise RuntimeError("PySide6 Qt runtime did not initialize")


def main() -> int:
    args = arguments()
    if sys.version_info[:2] != (3, 15):
        raise SystemExit("MoHan dependencies must be installed with Python 3.15.")
    requirements = requirement_lines(args.requirements.resolve())
    qt = [item for item in requirements if item.casefold().startswith("pyside6==")]
    remaining = [item for item in requirements if item not in qt]
    if len(qt) != 1:
        raise SystemExit("Expected exactly one pinned PySide6 requirement.")

    if not args.verify_only:
        # Qt 6.11 publishes cp310-abi3 wheels that are technically compatible
        # with CPython 3.15 RC1, but its package metadata still says <3.15.
        # Keep this narrowly scoped exception until upstream metadata catches up.
        subprocess.run(
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "--only-binary=:all:",
                "--ignore-requires-python",
                qt[0],
            ],
            check=True,
        )
        if remaining:
            subprocess.run(
                [sys.executable, "-m", "pip", "install", *remaining],
                check=True,
            )
    verify_qt_stable_abi()
    print("PYTHON315_DEPENDENCIES_AND_QT_STABLE_ABI_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
