"""Guarded local integration for owner-approved source-bound appearance packs."""

from __future__ import annotations

lazy import json
lazy import os
lazy import shutil
lazy import uuid
lazy from collections.abc import Callable, Mapping
lazy from dataclasses import dataclass
lazy from pathlib import Path
lazy from typing import Any, TypeAlias

lazy from tools.art_pipeline.source_bound_makeup import BUILTIN_PACK_TARGET, apply_makeup_updates
lazy from tools.art_pipeline.source_bound_reference import verify_reference_binding
lazy from tools.art_pipeline.source_bound_stage import (
    PACK_SUFFIX,
    PinnedFile,
    apply_pack_updates,
    collect_inputs,
    digest,
    read_pinned,
    relative_path,
)

APPROVAL_SCHEMA = "mohan.source-bound-integration-approval.v1"
APPROVAL_DECISION = "accept_selected_pack_for_guarded_local_integration"
INTEGRATION_SCHEMA = "mohan.source-bound-pack-integration.v1"
PREVIEW_STATES = ("rest", "half", "closed", "reopened")


class ConcurrentTargetChangeError(RuntimeError):
    """Raised when a target no longer contains the bytes written by this run."""


@dataclass(frozen=True, slots=True)
class PostcheckContext:
    """Pinned state available to the required post-write validation callback."""

    root: Path
    candidate: Path
    output: Path
    target: Path
    target_relative: str
    before_sha256: str
    after_sha256: str
    manifest: Mapping[str, Any]
    stage: Mapping[str, Any]
    candidate_receipt: Mapping[str, Any]
    approval: Mapping[str, Any]


Postcheck: TypeAlias = Callable[[PostcheckContext], Mapping[str, Any] | None]


@dataclass(frozen=True, slots=True)
class MultiPackPostcheckContext:
    """Pinned state exposed after both formal packs have been replaced."""

    root: Path
    candidate: Path
    output: Path
    targets: Mapping[str, Path]
    changes: tuple[Mapping[str, str], ...]
    manifest: Mapping[str, Any]
    stage: Mapping[str, Any]
    candidate_receipt: Mapping[str, Any]
    approval: Mapping[str, Any]


MultiPackPostcheck: TypeAlias = Callable[
    [MultiPackPostcheckContext], Mapping[str, Any] | None
]


@dataclass(frozen=True, slots=True)
class _IntegrationPlan:
    root: Path
    candidate: Path
    output: Path
    approval_path: Path
    approval: dict[str, Any]
    manifest: dict[str, Any]
    stage: dict[str, Any]
    candidate_receipt: dict[str, Any]
    candidate_receipt_path: Path
    candidate_receipt_sha256: str
    approval_sha256: str
    target: Path
    target_relative: str
    before_sha256: str
    after_sha256: str
    prepared: Path
    backup: Path


@dataclass(frozen=True, slots=True)
class _VerifiedCandidate:
    manifest: dict[str, Any]
    stage: dict[str, Any]
    receipt: dict[str, Any]
    receipt_sha256: str
    rebuilt_packs: Mapping[str, bytes]
    before_sha256: Mapping[str, str]


def _resolve_under(path: Path, parent: Path, label: str) -> Path:
    resolved = path.resolve()
    if not resolved.is_relative_to(parent.resolve()):
        raise ValueError(f"{label} escapes the repository: {resolved}")
    return resolved


