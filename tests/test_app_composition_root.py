from __future__ import annotations

lazy import tempfile
lazy from pathlib import Path

lazy from tools.check_app_composition_root import inspect_composition_root

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def inspect_source(source: str):
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "app.py"
        path.write_text(source, encoding="utf-8")
        return inspect_composition_root(path)


def issue_codes(source: str) -> set[str]:
    return {issue.code for issue in inspect_source(source).issues}


def valid_root() -> str:
    return '''from application.application_bootstrap import run_application

__all__ = ("main",)


def main() -> int:
    return run_application()


if __name__ == "__main__":
    raise SystemExit(main())
'''


def test_thin_composition_root_passes() -> None:
    report = inspect_source(valid_root())
    assert report.passed, report.issues
    assert report.physical_lines <= 50


def test_physical_line_limit_is_strict() -> None:
    source = valid_root() + ("\n" * 41)
    report = inspect_source(source)
    assert "physical_line_limit_exceeded" in {issue.code for issue in report.issues}


def test_dashboard_and_companion_window_are_forbidden() -> None:
    source = valid_root().replace(
        'if __name__ == "__main__":',
        "class Dashboard:\n    pass\n\n\nclass CompanionWindow:\n    pass\n\n\nif __name__ == \"__main__\":",
    )
    codes = issue_codes(source)
    assert "dashboard_defined_in_app" in codes
    assert "companion_window_defined_in_app" in codes


def test_business_constants_and_extra_functions_are_forbidden() -> None:
    source = valid_root().replace(
        "__all__ = (\"main\",)",
        '__all__ = ("main",)\nVOICE_PROVIDER = "azure"\n\ndef configure_voice():\n    return None',
    )
    codes = issue_codes(source)
    assert "business_constant_defined_in_app" in codes
    assert "top_level_statement_forbidden" in codes


def test_integration_and_infrastructure_imports_are_forbidden() -> None:
    source = valid_root().replace(
        "from application.application_bootstrap import run_application",
        "from application.application_bootstrap import run_application\nfrom infrastructure.database import Database\nfrom speech_providers import SpeechProvider",
    )
    issues = inspect_source(source).issues
    forbidden = [issue for issue in issues if issue.code == "infrastructure_import_forbidden"]
    assert len(forbidden) == 2
    assert all("must not import" in issue.message for issue in forbidden)


def test_main_must_be_one_argument_free_delegate_call() -> None:
    source = valid_root().replace(
        "    return run_application()",
        "    configured = True\n    return run_application(configured)",
    )
    assert "main_not_thin_delegate" in issue_codes(source)


def test_bootstrap_owner_must_be_explicit() -> None:
    source = valid_root().replace(
        "from application.application_bootstrap import run_application",
        "from helpers import run_application",
    )
    assert "bootstrap_owner_not_explicit" in issue_codes(source)


def test_current_app_satisfies_composition_root_contract() -> None:
    report = inspect_composition_root(PROJECT_ROOT / "app.py")
    evidence = "\n".join(
        f"- {issue.code} (line {issue.line}): {issue.message}"
        for issue in report.issues
    )
    assert report.passed, f"app.py composition-root violations:\n{evidence}"


def run() -> None:
    test_thin_composition_root_passes()
    test_physical_line_limit_is_strict()
    test_dashboard_and_companion_window_are_forbidden()
    test_business_constants_and_extra_functions_are_forbidden()
    test_integration_and_infrastructure_imports_are_forbidden()
    test_main_must_be_one_argument_free_delegate_call()
    test_bootstrap_owner_must_be_explicit()
    test_current_app_satisfies_composition_root_contract()


if __name__ == "__main__":
    run()
