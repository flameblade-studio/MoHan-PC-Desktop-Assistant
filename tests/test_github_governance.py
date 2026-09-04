from __future__ import annotations

lazy import json
lazy import os
lazy import re
lazy import struct
lazy import subprocess
lazy import sys
lazy from pathlib import Path
lazy from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
MIN_PREVIEW_BYTES = 100_000
LANGUAGE_COUNT = 4


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


def assert_external_actions_pinned(workflow: str) -> None:
    references = re.findall(r"(?m)^\s*uses:\s*([^\s#]+)", workflow)
    assert references, "workflow must use at least one GitHub Action"
    unpinned = [
        reference
        for reference in references
        if not reference.startswith("./")
        and not re.fullmatch(r"[^@\s]+@[0-9a-f]{40}", reference)
    ]
    assert not unpinned, (
        "external GitHub Actions must be pinned to complete 40-character "
        f"commit SHAs: {unpinned}"
    )


def _run_pr_checker(payload: dict[str, object]) -> subprocess.CompletedProcess[str]:
    with TemporaryDirectory() as temporary_directory:
        event_path = Path(temporary_directory) / "event.json"
        event_path.write_text(
            json.dumps(payload, ensure_ascii=False),
            encoding="utf-8",
        )
        environment = os.environ.copy()
        environment["GITHUB_EVENT_PATH"] = str(event_path)
        return subprocess.run(
            [sys.executable, str(ROOT / "tools/check_four_language_pr.py")],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
            env=environment,
        )


def _run_dependabot_normalizer(title: str) -> str:
    environment = os.environ.copy()
    environment["PR_TITLE"] = title
    completed = subprocess.run(
        [sys.executable, str(ROOT / "tools/normalize_dependabot_title.py")],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        env=environment,
    )
    assert completed.returncode == 0, completed.stderr
    return completed.stdout.rstrip("\r\n")