def _read_json_payload(path: Path, label: str) -> tuple[dict[str, Any], bytes]:
    if not path.is_file() or path.is_symlink():
        raise ValueError(f"{label} must be a regular file: {path}")
    payload = path.read_bytes()
    value = json.loads(payload.decode("utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{label} must contain a JSON object.")
    return value, payload


def _read_json(path: Path, label: str) -> dict[str, Any]:
    return _read_json_payload(path, label)[0]


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _verify_approval(
    root: Path,
    candidate_receipt_sha256: str,
    approval_path: Path,
) -> tuple[dict[str, Any], str]:
    approval, approval_payload = _read_json_payload(approval_path, "approval")
    if approval.get("schema") != APPROVAL_SCHEMA:
        raise ValueError("Unsupported source-bound integration approval schema.")
    if approval.get("decision") != APPROVAL_DECISION:
        raise ValueError("Approval does not authorize guarded local integration.")
    owner_text = approval.get("owner_decision_text")
    if not isinstance(owner_text, str) or not owner_text.strip():
        raise ValueError("Approval requires the owner's non-empty textual decision.")
    if approval.get("candidate_receipt_sha256") != candidate_receipt_sha256:
        raise ValueError("Approval is not bound to the candidate receipt SHA-256.")
    regression = approval.get("regression")
    if not isinstance(regression, dict) or type(regression.get("exit_code")) is not int:
        raise ValueError("Approval requires an integer regression exit code.")
    if regression["exit_code"] != 0:
        raise ValueError("Approval regression gate is not green.")
    report = regression.get("report")
    if not isinstance(report, dict):
        raise ValueError("Approval requires a SHA-bound regression report.")
    try:
        pin = PinnedFile(report["path"], report["sha256"], "regression-report")
    except (KeyError, TypeError) as error:
        raise ValueError("Approval requires a SHA-bound regression report.") from error
    read_pinned(root, pin)
    return approval, digest(approval_payload)


def _verify_candidate_contract(
    root: Path,
    candidate: Path,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], str, str, bytes, str]:
    verified = _verify_candidate(root, candidate, include_makeup=False)
    target_relative, rebuilt_pack = next(iter(verified.rebuilt_packs.items()))
    return (
        verified.manifest,
        verified.stage,
        verified.receipt,
        verified.receipt_sha256,
        target_relative,
        rebuilt_pack,
        verified.before_sha256[target_relative],
    )


def _verify_candidate(
    root: Path,
    candidate: Path,
    *,
    include_makeup: bool,
) -> _VerifiedCandidate:
    manifest = _read_json(candidate / "input-manifest.json", "candidate input manifest")
    stage = _read_json(candidate / "stage.json", "candidate stage report")
    receipt, receipt_payload = _read_json_payload(candidate / "receipt.json", "candidate receipt")
    makeup_updates = manifest.get("makeup_updates", [])
    if not include_makeup and makeup_updates:
        raise ValueError("Single-outfit integration does not authorize makeup-pack replacements.")
    if len(manifest.get("pack_updates", [])) != 1:
        raise ValueError("Integration requires exactly one selected official pack update.")
    pack_update = manifest["pack_updates"][0]
    target_relative = pack_update.get("target")
    expected_target = f"assets/official-packs/{manifest.get('pack_id')}{PACK_SUFFIX}"
    if target_relative != expected_target:
        raise ValueError("Integration target must be the selected official pack.")
    if include_makeup and (not isinstance(makeup_updates, list) or not makeup_updates):
        raise ValueError("Multi-pack integration requires built-in makeup updates.")

    shared_keys = ["schema", "view_id", "native_identity", "material_changes", "files"]
    if include_makeup:
        shared_keys.append("makeup_changes")
    if any(stage.get(key) != receipt.get(key) for key in shared_keys):
        raise ValueError("Candidate stage report and receipt disagree.")
    if (
        stage.get("status") != "staged-awaiting-runtime-preview"
        or receipt.get("status") != "scratch-runtime-preview-awaiting-visual-review"
        or stage.get("formal_integrated") is not False
        or receipt.get("formal_integrated") is not False
        or stage.get("native_identity", {}).get("passed") is not True
    ):
        raise ValueError("Candidate is not an unintegrated, native-identity-verified preview.")

    files = collect_inputs(root, manifest)
    native = manifest.get("native")
    if not isinstance(native, dict):
        raise ValueError("Source-bound manifest requires native authority.")
    native_pin = PinnedFile(native["source"], native["sha256"], native["target"])
    native_bytes = read_pinned(root, native_pin)
    if native["source"] != native["target"] or files.get(native["target"]) != native_bytes:
        raise ValueError("Native authority is not pinned at its canonical target.")
    verify_reference_binding(root, manifest)
    for provenance in manifest.get("material_provenance", []):
        read_pinned(root, PinnedFile(provenance["path"], provenance["sha256"], "provenance"))

    apply_pack_updates(root, manifest, files)
    if include_makeup:
        apply_makeup_updates(root, manifest, files)
    _verify_preview_receipt(
        candidate,
        receipt,
        makeup_updates_validated=include_makeup,
    )
    _verify_staged_candidate_files(candidate, stage, files)
    target_relatives = (target_relative, BUILTIN_PACK_TARGET) if include_makeup else (target_relative,)
    pins_by_target = {
        pin["target"]: pin["sha256"]
        for pin in manifest["files"]
        if isinstance(pin, dict) and pin.get("target") in target_relatives
    }
    if set(pins_by_target) != set(target_relatives):
        raise ValueError("Integration targets require canonical source-bound baseline pins.")
    return _VerifiedCandidate(
        manifest=manifest,
        stage=stage,
        receipt=receipt,
        receipt_sha256=digest(receipt_payload),
        rebuilt_packs={target: files[target] for target in target_relatives},
        before_sha256=pins_by_target,
    )


