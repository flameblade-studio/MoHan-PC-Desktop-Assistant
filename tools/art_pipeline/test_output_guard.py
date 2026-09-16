"""Isolated tests for tools/art_pipeline/output_guard.py.

Runs entirely in a temporary sandbox: a fake project root, a fake sealed pin, a
fake stage directory and a fake handoff directory.  Nothing in the real project
is touched.

Covered properties:

  1. a sealed pin is refused and its bytes are untouched
  2. an ``extra_locked`` path is refused even when its name is on the living set
  3. the pin registry is refused by default and only writable with explicit opt-in
  4. ordinary living handoff documents stay writable (the ledger must not dead-lock)
  5. an existing ``.partial`` staging file is never overwritten
  6. an interrupted run leaves no published receipt
  7. a completed run publishes exactly one receipt and no stray partial
  8. strict mode fails loudly on a missing or malformed pin registry
  9. out-of-boundary targets are refused

Usage:
  python test_output_guard.py
"""

from __future__ import annotations

lazy import json
lazy import sys
lazy import tempfile
lazy from pathlib import Path

PROJECT_ROOT = Path(r"D:/FlamebladeStudio/CodexProjects/2026-09-02/mohan-front-layer-repair")
sys.path.insert(0, str(PROJECT_ROOT))

lazy from tools.art_pipeline.output_guard import (  # noqa: E402
    OutputGuard,
    PinRegistryError,
    WriteRefused,
    sha256_file,
)

RESULTS: list[dict] = []
BAD_REGISTRIES = ("missing", "malformed", "no-entries", "entry-without-path")
SEALED_RELATIVE = "scratchpad/sealed/owner-approval.json"


def check(name: str, ok: bool, detail: str = "") -> None:
    RESULTS.append({"check": name, "ok": bool(ok), "detail": detail})
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  ({detail})" if detail else ""))


