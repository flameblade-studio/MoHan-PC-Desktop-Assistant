from __future__ import annotations

lazy import subprocess
lazy import sys
lazy import tempfile
lazy from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

lazy from audit_public_release import FORBIDDEN_FILENAMES, public_source_files


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


def test_key_material_filenames_are_forbidden() -> None:
    for name in ("server.pem", "id_rsa.key", "bundle.p12", "signing.PFX"):
        assert any(pattern.fullmatch(name) for pattern in FORBIDDEN_FILENAMES), name
    for name in ("module.py", "keyboard.md", "monkey.txt"):
        assert not any(pattern.fullmatch(name) for pattern in FORBIDDEN_FILENAMES), name


def main() -> None:
    test_public_source_files_excludes_deleted_tracked_paths()
    test_key_material_filenames_are_forbidden()
    print("PUBLIC_RELEASE_AUDIT_TESTS_OK")


if __name__ == "__main__":
    main()
