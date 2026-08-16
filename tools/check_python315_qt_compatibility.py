"""Validate the checked-in Python 3.15 Qt compatibility policy."""

from __future__ import annotations

lazy import argparse
lazy import json
lazy import re
lazy from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "tools" / "qt315" / "build-config.toml"
WORKFLOWS = (
    ROOT / ".github" / "workflows" / "cross-platform-core.yml",
    ROOT / ".github" / "workflows" / "preview-packages.yml",
    ROOT / ".github" / "workflows" / "release.yml",
    ROOT / ".github" / "workflows" / "windows-ci.yml",
)
REQUIRED_VALUES = {
    "qt_sdk_version": '"6.11.1"',
    "python_requirement": '">=3.15,<3.16"',
    "wheel_version": '"6.11.1+mohan.py315.1"',
    "wheel_abi": '"cp310-abi3"',
    "official_pypi_metadata_allows_python315": "false",
    "requires_clean_resolver": "true",
    "requires_ignore_requires_python": "false",
}


def _policy_values() -> tuple[bool, tuple[str, ...]]:
    text = POLICY.read_text(encoding="utf-8")
    issues: list[str] = []
    for key, expected in REQUIRED_VALUES.items():
        pattern = rf"(?m)^{re.escape(key)}\s*=\s*{re.escape(expected)}\s*$"
        if re.search(pattern, text) is None:
            issues.append(f"policy:{key}")
    if "pyside_source_commit = \"" not in text:
        issues.append("policy:pyside_source_commit")
    if "[patches.designer_msvc_python_embed]" not in text:
        issues.append("policy:designer_patch")
    return not issues, tuple(issues)


def _workflow_values() -> tuple[bool, tuple[str, ...]]:
    issues: list[str] = []
    for workflow in WORKFLOWS:
        text = workflow.read_text(encoding="utf-8")
        if "build_python315_qt_compat.py" not in text:
            issues.append(f"workflow_missing_builder:{workflow.name}")
        if "--qt-compat-wheelhouse" not in text:
            issues.append(f"workflow_missing_install_flag:{workflow.name}")
        if "--ignore-requires-python" in text:
            issues.append(f"workflow_forbidden_bypass:{workflow.name}")
    return not issues, tuple(issues)


def arguments(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = arguments(argv)
    policy_ok, policy_issues = _policy_values()
    workflow_ok, workflow_issues = _workflow_values()
    issues = policy_issues + workflow_issues
    payload = {
        "status": "passed" if not issues else "blocked",
        "policy": policy_ok,
        "workflows": workflow_ok,
        "issues": list(issues),
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    elif issues:
        print("PYTHON315_QT_COMPATIBILITY_BLOCKED")
        for issue in issues:
            print(f"- {issue}")
    else:
        print("PYTHON315_QT_COMPATIBILITY_POLICY_OK")
    return 0 if not issues else 1


if __name__ == "__main__":
    raise SystemExit(main())