def _verify_staged_candidate_files(
    candidate: Path,
    stage: Mapping[str, Any],
    files: Mapping[str, bytes],
) -> None:
    expected_hashes = {name: digest(data) for name, data in sorted(files.items())}
    if stage.get("files") != expected_hashes:
        raise ValueError("Candidate stage file map differs from a fresh source-bound rebuild.")
    for name, expected_bytes in files.items():
        relative_path(name)
        path = candidate / name
        if path.is_symlink() or not path.resolve().is_relative_to(candidate.resolve()):
            raise ValueError(f"Candidate stage file escapes its directory: {name}")
        if path.read_bytes() != expected_bytes:
            raise ValueError(f"Candidate stage file differs from a fresh source-bound rebuild: {name}")


def _verify_preview_receipt(
    candidate: Path,
    receipt: Mapping[str, Any],
    *,
    makeup_updates_validated: bool = False,
) -> None:
    if receipt.get("owner_visual_approval") != "pending":
        raise ValueError("Candidate preview receipt must still await owner visual approval.")
    frames = receipt.get("frames")
    if not isinstance(frames, dict) or set(frames) != set(PREVIEW_STATES):
        raise ValueError("Candidate preview receipt requires exactly four eye-state frames.")
    layer_counts: set[int] = set()
    frame_hashes: dict[str, str] = {}
    for state in PREVIEW_STATES:
        frame = frames[state]
        if not isinstance(frame, dict):
            raise ValueError(f"Candidate preview frame declaration is invalid: {state}")
        layer_count = frame.get("layer_count")
        if type(layer_count) is not int or layer_count <= 0:
            raise ValueError(f"Candidate preview layer count is invalid: {state}")
        layer_counts.add(layer_count)
        frame_path = candidate / f"{state}.png"
        if frame_path.is_symlink():
            raise ValueError(f"Candidate preview frame must be a regular file: {state}")
        frame_path = _resolve_under(frame_path, candidate, "preview frame")
        if not frame_path.is_file():
            raise ValueError(f"Candidate preview frame must be a regular file: {state}")
        actual_sha256 = digest(frame_path.read_bytes())
        if frame.get("sha256") != actual_sha256:
            raise ValueError(f"Candidate preview frame SHA-256 changed: {state}")
        frame_hashes[state] = actual_sha256
    if len(layer_counts) != 1:
        raise ValueError("Candidate preview frames have inconsistent appearance layer counts.")
    if frame_hashes["rest"] != frame_hashes["reopened"]:
        raise ValueError("Candidate reopened preview differs from rest.")

    _verify_face_identity(receipt, makeup_updates_validated=makeup_updates_validated)