def make_sandbox(tmp: Path, *, pins: str = "valid") -> tuple[Path, Path, Path]:
    root = tmp / "project"
    handoff = tmp / "handoff"
    stage = root / "scratchpad" / "stage-01"
    sealed = root / SEALED_RELATIVE
    (root / "scratchpad" / "sealed").mkdir(parents=True)
    stage.mkdir(parents=True)
    handoff.mkdir(parents=True)
    sealed.write_bytes(b'{"owner_approved": true, "sealed": "bytes"}\n')

    pins_path = handoff / "SOURCE_PINS.json"
    if pins == "valid":
        pins_path.write_text(json.dumps({
            "schema": "flameblade.source-pins.v1",
            "entries": [{"path": str(sealed), "sha256": sha256_file(sealed), "role": "owner_approval"}],
        }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    elif pins == "malformed":
        pins_path.write_text("{not json", encoding="utf-8")
    elif pins == "no-entries":
        pins_path.write_text(json.dumps({"schema": "flameblade.source-pins.v1"}), encoding="utf-8")
    elif pins == "entry-without-path":
        pins_path.write_text(json.dumps({"schema": "x", "entries": [{"sha256": "ab"}]}), encoding="utf-8")

    for name in ("CURRENT_STATUS.md", "TASKS.json", "config.json"):
        (handoff / name).write_text("original\n", encoding="utf-8")
    return root, handoff, stage


def refusal(fn) -> tuple[bool, str]:
    try:
        fn()
        return False, ""
    except WriteRefused as error:
        return True, error.reason


def _run_receipt(guard_obj: OutputGuard, receipt: Path) -> None:
    with guard_obj.plan_receipt(receipt, lambda state: {"status": "ok"}):
        pass


def case_sealed_pin(guard, sealed: Path, sealed_before: bytes) -> None:
    print("1. sealed pin refused, bytes untouched")
    refused, reason = refusal(lambda: guard().assert_can_write(sealed))
    check("sealed_pin_refused", refused and reason == "source_pin", f"reason={reason}")
    check("sealed_pin_bytes_unchanged", sealed.read_bytes() == sealed_before,
          f"sha={sha256_file(sealed)[:12]}")
    check("pin_count_loaded", guard().loaded_pin_count == 1, f"loaded={guard().loaded_pin_count}")
    alternative = sealed.with_name("owner-approval-deepseek-01.json")
    refused, reason = refusal(lambda: guard().assert_can_write(alternative))
    check("alternative_path_allowed", not refused, reason)


def case_extra_locked(guard, handoff: Path) -> None:
    print("2. extra_locked wins even when the name is a living document")
    for name in ("CURRENT_STATUS.md", "TASKS.json"):
        target = handoff / name
        refused, reason = refusal(
            lambda t=target: guard(extra_locked=[t], create_only=False).assert_can_write(t)
        )
        check(f"extra_locked_wins::{name}", refused and reason == "extra_locked", reason)


def case_pin_registry(guard, pins_path: Path, sealed: Path) -> None:
    print("3. the pin registry is refused by default, allowed only with opt-in")
    refused, reason = refusal(lambda: guard(create_only=False).assert_can_write(pins_path))
    check("pin_registry_refused_by_default", refused and reason == "pin_registry_locked", reason)
    refused, reason = refusal(
        lambda: guard(create_only=False, allow_tracked_updates=True).assert_can_write(pins_path)
    )
    check("pin_registry_allowed_with_optin", not refused, reason)
    refused, reason = refusal(
        lambda: guard(create_only=False, allow_tracked_updates=True).assert_can_write(sealed)
    )
    check("optin_does_not_unlock_sealed_source", refused and reason == "source_pin", reason)


def case_living_documents(guard, handoff: Path) -> None:
    print("4. ordinary living handoff documents stay writable")
    for name in ("CURRENT_STATUS.md", "TASKS.json", "config.json"):
        target = handoff / name
        refused, reason = refusal(lambda t=target: guard(create_only=False).assert_can_write(t))
        check(f"living_document_writable::{name}", not refused, reason)


def case_existing_partial(guard, stage: Path) -> None:
    print("5. an existing .partial is never overwritten")
    partial = stage / "receipt.json.partial"
    partial.write_text("previous interrupted run\n", encoding="utf-8")
    before = partial.read_bytes()
    refused, reason = refusal(lambda: _run_receipt(guard(), stage / "receipt.json"))
    check("existing_partial_refused", refused and reason == "partial_already_exists", reason)
    check("partial_bytes_unchanged", partial.read_bytes() == before,
          f"sha={sha256_file(partial)[:12]}")
    check("no_receipt_from_refused_run", not (stage / "receipt.json").exists())
    partial.unlink()


def case_interrupted(guard, stage: Path) -> None:
    print("6. interrupted run leaves no published receipt")
    raised: list[str] = []

    def interrupted() -> None:
        try:
            with guard().plan_receipt(stage / "receipt-int.json", lambda s: {"status": "ok"}):
                (stage / "derived.rgba.png").write_bytes(b"partial")
                raise RuntimeError("simulated worker failure")
        except RuntimeError as error:
            raised.append(str(error))

    interrupted()
    check("no_receipt_after_failure", not (stage / "receipt-int.json").exists())
    check("no_partial_left_after_failure", not (stage / "receipt-int.json.partial").exists())
    check("failure_propagated", bool(raised), raised[0] if raised else "")


def case_completed(guard, stage: Path) -> None:
    print("7. completed run publishes exactly one receipt")
    good = stage / "receipt-good.json"
    with guard().plan_receipt(good, lambda s: {"status": "ok", "rows": s.get("rows")}) as state:
        state["rows"] = 3
    check("receipt_published_once",
          json.loads(good.read_text(encoding="utf-8")) == {"status": "ok", "rows": 3})
    check("no_partial_after_success", not good.with_name(good.name + ".partial").exists())


def case_strict(tmp: Path) -> None:
    print("8. strict mode fails loudly on a bad registry")
    for label in BAD_REGISTRIES:
        sub = tmp / f"case-{label}"
        sub.mkdir()
        sub_root, sub_handoff, sub_stage = make_sandbox(sub, pins=label)
        try:
            OutputGuard(sub_root, stage_dir=sub_stage, handoff_dir=sub_handoff, strict_pins=True)
            check(f"strict_fails::{label}", False, "guard constructed with a bad registry")
        except PinRegistryError:
            check(f"strict_fails::{label}", True, "PinRegistryError")
        try:
            relaxed = OutputGuard(sub_root, stage_dir=sub_stage, handoff_dir=sub_handoff, strict_pins=False)
            check(f"nonstrict_constructs::{label}", relaxed.loaded_pin_count == 0,
                  f"pins={relaxed.loaded_pin_count}")
        except Exception as error:  # noqa: BLE001
            check(f"nonstrict_constructs::{label}", False, str(error))


def case_boundary(guard, tmp: Path) -> None:
    print("9. out-of-boundary target is refused")
    refused, reason = refusal(lambda: guard().assert_can_write(tmp / "outside" / "escape.json"))
    check("outside_boundary_refused", refused and reason == "outside_allowed_boundary", reason)


def main() -> int:
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        root, handoff, stage = make_sandbox(tmp)
        sealed = root / SEALED_RELATIVE
        pins_path = handoff / "SOURCE_PINS.json"

        def guard(**kwargs) -> OutputGuard:
            return OutputGuard(root, stage_dir=stage, handoff_dir=handoff, **kwargs)

        case_sealed_pin(guard, sealed, sealed.read_bytes())
        case_extra_locked(guard, handoff)
        case_pin_registry(guard, pins_path, sealed)
        case_living_documents(guard, handoff)
        case_existing_partial(guard, stage)
        case_interrupted(guard, stage)
        case_completed(guard, stage)
        case_strict(tmp)
        case_boundary(guard, tmp)

    failures = [r for r in RESULTS if not r["ok"]]
    print()
    print(json.dumps({"checks": len(RESULTS), "failures": len(failures),
                      "failed": [r["check"] for r in failures]}, ensure_ascii=False))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
