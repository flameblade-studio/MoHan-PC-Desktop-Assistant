from __future__ import annotations

import re
import struct
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(relative: str) -> str:
    path = ROOT / relative
    assert path.is_file(), f"missing required GitHub file: {relative}"
    return path.read_text(encoding="utf-8")


def assert_action_pinned(workflow: str, action: str) -> None:
    references = re.findall(
        rf"uses:\s*{re.escape(action)}@([^\s#]+)",
        workflow,
    )
    assert references, f"missing required GitHub Action: {action}"
    assert all(re.fullmatch(r"[0-9a-f]{40}", ref) for ref in references), (
        f"{action} must be pinned to a complete 40-character commit SHA: "
        f"{references}"
    )


def main() -> None:
    codeowners = read(".github/CODEOWNERS")
    assert "* @hitoshic1982" in codeowners

    codeql = read(".github/workflows/codeql.yml")
    assert "github/codeql-action/init@5595ccaf912efad79be6eef63a5619ff05969be3" in codeql
    assert "github/codeql-action/analyze@5595ccaf912efad79be6eef63a5619ff05969be3" in codeql
    assert "security-events: write" in codeql
    assert "pull_request_target" not in codeql

    dependency_review = read(".github/workflows/dependency-review.yml")
    assert "actions/dependency-review-action@a1d282b36b6f3519aa1f3fc636f609c47dddb294" in dependency_review
    assert "fail-on-severity: moderate" in dependency_review
    assert "pull_request_target" not in dependency_review

    audit = read(".github/workflows/security-audit.yml")
    assert "pip-audit==2.10.1" in audit
    assert "python -m pip_audit -r requirements.txt --strict" in audit

    release = read(".github/workflows/release.yml")
    assert_action_pinned(release, "actions/upload-artifact")
    assert_action_pinned(release, "actions/download-artifact")
    assert "actions/attest@1e69f48acb82d1966a394da916b4c1698aa569d6" in release
    assert "cyclonedx-bom==7.3.0" in release
    assert "SHA256" in release
    assert "tools/audit_public_release.py" in release
    assert "tests/run_all.py" in release
    assert "PACKAGED_SELFTEST_OK" in release
    assert "PACKAGED_EVENT_LOOP_OK" in release
    assert "Build and verify EXE and MSI installers" in release
    assert "installer\\build_installers.ps1" in release
    assert "installer\\test_installers.ps1" in release
    assert "create_release_metadata.py" in release
    assert "sync_wordpress_download_page.py" not in release
    assert "WORDPRESS_APP_PASSWORD" not in release
    assert "macOS ${{ matrix.architecture }} limited Preview DMG" in release
    assert "macos-15-intel" in release
    assert "macos-15" in release
    assert "Linux limited Preview AppImage" in release
    assert "docs/releases/${{ needs.resolve-release.outputs.tag }}.md" in release
    assert "git merge-base --is-ancestor" in release
    assert "commit: ${{ steps.source.outputs.commit }}" in release
    assert "ref: ${{ needs.resolve-release.outputs.commit }}" in release
    assert "Release tag changed after validation" in release
    assert "metadata:" in release
    assert "name: generate-release-metadata" in release
    assert "name: Re-verify exact artifact set and SHA256 catalog" in release
    publish_job = release.split("\n  publish:\n", maxsplit=1)[1]
    assert "pip install" not in publish_job
    assert "cyclonedx-py" not in publish_job
    assert "sha256sum --check --strict" in publish_job
    assert "client_secret" not in release

    preview_packages = read(".github/workflows/preview-packages.yml")
    assert_action_pinned(preview_packages, "actions/upload-artifact")
    assert "name: Cross-platform Preview package gate" in preview_packages
    assert "needs: [macos-preview, linux-preview]" in preview_packages
    assert "if: ${{ always() }}" in preview_packages
    assert "macos-15-intel" in preview_packages
    assert "macos-15" in preview_packages

    secret_defense = read(".github/workflows/secret-defense.yml")
    assert_action_pinned(secret_defense, "gitleaks/gitleaks-action")
    assert "fetch-depth: 0" in secret_defense
    release_notes = read(".github/release.yml")
    assert "新功能 / 新功能 / New features / 新機能" in release_notes
    assert "安全性 / 安全性 / Security / セキュリティ" in release_notes
    pr_template = read(".github/pull_request_template.md")
    for heading in ("## 繁體中文", "## 简体中文", "## English", "## 日本語"):
        assert heading in pr_template

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