def _verify_face_identity(
    receipt: Mapping[str, Any],
    *,
    makeup_updates_validated: bool,
) -> None:

    expected_face_status = (
        "same-state-face-core-identical-outside-authored-makeup"
        if makeup_updates_validated else "same-state-face-core-identical"
    )
    face_identity = receipt.get("composed_face_identity")
    if not isinstance(face_identity, dict) or face_identity.get("status") != expected_face_status:
        raise ValueError("Candidate composed face identity did not pass.")
    face_frames = face_identity.get("frames")
    if not isinstance(face_frames, dict) or set(face_frames) != set(PREVIEW_STATES):
        raise ValueError("Candidate face identity requires exactly four eye-state comparisons.")
    for state in PREVIEW_STATES:
        comparison = face_frames[state]
        if not isinstance(comparison, dict):
            raise ValueError(f"Candidate face identity comparison is invalid: {state}")
        compared = comparison.get("compared_pixels")
        changed = comparison.get("changed_pixels")
        if (
            type(compared) is not int
            or compared <= 0
            or type(changed) is not int
            or changed != 0
        ):
            raise ValueError(f"Candidate face core changed in preview: {state}")
        if makeup_updates_validated and (
            type(comparison.get("face_alpha_changed_pixels")) is not int
            or comparison["face_alpha_changed_pixels"] != 0
            or type(comparison.get("cosmetic_pixels")) is not int
            or comparison["cosmetic_pixels"] <= 0
            or type(comparison.get("cosmetic_changed_pixels")) is not int
            or comparison["cosmetic_changed_pixels"] <= 0
        ):
            raise ValueError(f"Candidate makeup face evidence is invalid: {state}")


def _temporary_sibling(target: Path) -> Path:
    return target.with_name(f".{target.name}.source-bound-{uuid.uuid4().hex}.tmp")


def _atomic_copy(source: Path, target: Path) -> None:
    temporary = _temporary_sibling(target)
    try:
        shutil.copy2(source, temporary)
        os.replace(temporary, target)
    finally:
        if temporary.exists():
            temporary.unlink()


def _copy_without_overwrite(source: Path, target: Path) -> None:
    """Atomically publish a copy only while the target path remains absent."""

    temporary = _temporary_sibling(target)
    try:
        shutil.copy2(source, temporary)
        os.link(temporary, target)
    finally:
        if temporary.exists():
            temporary.unlink()


def _prepare_plan(
    root: Path,
    candidate: Path,
    approval_path: Path,
    output: Path,
) -> _IntegrationPlan:
    root = root.resolve()
    candidate = _resolve_under(candidate, root / "scratchpad", "candidate")
    output = _resolve_under(output, root / "scratchpad", "integration output")
    approval_path = _resolve_under(approval_path, root, "approval")
    if output == (root / "scratchpad").resolve() or output.exists():
        raise FileExistsError(f"Integration output must be a new scratch directory: {output}")
    manifest, stage, receipt, receipt_sha256, target_relative, rebuilt_pack, before_sha256 = (
        _verify_candidate_contract(root, candidate)
    )
    candidate_receipt_path = candidate / "receipt.json"
    approval, approval_sha256 = _verify_approval(root, receipt_sha256, approval_path)
    if digest(candidate_receipt_path.read_bytes()) != receipt_sha256:
        raise ValueError("Candidate receipt changed during integration preflight.")
    target = _resolve_under(root / target_relative, root, "formal pack target")
    if not target.is_file() or target.is_symlink():
        raise ValueError(f"Formal pack target must be a regular file: {target}")
    if digest(target.read_bytes()) != before_sha256:
        raise ValueError("Formal pack target drifted from its source-bound baseline pin.")
    after_sha256 = digest(rebuilt_pack)
    if (candidate / target_relative).read_bytes() != rebuilt_pack:
        raise ValueError("Freshly rebuilt pack does not equal the staged candidate pack.")

    output.mkdir(parents=True, exist_ok=False)
    prepared = output / "prepared" / target_relative
    backup = output / "backup" / target_relative
    prepared.parent.mkdir(parents=True, exist_ok=True)
    backup.parent.mkdir(parents=True, exist_ok=True)
    prepared.write_bytes(rebuilt_pack)
    if digest(prepared.read_bytes()) != after_sha256:
        raise RuntimeError("Prepared pack hash verification failed.")
    shutil.copy2(target, backup)
    if digest(backup.read_bytes()) != before_sha256 or backup.read_bytes() != target.read_bytes():
        raise RuntimeError("Formal pack backup verification failed.")
    plan = _IntegrationPlan(
        root=root,
        candidate=candidate,
        output=output,
        approval_path=approval_path,
        approval=approval,
        manifest=manifest,
        stage=stage,
        candidate_receipt=receipt,
        candidate_receipt_path=candidate_receipt_path,
        candidate_receipt_sha256=receipt_sha256,
        approval_sha256=approval_sha256,
        target=target,
        target_relative=target_relative,
        before_sha256=before_sha256,
        after_sha256=after_sha256,
        prepared=prepared,
        backup=backup,
    )
    _write_json(
        output / "preflight.json",
        {
            "schema": INTEGRATION_SCHEMA,
            "status": "preflight_passed_pending_atomic_replace",
            "formal_integrated": False,
            "release": False,
            "candidate": candidate.relative_to(root).as_posix(),
            "candidate_receipt_sha256": plan.candidate_receipt_sha256,
            "approval": approval_path.relative_to(root).as_posix(),
            "approval_sha256": approval_sha256,
            "owner_decision_text": approval["owner_decision_text"],
            "stage_file_count": len(stage["files"]),
            "change": _change_record(plan),
        },
    )
    return plan


