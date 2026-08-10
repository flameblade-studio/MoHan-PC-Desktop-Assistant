from __future__ import annotations

lazy import re
lazy import struct
lazy from pathlib import Path

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


def test_workspace_workflow_policy() -> None:
    assert "* @hitoshic1982" in read(".github/CODEOWNERS")
    workflow_dir = ROOT / ".github" / "workflows"
    for workflow_path in workflow_dir.glob("*.yml"):
        workflow = workflow_path.read_text(encoding="utf-8")
        assert 'FORCE_JAVASCRIPT_ACTIONS_TO_NODE24: "true"' in workflow, (
            f"{workflow_path.name} must force the GitHub Actions Node 24 runtime"
        )
        assert "ACTIONS_ALLOW_USE_UNSECURE_NODE_VERSION" not in workflow
        assert 'run: "$MOHAN_JIT_PYTHON"' not in workflow, (
            f"{workflow_path.name} must use a YAML block scalar when invoking "
            "the quoted JIT-runtime path"
        )


def test_security_workflows() -> None:
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
    assert 'python-version: "3.14.7"' in audit
    assert "isolated audit tooling" in audit
    assert "cannot\n      # start on 3.15" in audit


def test_release_supply_chain(release: str) -> None:
    assert_action_pinned(release, "actions/upload-artifact")
    assert_action_pinned(release, "actions/download-artifact")
    assert "actions/attest@1e69f48acb82d1966a394da916b4c1698aa569d6" in release
    assert "cyclonedx-bom==7.3.0" in release
    assert 'PYTHONUTF8: "1"' in release
    assert release.count('python-version: "3.14.7"') == 1
    metadata_job = release.split("\n  metadata:\n", maxsplit=1)[1].split(
        "\n  publish:\n",
        maxsplit=1,
    )[0]
    for required in (
        "id: runtime-python",
        "id: sbom-python",
        "isolated Python 3.14 SBOM tooling runtime",
        "--pyproject pyproject.toml",
        "--pyproject sbom/preview.pyproject.toml",
        "--spec-version 1.7",
        "--output-reproducible",
        "--validate",
        "tools/validate_release_sboms.py",
    ):
        assert required in metadata_job
    for artifact in (
        "*-SBOM-Validation.json",
        "Performance-Evidence.zip",
        "Performance-Summary.json",
    ):
        assert artifact in release
    assert "tools/profile_mohan_tachyon.py" in release
    assert "tools/check_four_language_docs.py" in release
    assert (
        "墨寒桌面助理 $tag／墨寒桌面助手 $tag／"
        "MoHan Desktop Assistant $tag／"
        "墨寒デスクトップアシスタント $tag"
    ) in release
    assert "SHA256" in release


def test_release_runtime_and_packages(release: str) -> None:
    public_audit = read("tools/audit_public_release.py")
    assert "safe.directory={ROOT.as_posix()}" in public_audit
    for required in (
        "tools/audit_public_release.py",
        "tests/run_all.py",
        "tools/install_python315_dependencies.py",
        "tools/build_python315_jit_runtime.py",
        "37e98da7c19a9e5892ee756d6dee08225422cd49",
        "repository: python/cpython",
        'python-version: "3.15.0-rc.1"',
        "PACKAGED_SELFTEST_OK",
        "PACKAGED_JIT_DEFAULT_OK",
        "MOHAN_DISABLE_JIT",
        "PACKAGED_EVENT_LOOP_OK",
        "Build and verify EXE and MSI installers",
        "installer\\build_installers.ps1",
        "installer\\test_installers.ps1",
        "create_release_metadata.py",
        "macOS ${{ matrix.architecture }} limited Preview DMG",
        "macos-15-intel",
        "macos-15",
        "Linux limited Preview AppImage",
    ):
        assert required in release
    assert "--enable-experimental-jit=yes" in read(
        "tools/build_python315_jit_runtime.py"
    )
    assert "sync_wordpress_download_page.py" not in release
    assert "WORDPRESS_APP_PASSWORD" not in release


def test_release_publication_boundary(release: str) -> None:
    for required in (
        "docs/releases/${{ needs.resolve-release.outputs.tag }}.md",
        "git merge-base --is-ancestor",
        "commit: ${{ steps.source.outputs.commit }}",
        "ref: ${{ needs.resolve-release.outputs.commit }}",
        "Release tag changed after validation",
        "Verify existing pre-release without modifying it",
        "Existing Release assets differ from the exact verified set.",
        "github.event_name == 'push' || inputs.publish",
        "metadata:",
        "name: generate-release-metadata",
        "name: Re-verify exact artifact set and SHA256 catalog",
    ):
        assert required in release
    assert 'default: false\n        type: boolean' in release
    publish_job = release.split("\n  publish:\n", maxsplit=1)[1]
    assert "pip install" not in publish_job
    assert "cyclonedx-py" not in publish_job
    assert "sha256sum --check --strict" in publish_job
    assert "client_secret" not in release


