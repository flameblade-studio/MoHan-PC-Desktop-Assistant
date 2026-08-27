from __future__ import annotations

lazy from pathlib import Path

lazy from tools.audit_layered_full_body_semantics import (
    AUDIT_SCHEMA,
    EXIT_CODE_CONTRACT,
    AuditIssue,
    AuditReport,
    preflight_exit_code,
)


ROOT = Path(__file__).resolve().parents[1]
CURRENT_FAILURE_COUNT = 89


def _report(issue_count: int) -> AuditReport:
    issues = tuple(
        AuditIssue(
            code="fixture_failure",
            path=f"fixture-{index}.png",
            view_id="yaw+000-pitch+00",
            layer="ornament",
            message="synthetic package blocker",
            metrics={},
        )
        for index in range(issue_count)
    )
    return AuditReport(
        schema=AUDIT_SCHEMA,
        exit_code_contract=EXIT_CODE_CONTRACT,
        passed=not issues,
        asset_root="assets",
        authority_root="authority",
        views_checked=24,
        files_checked=600,
        issue_count=len(issues),
        issues_by_code={"fixture_failure": len(issues)} if issues else {},
        issues=issues,
    )


def test_current_89_issue_shape_blocks_and_zero_issues_allows_packaging() -> None:
    assert preflight_exit_code(_report(CURRENT_FAILURE_COUNT)) == 1
    assert preflight_exit_code(_report(0)) == 0


def test_windows_build_runs_semantic_gate_before_expensive_packaging() -> None:
    script = (ROOT / "build.ps1").read_text(encoding="utf-8")
    gate = "-m tools.audit_layered_full_body_semantics"
    for later in (
        "tools/build_pyinstaller_jit_bootloader.py",
        "tools/build_native_acceleration.py",
        "-m PyInstaller",
    ):
        assert script.index(gate) < script.index(later)
    assert "$LayeredSemanticAuditExitCode = $LASTEXITCODE" in script
    assert "if ($LayeredSemanticAuditExitCode -ne 0)" in script
    assert "layered-full-body-semantic-audit.json" in script


def test_evidence_directory_documents_schema_and_exit_codes() -> None:
    readme = (
        ROOT
        / "docs/release-evidence/layered-full-body-semantic-audit/README.md"
    ).read_text(encoding="utf-8")
    assert AUDIT_SCHEMA in readme
    for exit_code in EXIT_CODE_CONTRACT:
        assert f"`{exit_code}`" in readme