def _prepare_multi_plans(
    root: Path,
    candidate: Path,
    approval_path: Path,
    output: Path,
) -> tuple[_IntegrationPlan, ...]:
    """Finish every two-pack preflight and backup before either formal write."""
    root = root.resolve()
    candidate = _resolve_under(candidate, root / "scratchpad", "candidate")
    output = _resolve_under(output, root / "scratchpad", "integration output")
    approval_path = _resolve_under(approval_path, root, "approval")
    if output == (root / "scratchpad").resolve() or output.exists():
        raise FileExistsError(f"Integration output must be a new scratch directory: {output}")
    verified = _verify_candidate(root, candidate, include_makeup=True)
    candidate_receipt_path = candidate / "receipt.json"
    approval, approval_sha256 = _verify_approval(
        root,
        verified.receipt_sha256,
        approval_path,
    )
    if digest(candidate_receipt_path.read_bytes()) != verified.receipt_sha256:
        raise ValueError("Candidate receipt changed during integration preflight.")

    targets: dict[str, Path] = {}
    for target_relative, before_sha256 in verified.before_sha256.items():
        target = _resolve_under(root / target_relative, root, "formal pack target")
        if not target.is_file() or target.is_symlink():
            raise ValueError(f"Formal pack target must be a regular file: {target}")
        if digest(target.read_bytes()) != before_sha256:
            raise ValueError(f"Formal pack target drifted from its baseline pin: {target_relative}")
        rebuilt_pack = verified.rebuilt_packs[target_relative]
        staged = candidate / target_relative
        if staged.is_symlink() or staged.read_bytes() != rebuilt_pack:
            raise ValueError(
                f"Freshly rebuilt pack does not equal the staged candidate: {target_relative}"
            )
        targets[target_relative] = target

    output.mkdir(parents=True, exist_ok=False)
    plans: list[_IntegrationPlan] = []
    for target_relative, target in targets.items():
        rebuilt_pack = verified.rebuilt_packs[target_relative]
        after_sha256 = digest(rebuilt_pack)
        prepared = output / "prepared" / target_relative
        backup = output / "backup" / target_relative
        prepared.parent.mkdir(parents=True, exist_ok=True)
        backup.parent.mkdir(parents=True, exist_ok=True)
        prepared.write_bytes(rebuilt_pack)
        if digest(prepared.read_bytes()) != after_sha256:
            raise RuntimeError(f"Prepared pack hash verification failed: {target_relative}")
        plans.append(_IntegrationPlan(
            root=root,
            candidate=candidate,
            output=output,
            approval_path=approval_path,
            approval=approval,
            manifest=verified.manifest,
            stage=verified.stage,
            candidate_receipt=verified.receipt,
            candidate_receipt_path=candidate_receipt_path,
            candidate_receipt_sha256=verified.receipt_sha256,
            approval_sha256=approval_sha256,
            target=target,
            target_relative=target_relative,
            before_sha256=verified.before_sha256[target_relative],
            after_sha256=after_sha256,
            prepared=prepared,
            backup=backup,
        ))
    for plan in plans:
        shutil.copy2(plan.target, plan.backup)
        if (
            digest(plan.backup.read_bytes()) != plan.before_sha256
            or plan.backup.read_bytes() != plan.target.read_bytes()
        ):
            raise RuntimeError(f"Formal pack backup verification failed: {plan.target_relative}")
    _write_json(
        output / "preflight.json",
        {
            "schema": INTEGRATION_SCHEMA,
            "status": "preflight_passed_pending_atomic_replace",
            "formal_integrated": False,
            "release": False,
            "candidate": candidate.relative_to(root).as_posix(),
            "candidate_receipt_sha256": verified.receipt_sha256,
            "approval": approval_path.relative_to(root).as_posix(),
            "approval_sha256": approval_sha256,
            "owner_decision_text": approval["owner_decision_text"],
            "stage_file_count": len(verified.stage["files"]),
            "changes": [_change_record(plan) for plan in plans],
        },
    )
    return tuple(plans)