def test_pr_language_governance_and_dependabot_normalization() -> None:
    language_guard = read(".github/workflows/pr-language-governance.yml")
    normalizer_workflow = read(
        ".github/workflows/dependabot-title-normalization.yml"
    )
    checker = read("tools/check_four_language_pr.py")
    config = json.loads(read("release-please-config.json"))
    title_pattern = config["pull-request-title-pattern"]

    assert title_pattern == "${version} 發版／发版／Release／リリース"
    assert len(title_pattern.split("／")) == LANGUAGE_COUNT
    assert title_pattern.replace("${version}", "4.5.1") == (
        "4.5.1 發版／发版／Release／リリース"
    )
    assert "${component}" not in title_pattern
    assert "RELEASE_PLEASE_PR_EXEMPT" not in language_guard
    assert "RELEASE_PLEASE_BODY_EXEMPT" in language_guard
    assert "RELEASE_PLEASE_PR_EXEMPT" not in checker
    assert language_guard.index("title=$(jq") < language_guard.index(
        "RELEASE_PLEASE_BODY_EXEMPT"
    )
    assert "pull_request_target:" in normalizer_workflow
    assert (
        "if: ${{ github.event.pull_request.user.login == 'dependabot[bot]' }}"
        in normalizer_workflow
    )
    assert "contents: read\n      pull-requests: write" in normalizer_workflow
    assert "tools/normalize_dependabot_title.py" in normalizer_workflow
    assert 'gh pr edit "$PR_NUMBER"' in normalizer_workflow
    assert '--repo "$GITHUB_REPOSITORY"' in normalizer_workflow
    assert '--title "$normalized_title"' in normalizer_workflow
    assert "bash -c" not in normalizer_workflow
    assert_action_pinned(normalizer_workflow, "actions/checkout")
    assert_action_pinned(normalizer_workflow, "actions/setup-python")

    release_payload = {
        "pull_request": {
            "title": "4.5.1 發版／发版／Release／リリース",
            "body": "",
            "head": {"ref": "release-please--branches--main"},
            "user": {"login": "github-actions[bot]"},
        }
    }
    release_result = _run_pr_checker(release_payload)
    assert release_result.returncode == 0, release_result.stderr
    assert "RELEASE_PLEASE_BODY_EXEMPT" in release_result.stdout

    release_with_invalid_title = {
        **release_payload,
        "pull_request": {
            **release_payload["pull_request"],
            "title": "chore(main): release 4.5.1",
        },
    }
    invalid_release_result = _run_pr_checker(release_with_invalid_title)
    assert invalid_release_result.returncode == 1
    assert "pull-request title" in invalid_release_result.stderr

    dependabot_payload = {
        "pull_request": {
            "title": "更新／更新／Update／更新",
            "body": "",
            "head": {"ref": "dependabot/pip/example-1.2.3"},
            "user": {"login": "dependabot[bot]"},
        }
    }
    dependabot_result = _run_pr_checker(dependabot_payload)
    assert dependabot_result.returncode == 1
    assert "pull-request body" in dependabot_result.stderr

    normalization_cases = (
        (
            "build(deps): bump actions/checkout from 4 to 5",
            "相依套件更新：actions/checkout 4 → 5／"
            "依赖项更新：actions/checkout 4 → 5／"
            "Dependency update: actions/checkout 4 → 5／"
            "依存関係の更新：actions/checkout 4 → 5",
        ),
        (
            "build(deps): bump github/codeql-action/analyze from 4.37.6 to 4.37.9",
            "相依套件更新：github/codeql-action/analyze 4.37.6 → 4.37.9／"
            "依赖项更新：github/codeql-action/analyze 4.37.6 → 4.37.9／"
            "Dependency update: github/codeql-action/analyze 4.37.6 → 4.37.9／"
            "依存関係の更新：github/codeql-action/analyze 4.37.6 → 4.37.9",
        ),
    )
    for source_title, expected_title in normalization_cases:
        normalized_title = _run_dependabot_normalizer(source_title)
        assert normalized_title == expected_title
        assert _run_dependabot_normalizer(normalized_title) == normalized_title

    assert (
        _run_dependabot_normalizer("build(deps): bump actions/checkout four to five")
        == ""
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


def test_funding_configuration() -> None:
    funding = read(".github/FUNDING.yml")
    assert funding == "ko_fi: flamebladestudio\n"
    for retired_support in (
        "buy_me_a_coffee",
        "paypal",
    ):
        assert retired_support not in funding.lower()


def test_security_workflows() -> None:
    codeql = read(".github/workflows/codeql.yml")
    assert "github/codeql-action/init@cdf488f595d80d6e07e03d4674febd5ab45fa938" in codeql
    assert "github/codeql-action/analyze@cdf488f595d80d6e07e03d4674febd5ab45fa938" in codeql
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


def _assert_release_supply_chain(release: str) -> None:
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
    assert not re.search(r"(?m)^\s+python tools/", metadata_job), (
        "release metadata must run project-owned tools with the saved "
        "Python 3.15 runtime instead of the mutable PATH"
    )
    assert "tools/check_four_language_docs.py" not in metadata_job
    for artifact in (
        "*-SBOM-Validation.json",
        "Performance-Evidence.zip",
        "Performance-Summary.json",
    ):
        assert artifact in release
    assert "tools/profile_mohan_tachyon.py" in release
    assert "tools/check_four_language_docs.py" in release
    release_title = (
        "墨寒桌面助理 $tag／墨寒桌面助手 $tag／"
        "MoHan Desktop Assistant $tag／"
        "墨寒デスクトップアシスタント $tag"
    )
    assert f'release_title="{release_title}"' in release
    assert '--title "$release_title"' in release
    publish_job = release.split("\n  publish:\n", maxsplit=1)[1]
    assert "LANG: C.UTF-8" in publish_job
    assert "LC_ALL: C.UTF-8" in publish_job
    assert "\ufffd" not in release_title
    for maturity_label in (
        "正式版",
        "預覽版",
        "预览版",
        "stable release",
        "preview release",
        "正式リリース",
        "プレビュー版",
    ):
        assert maturity_label.casefold() not in release_title.casefold()
    assert "SHA256" in release


def _assert_release_runtime_and_packages(release: str) -> None:
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
    assert "--enable-experimental-jit=yes-off" in read(
        "tools/build_python315_jit_runtime.py"
    )
    assert "sync_wordpress_download_page.py" not in release
    assert "WORDPRESS_APP_PASSWORD" not in release


def _assert_release_publication_boundary(release: str) -> None:
    for required in (
        "docs/releases/$RELEASE_TAG.md",
        "git merge-base --is-ancestor",
        "commit: ${{ steps.source.outputs.commit }}",
        "ref: ${{ needs.resolve-release.outputs.commit }}",
        "Release tag changed after validation",
        "Verify existing release without modifying it",
        "Existing Release assets differ from the exact verified set.",
        "github.event_name == 'push' || github.event_name == 'release' || inputs.publish",
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


def _assert_release_preflight_precedes_packaging(release: str) -> None:
    resolve_job = release.split("\n  resolve-release:\n", maxsplit=1)[1].split(
        "\n  windows:\n",
        maxsplit=1,
    )[0]
    for required in (
        "Validate Release publication mode before packaging",
        "Expected an existing Release for verification before packaging",
        "Release already exists; refusing to rebuild it",
        "Set up Python 3.15 release preflight runtime",
        "id: preflight-python",
        'python-version: "3.15.0-rc.1"',
        "Enforce thin app composition root before packaging",
        '"$PREFLIGHT_PYTHON" tools/check_app_composition_root.py app.py',
        "Validate MoHan Qt 3.15 compatibility policy before packaging",
        '"$PREFLIGHT_PYTHON" tools/check_python315_qt_compatibility.py',
        "Require curated four-language Release notes before packaging",
        "PREFLIGHT_PYTHON: ${{ steps.preflight-python.outputs.python-path }}",
        '"$PREFLIGHT_PYTHON" tools/check_four_language_docs.py',
        "Enforce reproducible v4 OpenAI Vision package gate",
        '"$PREFLIGHT_PYTHON" tools/check_openai_vision_release.py',
    ):
        assert required in resolve_job
    assert "Require audited PoseAtlas release assets" not in resolve_job
    assert "tools/check_pose_atlas_release.py" not in resolve_job
    assert 'python-version: "3.14' not in resolve_job
    assert not re.search(r"(?m)^\s+python tools/", resolve_job)
    assert resolve_job.index("Validate Release publication mode") < (
        resolve_job.index("Set up Python 3.15 release preflight runtime")
    )
    app_preflight = resolve_job.index(
        "Enforce thin app composition root before packaging"
    )
    qt_preflight = resolve_job.index(
        "Validate MoHan Qt 3.15 compatibility policy before packaging"
    )
    assert resolve_job.index("Set up Python 3.15 release preflight runtime") < (
        app_preflight
    )
    assert app_preflight < qt_preflight
    assert qt_preflight < resolve_job.index(
        "Require curated four-language Release notes before packaging"
    )
    assert qt_preflight < resolve_job.index(
        "Enforce reproducible v4 OpenAI Vision package gate"
    )
    assert "--ignore-requires-python" not in resolve_job
    assert "continue-on-error" not in resolve_job


def test_release_workflow() -> None:
    release = read(".github/workflows/release.yml")
    _assert_release_supply_chain(release)
    _assert_release_runtime_and_packages(release)
    _assert_release_publication_boundary(release)
    _assert_release_preflight_precedes_packaging(release)


def test_publishing_merge_policy() -> None:
    publishing = read("PUBLISHING.md")
    for required in (
        "既定合併政策只允許 squash",
        "既定合并策略仅允许 squash",
        "established merge policy only permits squash merging",
        "既定のマージポリシーでは squash マージだけを許可",
        "不得在每次發布時重新查詢",
        "不得在每次发布时重新查询",
        "Do not re-query this known policy for every release",
        "リリースごとにこの既知のポリシーを再照会",
    ):
        assert required in publishing


def test_publishing_github_credential_policy() -> None:
    publishing = read("PUBLISHING.md")
    for required in (
        "一條可預測的憑證路徑",
        "一条可预测的凭证路径",
        "one predictable credential path",
        "予測可能な認証経路を一つだけ使用",
        "在外部狀態未改變前不得反覆重試",
        "在外部状态未变化前不得反复重试",
        "while the external state is unchanged",
        "外部状態が変わらない限り",
    ):
        assert required in publishing


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
    assert_external_actions_pinned(windows_ci)
    pinned_quality_install = (
        "python -m pip install --only-binary=:all: -r requirements-dev.txt"
    )
    for required in (
        'PYTHONUTF8: "1"',
        'PYTHON_JIT = "0"',
        'PYTHON_JIT = "1"',
        "tools/benchmark_python315_hotpaths.py",
        "tools/build_python315_jit_runtime.py",
        "tools/profile_mohan_tachyon.py",
        pinned_quality_install,
        "python -m ruff check .",
        "--target all",
        "--min-samples 100",
        "--max-sample-read-error-percent 15",
        "--max-missed-samples-percent 10",
        "windows-tachyon-evidence",
    ):
        assert required in windows_ci
    assert windows_ci.index(pinned_quality_install) < windows_ci.index(
        "python -m ruff check ."
    )
    release_workflow = read(".github/workflows/release.yml")
    assert_external_actions_pinned(release_workflow)
    assert pinned_quality_install in release_workflow
    assert release_workflow.index(pinned_quality_install) < release_workflow.index(
        "python -m ruff check ."
    )
    quality_requirements = [
        line.strip()
        for line in read("requirements-dev.txt").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    ruff_requirements = [
        requirement
        for requirement in quality_requirements
        if requirement.partition("==")[0].casefold() == "ruff"
    ]
    assert len(ruff_requirements) == 1, (
        "requirements-dev.txt must contain exactly one Ruff requirement"
    )
    assert re.fullmatch(
        r"ruff==[0-9]+(?:\.[0-9]+){2}",
        ruff_requirements[0],
    ), "requirements-dev.txt must pin Ruff to one stable version"
    assert release_workflow.index(
        "Require the release tag to still identify the validated commit"
    ) < release_workflow.index("Attest every published artifact")
    for required in (
        "Existing Release asset size differs",
        "Existing Release asset content differs",
        "Accept: application/octet-stream",
    ):
        assert required in release_workflow


def test_secret_defense_and_community_files() -> None:
    secret_defense = read(".github/workflows/secret-defense.yml")
    # The gitleaks-action wrapper requires a paid license for organization
    # repositories, so the workflow downloads the free gitleaks OSS CLI
    # directly and verifies its SHA-256 checksum before scanning.
    assert_action_pinned(secret_defense, "actions/checkout")
    assert "gitleaks_8.30.1_linux_x64.tar.gz" in secret_defense
    assert (
        "551f6fc83ea457d62a0d98237cbad105af8d557003051f41f3e7ca7b3f2470eb"
        in secret_defense
    )
    assert "./gitleaks detect" in secret_defense
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
        r"title=${title//$'\r'/}",
        r"body=${body//$'\r'/}",
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
    assert preview.is_file() and preview.stat().st_size > MIN_PREVIEW_BYTES
    header = preview.read_bytes()[:24]
    assert header[:8] == b"\x89PNG\r\n\x1a\n"
    assert struct.unpack(">II", header[16:24]) == (1280, 640)


def main() -> None:
    test_workspace_workflow_policy()
    test_pr_language_governance_and_dependabot_normalization()
    test_funding_configuration()
    test_security_workflows()
    test_release_workflow()
    test_publishing_merge_policy()
    test_publishing_github_credential_policy()
    test_preview_and_windows_workflows()
    test_secret_defense_and_community_files()
    print("GITHUB_GOVERNANCE_AND_SUPPLY_CHAIN_OK")


if __name__ == "__main__":
    main()
