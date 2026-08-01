from __future__ import annotations

import struct
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(relative: str) -> str:
    path = ROOT / relative
    assert path.is_file(), f"missing required GitHub file: {relative}"
    return path.read_text(encoding="utf-8")


def main() -> None:
    codeowners = read(".github/CODEOWNERS")
    assert "* @hitoshic1982" in codeowners

    codeql = read(".github/workflows/codeql.yml")
    assert "github/codeql-action/init@v4" in codeql
    assert "github/codeql-action/analyze@v4" in codeql
    assert "security-events: write" in codeql
    assert "pull_request_target" not in codeql

    dependency_review = read(".github/workflows/dependency-review.yml")
    assert "actions/dependency-review-action@v5" in dependency_review
    assert "fail-on-severity: moderate" in dependency_review
    assert "pull_request_target" not in dependency_review

    audit = read(".github/workflows/security-audit.yml")
    assert "pip-audit==2.10.1" in audit
    assert "python -m pip_audit -r requirements.txt --strict" in audit

    release = read(".github/workflows/release.yml")
    assert "actions/upload-artifact@v6" in release
    assert "actions/attest@v4" in release
    assert "cyclonedx-bom==7.3.0" in release
    assert "SHA256" in release
    assert "tools/audit_public_release.py" in release
    assert "tests/run_all.py" in release
    assert "PACKAGED_SELFTEST_OK" in release
    assert "PACKAGED_EVENT_LOOP_OK" in release
    assert "Build EXE and MSI installers" in release
    assert "installer\\build_installers.ps1" in release
    assert "installer\\test_installers.ps1" in release
    assert "create_release_metadata.py" in release
    assert "sync_wordpress_download_page.py" in release
    assert "client_secret" not in release

    secret_defense = read(".github/workflows/secret-defense.yml")
    assert "gitleaks/gitleaks-action@ff98106e" in secret_defense
    assert "fetch-depth: 0" in secret_defense
    release_notes = read(".github/release.yml")
    assert "New features / 新功能" in release_notes
    assert "Security / 安全性" in release_notes

    read("ROADMAP.md")
    read("GOVERNANCE.md")
    preview = ROOT / "docs/media/github-social-preview.png"
    assert preview.is_file() and preview.stat().st_size > 100_000
    header = preview.read_bytes()[:24]
    assert header[:8] == b"\x89PNG\r\n\x1a\n"
    assert struct.unpack(">II", header[16:24]) == (1280, 640)

    print("GITHUB_GOVERNANCE_AND_SUPPLY_CHAIN_OK")


if __name__ == "__main__":
    main()