def _change_record(plan: _IntegrationPlan) -> dict[str, str]:
    return {
        "path": plan.target_relative,
        "before_sha256": plan.before_sha256,
        "after_sha256": plan.after_sha256,
        "backup": plan.backup.relative_to(plan.output).as_posix(),
    }


def _postcheck_context(plan: _IntegrationPlan) -> PostcheckContext:
    return PostcheckContext(
        root=plan.root,
        candidate=plan.candidate,
        output=plan.output,
        target=plan.target,
        target_relative=plan.target_relative,
        before_sha256=plan.before_sha256,
        after_sha256=plan.after_sha256,
        manifest=plan.manifest,
        stage=plan.stage,
        candidate_receipt=plan.candidate_receipt,
        approval=plan.approval,
    )


def _multi_postcheck_context(plans: tuple[_IntegrationPlan, ...]) -> MultiPackPostcheckContext:
    first = plans[0]
    return MultiPackPostcheckContext(
        root=first.root,
        candidate=first.candidate,
        output=first.output,
        targets={plan.target_relative: plan.target for plan in plans},
        changes=tuple(_change_record(plan) for plan in plans),
        manifest=first.manifest,
        stage=first.stage,
        candidate_receipt=first.candidate_receipt,
        approval=first.approval,
    )


def _success_receipt(
    plan: _IntegrationPlan,
    postcheck_result: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "schema": INTEGRATION_SCHEMA,
        "status": "guarded_local_integration_complete",
        "formal_integrated": True,
        "release": False,
        "candidate_receipt_sha256": plan.candidate_receipt_sha256,
        "approval": plan.approval_path.relative_to(plan.root).as_posix(),
        "approval_sha256": plan.approval_sha256,
        "owner_decision_text": plan.approval["owner_decision_text"],
        "change": _change_record(plan),
        "postcheck": dict(postcheck_result),
    }


def _multi_success_receipt(
    plans: tuple[_IntegrationPlan, ...],
    postcheck_result: Mapping[str, Any],
) -> dict[str, Any]:
    first = plans[0]
    return {
        "schema": INTEGRATION_SCHEMA,
        "status": "guarded_local_integration_complete",
        "formal_integrated": True,
        "release": False,
        "candidate_receipt_sha256": first.candidate_receipt_sha256,
        "approval": first.approval_path.relative_to(first.root).as_posix(),
        "approval_sha256": first.approval_sha256,
        "owner_decision_text": first.approval["owner_decision_text"],
        "changes": [_change_record(plan) for plan in plans],
        "postcheck": dict(postcheck_result),
    }


