from __future__ import annotations

lazy import json
lazy import io
lazy import sys
lazy from contextlib import redirect_stderr
lazy from contextlib import redirect_stdout
lazy import importlib
lazy from pathlib import Path
lazy from tempfile import TemporaryDirectory

lazy import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DENYLIST_EXIT_ERROR_CODE = 2

DENYLIST_TOOL = importlib.import_module("tools.validate_third_party_denylist")


def _write_policy(path: Path, aliases: tuple[str, ...]) -> None:
    payload = {
        "schema": "mohan.third-party-denylist.v1",
        "permanent_denials": [
            {
                "id": "test-scope",
                "aliases": list(aliases),
            }
        ],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _run_tool(
    policy_path: Path,
    candidate_paths: tuple[Path, ...],
    *,
    verify_local_absence: bool = False,
) -> tuple[int, str, str]:
    stdout = io.StringIO()
    stderr = io.StringIO()
    old_policy = DENYLIST_TOOL.POLICY_PATH
    old_load_policy = DENYLIST_TOOL.load_policy
    old_argv = list(DENYLIST_TOOL.sys.argv)

    args = ["validate_third_party_denylist.py"]
    for candidate in candidate_paths:
        args.extend(["--candidate", str(candidate)])
    if verify_local_absence:
        args.append("--verify-local-absence")

    DENYLIST_TOOL.POLICY_PATH = policy_path
    DENYLIST_TOOL.sys.argv = args
    DENYLIST_TOOL.load_policy = lambda path=policy_path: old_load_policy(path)

    try:
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = DENYLIST_TOOL.main()
        return code, stdout.getvalue(), stderr.getvalue()
    finally:
        DENYLIST_TOOL.POLICY_PATH = old_policy
        DENYLIST_TOOL.load_policy = old_load_policy
        DENYLIST_TOOL.sys.argv = old_argv


def _create_candidate(path: Path, text: str) -> Path:
    path.write_text(text + "\n", encoding="utf-8")
    return path


def _scenario_clean_allowlist(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    policy_path = root / "THIRD_PARTY_DENYLIST.json"
    candidate_path = root / "asset-not-denied.txt"

    _write_policy(
        policy_path,
        ("not-denied-item", "another-safe-item"),
    )
    _create_candidate(
        candidate_path,
        "Safe dependency includes: model-a, model-b, renderer",
    )

    code, out, err = _run_tool(policy_path, (candidate_path,))
    assert code == 0
    assert out == "third-party denylist validation passed\n"
    assert err == ""


def _scenario_denied_license_references(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    policy_path = root / "THIRD_PARTY_DENYLIST.json"
    candidate_path = root / "asset-bad-license.txt"

    _write_policy(policy_path, ("cc by-sa", "gpl"))
    _create_candidate(
        candidate_path,
        "Third party dependency note: CC BY-SA and GPL content",
    )

    code, out, err = _run_tool(policy_path, (candidate_path,))
    assert code == DENYLIST_EXIT_ERROR_CODE
    assert "cc by-sa" in err
    assert "gpl" in err
    assert "asset-bad-license.txt" in err
    assert out == ""


def _scenario_ofl_by_entry_type(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    non_font_policy = root / "THIRD_PARTY_DENYLIST.json"
    font_policy = root / "THIRD_PARTY_DENYLIST_FONT.json"
    non_font_candidate = root / "non_font_asset.txt"
    font_candidate = root / "font_asset.txt"

    _write_policy(non_font_policy, ("ofl", "ofl 1.1"))
    _write_policy(font_policy, ("cc by-sa",))
    _create_candidate(
        non_font_candidate,
        "Model asset metadata: OFL (forbidden here)",
    )
    _create_candidate(
        font_candidate,
        "Font package metadata: SIL Open Font License 1.1, OFL",
    )

    failed_code, _, failed_err = _run_tool(
        non_font_policy,
        (non_font_candidate,),
    )
    assert failed_code == DENYLIST_EXIT_ERROR_CODE
    assert "ofl" in failed_err.lower()

    passed_code, passed_out, passed_err = _run_tool(
        font_policy,
        (font_candidate,),
    )
    assert passed_code == 0
    assert passed_out == "third-party denylist validation passed\n"
    assert passed_err == ""


def _scenario_bad_or_missing_policy(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    candidate_path = root / "asset.txt"
    _create_candidate(candidate_path, "Safe content")

    invalid_path = root / "MISSING_THIRD_PARTY_DENYLIST.json"
    with pytest.raises(FileNotFoundError):
        _run_tool(invalid_path, (candidate_path,))

    malformed_path = root / "THIRD_PARTY_DENYLIST_MALFORMED.json"
    malformed_path.write_text(
        json.dumps(
            {
                "schema": "wrong.schema.id",
                "permanent_denials": [],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError):
        _run_tool(malformed_path, (candidate_path,))


def test_allowlist_candidate_passes() -> None:
    with TemporaryDirectory(prefix="mohan-denylist-allowlist-") as raw:
        _scenario_clean_allowlist(Path(raw))


def test_denied_license_references_fail_with_entry_name() -> None:
    with TemporaryDirectory(prefix="mohan-denylist-denied-") as raw:
        _scenario_denied_license_references(Path(raw))


def test_ofl_denied_for_non_font_entry_but_allowed_for_font_entry() -> None:
    with TemporaryDirectory(prefix="mohan-denylist-ofl-") as raw:
        _scenario_ofl_by_entry_type(Path(raw))


def test_bad_or_missing_policy_is_a_clear_error() -> None:
    with TemporaryDirectory(prefix="mohan-denylist-policy-") as raw:
        _scenario_bad_or_missing_policy(Path(raw))


def main() -> int:
    with TemporaryDirectory(prefix="mohan-denylist-validator-") as temp:
        temporary = Path(temp)
        _scenario_clean_allowlist(temporary / "clean")
        _scenario_denied_license_references(temporary / "denied")
        _scenario_ofl_by_entry_type(temporary / "ofl")
        _scenario_bad_or_missing_policy(temporary / "invalid")
    print("THIRD_PARTY_DENYLIST_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
