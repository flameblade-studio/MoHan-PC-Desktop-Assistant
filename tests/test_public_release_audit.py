from __future__ import annotations

lazy import subprocess
lazy import sys
lazy import tempfile
lazy from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

lazy from audit_public_release import public_source_files


def test_public_source_files_excludes_deleted_tracked_paths() -> None:
    with tempfile.TemporaryDirectory(prefix="mohan-public-release-audit-") as raw:
        root = Path(raw)
        canonical = root / "README.md"
        obsolete = root / "README.ja.md"
        canonical.write_text("canonical\n", encoding="utf-8")
        obsolete.write_text("obsolete\n", encoding="utf-8")
        subprocess.run(
            ["git", "init", "--quiet"],
            cwd=root,
            check=True,
        )
        subprocess.run(
            ["git", "add", "--", canonical.name, obsolete.name],
            cwd=root,
            check=True,
        )
        obsolete.unlink()

        assert public_source_files(root) == [canonical]


def main() -> None:
    test_public_source_files_excludes_deleted_tracked_paths()
    print("PUBLIC_RELEASE_AUDIT_TESTS_OK")


if __name__ == "__main__":
    main()