def _recover(plan: _IntegrationPlan, error: Exception) -> None:
    quarantine = plan.output / "quarantine" / plan.target_relative
    quarantine.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.replace(plan.target, quarantine)
    except OSError as move_error:
        _write_json(
            plan.output / "failed-concurrent-change.json",
            {
                "schema": INTEGRATION_SCHEMA,
                "status": "concurrent_target_change_preserved",
                "error": str(error),
                "target": plan.target_relative,
                "expected_after_sha256": plan.after_sha256,
                "observed_sha256": (
                    digest(plan.target.read_bytes()) if plan.target.is_file() else None
                ),
                "quarantine": None,
            },
        )
        raise ConcurrentTargetChangeError(
            f"Concurrent target change; preserve and inspect {plan.target}"
        ) from move_error
    moved_sha256 = digest(quarantine.read_bytes())
    restore_source = plan.backup if moved_sha256 == plan.after_sha256 else quarantine
    try:
        _copy_without_overwrite(restore_source, plan.target)
    except FileExistsError as restore_error:
        _write_json(
            plan.output / "failed-concurrent-change.json",
            {
                "schema": INTEGRATION_SCHEMA,
                "status": "concurrent_target_change_preserved",
                "error": str(error),
                "target": plan.target_relative,
                "expected_after_sha256": plan.after_sha256,
                "observed_sha256": digest(plan.target.read_bytes()),
                "quarantine": quarantine.relative_to(plan.output).as_posix(),
                "quarantine_sha256": moved_sha256,
            },
        )
        raise ConcurrentTargetChangeError(
            f"Concurrent target change; preserve and inspect {plan.target}"
        ) from restore_error
    if moved_sha256 != plan.after_sha256:
        _write_json(
            plan.output / "failed-concurrent-change.json",
            {
                "schema": INTEGRATION_SCHEMA,
                "status": "concurrent_target_change_preserved",
                "error": str(error),
                "target": plan.target_relative,
                "expected_after_sha256": plan.after_sha256,
                "observed_sha256": moved_sha256,
                "quarantine": quarantine.relative_to(plan.output).as_posix(),
            },
        )
        raise ConcurrentTargetChangeError(
            f"Concurrent target change; preserve and inspect {plan.target}"
        ) from error
    if digest(plan.target.read_bytes()) != plan.before_sha256:
        raise RuntimeError(f"Rollback verification failed: {plan.target}") from error
    _write_json(
        plan.output / "failed-restored.json",
        {
            "schema": INTEGRATION_SCHEMA,
            "status": "postcheck_failed_formal_pack_restored",
            "error": str(error),
            "restored": plan.target_relative,
            "restored_sha256": plan.before_sha256,
        },
    )


def _recover_multi(plans: tuple[_IntegrationPlan, ...], error: Exception) -> None:
    """Attempt every required rollback while preserving any concurrent bytes."""
    outcomes: list[dict[str, Any]] = []
    concurrent_errors: list[Exception] = []
    recovery_errors: list[Exception] = []
    for plan in reversed(plans):
        try:
            observed = digest(plan.target.read_bytes()) if plan.target.is_file() else None
            if observed == plan.before_sha256:
                outcomes.append({"path": plan.target_relative, "status": "baseline_unchanged"})
                continue
            _recover(plan, error)
        except ConcurrentTargetChangeError as recovery_error:
            concurrent_errors.append(recovery_error)
            outcomes.append({
                "path": plan.target_relative,
                "status": "concurrent_change_preserved",
                "observed_sha256": _read_digest_or_none(plan.target),
            })
        except Exception as recovery_error:
            recovery_errors.append(recovery_error)
            outcomes.append({
                "path": plan.target_relative,
                "status": "recovery_failed",
                "error_type": type(recovery_error).__name__,
                "error": str(recovery_error),
                "observed_sha256": _read_digest_or_none(plan.target),
            })
        else:
            outcomes.append({
                "path": plan.target_relative,
                "status": "restored",
                "restored_sha256": plan.before_sha256,
            })
    first = plans[0]
    status = "all_written_packs_restored"
    if recovery_errors:
        status = "rollback_incomplete"
    elif concurrent_errors:
        status = "concurrent_target_change_preserved"
    _write_json(
        first.output / "failed-transaction.json",
        {
            "schema": INTEGRATION_SCHEMA,
            "status": status,
            "error": str(error),
            "outcomes": list(reversed(outcomes)),
        },
    )
    if recovery_errors:
        raise RuntimeError(
            "Multi-pack rollback is incomplete; inspect the failed transaction evidence."
        ) from recovery_errors[0]
    if concurrent_errors:
        raise ConcurrentTargetChangeError(
            "Concurrent target change preserved while rolling back the multi-pack transaction."
        ) from concurrent_errors[0]


def _read_digest_or_none(path: Path) -> str | None:
    try:
        return digest(path.read_bytes()) if path.is_file() else None
    except OSError:
        return None