def test_release_workflow() -> None:
    release = read(".github/workflows/release.yml")
    test_release_supply_chain(release)
    test_release_runtime_and_packages(release)
    test_release_publication_boundary(release)


def test_preview_and_windows_workflows() -> None:
    preview_packages = read(".github/workflows/preview-packages.yml")
    llvm_setup = read(".github/actions/setup-llvm21/action.yml")
    assert_action_pinned(preview_packages, "actions/upload-artifact")
    for required in (
        "name: Cross-platform Preview package gate",
        "needs: [macos-preview, linux-preview]",
        "if: ${{ always() }}",
        "macos-15-intel",
        "macos-15",
        "tools/build_python315_jit_runtime.py",
        "repository: python/cpython",
        "uses: ./.github/actions/setup-llvm21",
    ):
        assert required in preview_packages
    for required in (
        "https://apt.llvm.org/llvm-snapshot.gpg.key",
        "6084F3CF814B57C1CF12EFD515CF4D18AF4F7421",
        "llvm-toolchain-noble-21",
        "clang-21 llvm-21",
        "LLVM_TOOLS_INSTALL_DIR",
    ):
        assert required in llvm_setup
    assert "llvm.sh" not in llvm_setup
    assert "curl |" not in llvm_setup
    assert " + " not in llvm_setup
    assert "--enable-shared" in read("tools/build_python315_jit_runtime.py")

    windows_ci = read(".github/workflows/windows-ci.yml")
    for required in (
        'PYTHONUTF8: "1"',
        'PYTHON_JIT = "0"',
        'PYTHON_JIT = "1"',
        "tools/benchmark_python315_hotpaths.py",
        "tools/build_python315_jit_runtime.py",
        "tools/profile_mohan_tachyon.py",
        "--target all",
        "--min-samples 100",
        "--max-sample-read-error-percent 15",
        "--max-missed-samples-percent 10",
        "windows-tachyon-evidence",
    ):
        assert required in windows_ci


def test_secret_defense_and_community_files() -> None:
    secret_defense = read(".github/workflows/secret-defense.yml")
    assert_action_pinned(secret_defense, "gitleaks/gitleaks-action")
    assert "fetch-depth: 0" in secret_defense
    release_notes = read(".github/release.yml")
    assert "新功能 / 新功能 / New features / 新機能" in release_notes
    assert "安全性 / 安全性 / Security / セキュリティ" in release_notes
    pr_template = read(".github/pull_request_template.md")
    for heading in ("## 繁體中文", "## 简体中文", "## English", "## 日本語"):
        assert heading in pr_template
    language_guard = read(".github/workflows/pr-language-governance.yml")
    for heading in ("## 繁體中文", "## 简体中文", "## English", "## 日本語"):
        assert heading in language_guard
    for required in (
        "opened, edited, reopened, synchronize, ready_for_review",
        "GITHUB_EVENT_PATH",
        "pull_request.title",
        "IFS='／'",
        "Missing non-empty language section",
        "FOUR_LANGUAGE_PR_METADATA_MINIMUM_OK",
        "tools/check_four_language_pr.py",
        "tools/check_four_language_docs.py",
        'python-version: "3.15.0-rc.1"',
    ):
        assert required in language_guard
    assert "FOUR_LANGUAGE_PR_METADATA_OK" in read(
        "tools/check_four_language_pr.py"
    )
    assert "FOUR_LANGUAGE_DOCUMENTATION_OK" in read(
        "tools/check_four_language_docs.py"
    )
    assert_action_pinned(language_guard, "actions/checkout")
    assert_action_pinned(language_guard, "actions/setup-python")
    assert "pull_request_target" not in language_guard
    assert "github.event.pull_request.body" not in language_guard
    read("ROADMAP.md")
    read("GOVERNANCE.md")

    preview = ROOT / "docs/media/github-social-preview.png"
    assert preview.is_file() and preview.stat().st_size > 100_000
    header = preview.read_bytes()[:24]
    assert header[:8] == b"\x89PNG\r\n\x1a\n"
    assert struct.unpack(">II", header[16:24]) == (1280, 640)


def main() -> None:
    test_workspace_workflow_policy()
    test_security_workflows()
    test_release_workflow()
    test_preview_and_windows_workflows()
    test_secret_defense_and_community_files()
    print("GITHUB_GOVERNANCE_AND_SUPPLY_CHAIN_OK")


if __name__ == "__main__":
    main()