def integrate_source_bound_pack(
    root: Path,
    candidate: Path,
    approval_path: Path,
    output: Path,
    *,
    postcheck: Postcheck,
) -> dict[str, Any]:
    """Install one approved pack and roll back a failed postcheck when safe.

    The caller must supply the post-write runtime validation. No approval is
    inferred or generated by this function.
    """

    plan = _prepare_plan(root, candidate, approval_path, output)
    written = False
    try:
        if digest(plan.candidate_receipt_path.read_bytes()) != plan.candidate_receipt_sha256:
            raise ValueError("Candidate receipt drifted immediately before atomic replace.")
        if digest(plan.approval_path.read_bytes()) != plan.approval_sha256:
            raise ValueError("Approval drifted immediately before atomic replace.")
        if digest(plan.target.read_bytes()) != plan.before_sha256:
            raise ValueError("Formal pack target drifted immediately before atomic replace.")
        _atomic_copy(plan.prepared, plan.target)
        written = True
        if digest(plan.target.read_bytes()) != plan.after_sha256:
            raise RuntimeError("Formal pack target write verification failed.")
        postcheck_result = postcheck(_postcheck_context(plan))
        if postcheck_result is None:
            postcheck_result = {}
        if not isinstance(postcheck_result, Mapping):
            raise TypeError("Postcheck must return a mapping or None.")
        if digest(plan.target.read_bytes()) != plan.after_sha256:
            raise ConcurrentTargetChangeError(
                f"Postcheck changed the formal target; preserve and inspect {plan.target}"
            )
        if digest(plan.candidate_receipt_path.read_bytes()) != plan.candidate_receipt_sha256:
            raise ValueError("Candidate receipt drifted during postcheck.")
        if digest(plan.approval_path.read_bytes()) != plan.approval_sha256:
            raise ValueError("Approval drifted during postcheck.")
        receipt = _success_receipt(plan, postcheck_result)
        receipt_temporary = plan.output / ".receipt.json.tmp"
        _write_json(receipt_temporary, receipt)
        os.replace(receipt_temporary, plan.output / "receipt.json")
        return receipt
    except Exception as error:
        if written:
            _recover(plan, error)
        raise


def integrate_source_bound_packs(
    root: Path,
    candidate: Path,
    approval_path: Path,
    output: Path,
    *,
    postcheck: MultiPackPostcheck,
) -> dict[str, Any]:
    """Install one outfit and its built-in makeup candidate as one local transaction."""
    plans = _prepare_multi_plans(root, candidate, approval_path, output)
    replacement_attempted = False
    first = plans[0]
    try:
        if digest(first.candidate_receipt_path.read_bytes()) != first.candidate_receipt_sha256:
            raise ValueError("Candidate receipt drifted immediately before atomic replace.")
        if digest(first.approval_path.read_bytes()) != first.approval_sha256:
            raise ValueError("Approval drifted immediately before atomic replace.")
        for plan in plans:
            if digest(plan.target.read_bytes()) != plan.before_sha256:
                raise ValueError(
                    f"Formal pack target drifted immediately before atomic replace: "
                    f"{plan.target_relative}"
                )
        for plan in plans:
            if digest(plan.target.read_bytes()) != plan.before_sha256:
                raise ConcurrentTargetChangeError(
                    f"Formal pack target changed before its atomic replace: {plan.target}"
                )
            replacement_attempted = True
            _atomic_copy(plan.prepared, plan.target)
            if digest(plan.target.read_bytes()) != plan.after_sha256:
                raise RuntimeError(f"Formal pack target write verification failed: {plan.target_relative}")
        postcheck_result = postcheck(_multi_postcheck_context(plans))
        if postcheck_result is None:
            postcheck_result = {}
        if not isinstance(postcheck_result, Mapping):
            raise TypeError("Postcheck must return a mapping or None.")
        for plan in plans:
            if digest(plan.target.read_bytes()) != plan.after_sha256:
                raise ConcurrentTargetChangeError(
                    f"Postcheck changed a formal target; preserve and inspect {plan.target}"
                )
        if digest(first.candidate_receipt_path.read_bytes()) != first.candidate_receipt_sha256:
            raise ValueError("Candidate receipt drifted during postcheck.")
        if digest(first.approval_path.read_bytes()) != first.approval_sha256:
            raise ValueError("Approval drifted during postcheck.")
        receipt = _multi_success_receipt(plans, postcheck_result)
        receipt_temporary = first.output / ".receipt.json.tmp"
        _write_json(receipt_temporary, receipt)
        os.replace(receipt_temporary, first.output / "receipt.json")
        return receipt
    except Exception as error:
        if replacement_attempted:
            _recover_multi(plans, error)
        raise
