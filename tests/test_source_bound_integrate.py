"""Source-bound pack integration stays pinned, atomic, and fail closed."""

from __future__ import annotations

lazy import json
lazy import zipfile
lazy from dataclasses import dataclass
lazy from io import BytesIO
lazy from pathlib import Path

lazy import pytest
lazy from PIL import Image

lazy import tools.art_pipeline.source_bound_integrate as subject
lazy from tools.art_pipeline.source_bound_integrate import (
    APPROVAL_DECISION,
    APPROVAL_SCHEMA,
    ConcurrentTargetChangeError,
    integrate_source_bound_pack,
    integrate_source_bound_packs,
)
lazy from tools.art_pipeline.source_bound_makeup import BUILTIN_PACK_TARGET, apply_makeup_updates
lazy from tools.art_pipeline.source_bound_stage import SCHEMA, digest, rebuild_pack

VIEW = "yaw+060-pitch+00"
PACK_ID = "example"
PACK_TARGET = f"assets/official-packs/{PACK_ID}.mohan-outfit"
MEMBER = f"assets/hanfu-robe-blue-{VIEW}-outerwear.png"
NATIVE = f"assets/pose-atlas/v5-base/{VIEW}.png"
EYE_STATES = ("rest", "half", "closed", "reopened")


@dataclass(frozen=True)
class Fixture:
    root: Path
    candidate: Path
    approval: Path
    output: Path
    target: Path
    baseline_pack: bytes
    candidate_pack: bytes


@dataclass(frozen=True)
class MultiFixture:
    single: Fixture
    makeup_target: Path
    baseline_makeup_pack: bytes
    candidate_makeup_pack: bytes
    makeup_source: Path


def _write(root: Path, relative: str, data: bytes) -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


def _write_json(root: Path, relative: str, value: object) -> tuple[Path, str]:
    data = (json.dumps(value, indent=2) + "\n").encode()
    path = _write(root, relative, data)
    return path, digest(data)


def _png(color: tuple[int, int, int, int], *, grayscale: bool = False) -> bytes:
    stream = BytesIO()
    if grayscale:
        Image.new("L", (2, 2), color[0]).save(stream, format="PNG")
    else:
        Image.new("RGBA", (2, 2), color).save(stream, format="PNG")
    return stream.getvalue()


def _pack(member: bytes) -> bytes:
    manifest = {
        "id": PACK_ID,
        "ensembles": [
            {
                "id": "selected",
                "selections": {
                    "garment": {"item_id": "robe", "variant_id": "blue"},
                },
            }
        ],
        "looks": [
            {
                "id": "robe",
                "variants": [
                    {
                        "id": "blue",
                        "poses": {
                            VIEW: [
                                {
                                    "path": MEMBER,
                                    "sha256": digest(member),
                                    "slot": "outerwear",
                                }
                            ]
                        },
                    }
                ],
            }
        ],
    }
    stream = BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        archive.writestr("manifest.json", json.dumps(manifest, indent=2) + "\n")
        archive.writestr(MEMBER, member)
        archive.writestr("fixed.txt", b"preserved")
    return stream.getvalue()


def _makeup_pack(member: bytes) -> bytes:
    makeup_member = f"assets/mohan-signature-classic-{VIEW}-cheeks.png"
    manifest = {
        "id": "mohan.makeup.builtin",
        "makeup": [{
            "id": "mohan-signature",
            "variants": [{
                "id": "classic",
                "poses": {VIEW: [{
                    "path": makeup_member,
                    "sha256": digest(member),
                    "slot": "cheeks",
                }]},
                "eye_states": {},
            }],
        }],
    }
    stream = BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        archive.writestr("manifest.json", json.dumps(manifest, indent=2) + "\n")
        archive.writestr(makeup_member, member)
        archive.writestr("makeup-metadata.txt", b"preserved")
    return stream.getvalue()


def _reference_binding(root: Path, baseline_manifest: dict, files: list[dict]) -> dict:
    reference_dir = "scratchpad/reference"
    _, input_sha = _write_json(root, f"{reference_dir}/input-manifest.json", baseline_manifest)
    frame_pins = {}
    frame_receipt = {}
    for state in EYE_STATES:
        frame_data = f"reference-{state}".encode()
        frame_path = f"{reference_dir}/{state}.png"
        _write(root, frame_path, frame_data)
        frame_sha = digest(frame_data)
        frame_pins[state] = {"source": frame_path, "target": f"{state}.png", "sha256": frame_sha}
        frame_receipt[state] = {"sha256": frame_sha}
    _, receipt_sha = _write_json(
        root,
        f"{reference_dir}/receipt.json",
        {
            "view_id": VIEW,
            "files": {pin["target"]: pin["sha256"] for pin in files},
            "frames": frame_receipt,
        },
    )
    return {
        "reference_frames": frame_pins,
        "reference_preview": {
            "path": reference_dir,
            "receipt_sha256": receipt_sha,
            "input_manifest_sha256": input_sha,
        },
    }


def _fixture(tmp_path: Path, *, write_approval: bool = True) -> Fixture:
    root = tmp_path
    values = {
        "baseline_member": _png((10, 20, 30, 255)),
        "candidate_member": _png((40, 50, 60, 255)),
        "native_data": b"pinned native authority",
        "source_member": "scratchpad/material/candidate.png",
        "source_mask": "scratchpad/material/allowed-mask.png",
    }
    values["baseline_pack"] = _pack(values["baseline_member"])
    values["candidate_pack"] = rebuild_pack(
        values["baseline_pack"], {MEMBER: values["candidate_member"]}
    )
    values["target"] = _write(root, PACK_TARGET, values["baseline_pack"])
    _write(root, NATIVE, values["native_data"])
    _write(root, values["source_member"], values["candidate_member"])
    _write(root, values["source_mask"], _png((255, 0, 0, 0), grayscale=True))
    values["native_pin"] = {
        "source": NATIVE,
        "target": NATIVE,
        "sha256": digest(values["native_data"]),
    }
    values["files"] = [
        values["native_pin"],
        {
            "source": PACK_TARGET,
            "target": PACK_TARGET,
            "sha256": digest(values["baseline_pack"]),
        },
    ]
    baseline_manifest = {
        "schema": SCHEMA,
        "view_id": VIEW,
        "native": values["native_pin"],
        "pack_id": PACK_ID,
        "ensemble_id": "selected",
        "makeup": "classic",
        "files": values["files"],
        "pack_updates": [],
    }
    manifest = {
        **baseline_manifest,
        "pack_updates": [
            {
                "target": PACK_TARGET,
                "members": [
                    {
                        "source": values["source_member"],
                        "target": MEMBER,
                        "sha256": digest(values["candidate_member"]),
                        "allowed_change_mask": {
                            "source": values["source_mask"],
                            "target": values["source_mask"],
                            "sha256": digest((root / values["source_mask"]).read_bytes()),
                        },
                    }
                ],
            }
        ],
        **_reference_binding(root, baseline_manifest, values["files"]),
    }
    candidate = root / "scratchpad/candidate"
    candidate.mkdir(parents=True)
    _write_json(candidate, "input-manifest.json", manifest)
    _write(candidate, NATIVE, values["native_data"])
    _write(candidate, PACK_TARGET, values["candidate_pack"])
    stage_files = {
        NATIVE: digest(values["native_data"]),
        PACK_TARGET: digest(values["candidate_pack"]),
    }
    shared = {
        "schema": SCHEMA,
        "view_id": VIEW,
        "formal_integrated": False,
        "native_identity": {"passed": True, "native_sha256": digest(values["native_data"])},
        "material_changes": {PACK_TARGET: {MEMBER: {"changed_pixels": 4}}},
        "files": stage_files,
    }
    _write_json(candidate, "stage.json", {**shared, "status": "staged-awaiting-runtime-preview"})
    frame_data = {
        "rest": _png((70, 80, 90, 255)),
        "half": _png((80, 90, 100, 255)),
        "closed": _png((90, 100, 110, 255)),
        "reopened": _png((70, 80, 90, 255)),
    }
    frames = {}
    face_frames = {}
    for state, data in frame_data.items():
        _write(candidate, f"{state}.png", data)
        frames[state] = {"sha256": digest(data), "layer_count": 3}
        face_frames[state] = {"compared_pixels": 4, "changed_pixels": 0}
    receipt_path, receipt_sha = _write_json(
        candidate,
        "receipt.json",
        {
            **shared,
            "status": "scratch-runtime-preview-awaiting-visual-review",
            "owner_visual_approval": "pending",
            "frames": frames,
            "composed_face_identity": {
                "status": "same-state-face-core-identical",
                "frames": face_frames,
            },
        },
    )
    assert receipt_path.is_file()
    regression_path, regression_sha = _write_json(
        root, "scratchpad/regression/report.json", {"status": "passed"}
    )
    approval = root / "scratchpad/approval.json"
    if write_approval:
        _write_json(
            root,
            "scratchpad/approval.json",
            {
                "schema": APPROVAL_SCHEMA,
                "decision": APPROVAL_DECISION,
                "owner_decision_text": "I approve this reviewed candidate for guarded local integration.",
                "candidate_receipt_sha256": receipt_sha,
                "regression": {
                    "report": {
                        "path": regression_path.relative_to(root).as_posix(),
                        "sha256": regression_sha,
                    },
                    "exit_code": 0,
                },
            },
        )
    return Fixture(
        root=root,
        candidate=candidate,
        approval=approval,
        output=root / "scratchpad/integration",
        target=values["target"],
        baseline_pack=values["baseline_pack"],
        candidate_pack=values["candidate_pack"],
    )


def _multi_fixture(tmp_path: Path) -> MultiFixture:
    single = _fixture(tmp_path)
    manifest = json.loads(
        single.candidate.joinpath("input-manifest.json").read_text(encoding="utf-8")
    )
    baseline_makeup_member = _png((30, 40, 50, 255))
    candidate_makeup_member = _png((60, 70, 80, 255))
    baseline_makeup_pack = _makeup_pack(baseline_makeup_member)
    makeup_target = _write(tmp_path, BUILTIN_PACK_TARGET, baseline_makeup_pack)
    makeup_source = _write(
        tmp_path,
        "scratchpad/makeup/candidate.png",
        candidate_makeup_member,
    )
    mask_path = _write(
        tmp_path,
        "scratchpad/makeup/allowed-mask.png",
        _png((255, 0, 0, 0), grayscale=True),
    )
    makeup_pin = {
        "source": BUILTIN_PACK_TARGET,
        "target": BUILTIN_PACK_TARGET,
        "sha256": digest(baseline_makeup_pack),
    }
    manifest["files"].append(makeup_pin)
    manifest["makeup_updates"] = [{
        "source": makeup_source.relative_to(tmp_path).as_posix(),
        "target": f"assets/mohan-signature-classic-{VIEW}-cheeks.png",
        "sha256": digest(candidate_makeup_member),
        "allowed_change_mask": {
            "source": mask_path.relative_to(tmp_path).as_posix(),
            "target": mask_path.relative_to(tmp_path).as_posix(),
            "sha256": digest(mask_path.read_bytes()),
        },
    }]
    baseline_manifest = {
        key: value for key, value in manifest.items()
        if key not in {"reference_frames", "reference_preview", "makeup_updates"}
    }
    baseline_manifest["pack_updates"] = []
    manifest.update(_reference_binding(tmp_path, baseline_manifest, manifest["files"]))
    _write_json(single.candidate, "input-manifest.json", manifest)

    files = {
        NATIVE: (tmp_path / NATIVE).read_bytes(),
        PACK_TARGET: single.baseline_pack,
        BUILTIN_PACK_TARGET: baseline_makeup_pack,
    }
    from tools.art_pipeline.source_bound_stage import apply_pack_updates

    material_changes = apply_pack_updates(tmp_path, manifest, files)
    makeup_changes = apply_makeup_updates(tmp_path, manifest, files)
    candidate_makeup_pack = files[BUILTIN_PACK_TARGET]
    _write(single.candidate, BUILTIN_PACK_TARGET, candidate_makeup_pack)
    shared = {
        "schema": SCHEMA,
        "view_id": VIEW,
        "formal_integrated": False,
        "native_identity": {
            "passed": True,
            "native_sha256": digest((tmp_path / NATIVE).read_bytes()),
        },
        "material_changes": material_changes,
        "makeup_changes": makeup_changes,
        "files": {name: digest(data) for name, data in sorted(files.items())},
    }
    _write_json(
        single.candidate,
        "stage.json",
        {**shared, "status": "staged-awaiting-runtime-preview"},
    )
    original_receipt = json.loads(single.candidate.joinpath("receipt.json").read_text())
    face_frames = {
        state: {
            "compared_pixels": 3,
            "changed_pixels": 0,
            "cosmetic_pixels": 1,
            "cosmetic_changed_pixels": 1,
            "face_alpha_changed_pixels": 0,
        }
        for state in EYE_STATES
    }
    _, receipt_sha = _write_json(
        single.candidate,
        "receipt.json",
        {
            **shared,
            "status": "scratch-runtime-preview-awaiting-visual-review",
            "owner_visual_approval": "pending",
            "frames": original_receipt["frames"],
            "composed_face_identity": {
                "status": "same-state-face-core-identical-outside-authored-makeup",
                "frames": face_frames,
            },
        },
    )
    approval = json.loads(single.approval.read_text(encoding="utf-8"))
    approval["candidate_receipt_sha256"] = receipt_sha
    _write_json(tmp_path, single.approval.relative_to(tmp_path).as_posix(), approval)
    return MultiFixture(
        single=single,
        makeup_target=makeup_target,
        baseline_makeup_pack=baseline_makeup_pack,
        candidate_makeup_pack=candidate_makeup_pack,
        makeup_source=makeup_source,
    )


def test_missing_approval_cannot_change_formal_pack(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path, write_approval=False)
    with pytest.raises(ValueError, match="approval"):
        integrate_source_bound_pack(
            fixture.root,
            fixture.candidate,
            fixture.approval,
            fixture.output,
            postcheck=lambda _context: {},
        )
    assert fixture.target.read_bytes() == fixture.baseline_pack
    assert not fixture.output.exists()


def test_single_outfit_entry_rejects_makeup_pack_changes(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    manifest_path = fixture.candidate / "input-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["makeup_updates"] = [{"target": "assets/official-packs/makeup.mohan-outfit"}]
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match="does not authorize makeup-pack"):
        integrate_source_bound_pack(
            fixture.root, fixture.candidate, fixture.approval, fixture.output,
            postcheck=lambda _context: {},
        )
    assert fixture.target.read_bytes() == fixture.baseline_pack
    assert not fixture.output.exists()


def test_baseline_pin_hash_drift_is_rejected_before_output(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    fixture.target.write_bytes(b"drift")
    with pytest.raises(ValueError, match="Pinned input changed"):
        integrate_source_bound_pack(
            fixture.root,
            fixture.candidate,
            fixture.approval,
            fixture.output,
            postcheck=lambda _context: {},
        )
    assert fixture.target.read_bytes() == b"drift"
    assert not fixture.output.exists()


def test_success_writes_one_pack_and_receipt_last(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)

    def postcheck(context):
        assert context.target.read_bytes() == fixture.candidate_pack
        assert not (context.output / "receipt.json").exists()
        return {"candidate_frames_equal": True}

    receipt = integrate_source_bound_pack(
        fixture.root,
        fixture.candidate,
        fixture.approval,
        fixture.output,
        postcheck=postcheck,
    )
    assert fixture.target.read_bytes() == fixture.candidate_pack
    assert (fixture.output / "backup" / PACK_TARGET).read_bytes() == fixture.baseline_pack
    assert receipt["formal_integrated"] is True
    assert receipt["release"] is False
    assert receipt["postcheck"] == {"candidate_frames_equal": True}
    assert json.loads((fixture.output / "receipt.json").read_text())["change"] == receipt["change"]


def test_failed_postcheck_rolls_back_only_written_pack(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)

    def failing_postcheck(_context):
        raise RuntimeError("synthetic postcheck failure")

    with pytest.raises(RuntimeError, match="synthetic postcheck failure"):
        integrate_source_bound_pack(
            fixture.root,
            fixture.candidate,
            fixture.approval,
            fixture.output,
            postcheck=failing_postcheck,
        )
    assert fixture.target.read_bytes() == fixture.baseline_pack
    assert (fixture.output / "failed-restored.json").is_file()
    assert not (fixture.output / "receipt.json").exists()


def test_concurrent_mutation_is_preserved_instead_of_rolled_back(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)

    def concurrent_failure(context):
        context.target.write_bytes(b"concurrent mutation")
        raise RuntimeError("synthetic postcheck failure after concurrent write")

    with pytest.raises(ConcurrentTargetChangeError, match="preserve and inspect"):
        integrate_source_bound_pack(
            fixture.root,
            fixture.candidate,
            fixture.approval,
            fixture.output,
            postcheck=concurrent_failure,
        )
    assert fixture.target.read_bytes() == b"concurrent mutation"
    assert (fixture.output / "failed-concurrent-change.json").is_file()
    assert not (fixture.output / "failed-restored.json").exists()
    assert not (fixture.output / "receipt.json").exists()


def test_successful_postcheck_mutation_is_detected_and_preserved(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)

    def mutating_postcheck(context):
        context.target.write_bytes(b"concurrent mutation after successful checks")
        return {"synthetic_postcheck": "passed"}

    with pytest.raises(ConcurrentTargetChangeError, match="preserve and inspect"):
        integrate_source_bound_pack(
            fixture.root,
            fixture.candidate,
            fixture.approval,
            fixture.output,
            postcheck=mutating_postcheck,
        )
    assert fixture.target.read_bytes() == b"concurrent mutation after successful checks"
    assert (fixture.output / "failed-concurrent-change.json").is_file()
    assert not (fixture.output / "failed-restored.json").exists()
    assert not (fixture.output / "receipt.json").exists()


def test_candidate_receipt_drift_after_approval_is_rejected_before_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _fixture(tmp_path)
    original_verify_approval = subject._verify_approval

    def verify_then_mutate(*args, **kwargs):
        result = original_verify_approval(*args, **kwargs)
        fixture.candidate.joinpath("receipt.json").write_text("{}\n", encoding="utf-8")
        return result

    monkeypatch.setattr(subject, "_verify_approval", verify_then_mutate)
    with pytest.raises(ValueError, match="Candidate receipt changed during integration preflight"):
        integrate_source_bound_pack(
            fixture.root,
            fixture.candidate,
            fixture.approval,
            fixture.output,
            postcheck=lambda _context: {},
        )
    assert fixture.target.read_bytes() == fixture.baseline_pack
    assert not fixture.output.exists()


def test_stage_clone_cannot_stand_in_for_preview_receipt(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    stage = json.loads(fixture.candidate.joinpath("stage.json").read_text())
    _write_json(fixture.candidate, "receipt.json", stage)

    with pytest.raises(ValueError, match="unintegrated, native-identity-verified preview"):
        integrate_source_bound_pack(
            fixture.root,
            fixture.candidate,
            fixture.approval,
            fixture.output,
            postcheck=lambda _context: {},
        )
    assert fixture.target.read_bytes() == fixture.baseline_pack
    assert not fixture.output.exists()


def test_missing_preview_frame_is_rejected_before_output(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    fixture.candidate.joinpath("half.png").unlink()

    with pytest.raises(ValueError, match="regular file: half"):
        integrate_source_bound_pack(
            fixture.root,
            fixture.candidate,
            fixture.approval,
            fixture.output,
            postcheck=lambda _context: {},
        )
    assert fixture.target.read_bytes() == fixture.baseline_pack
    assert not fixture.output.exists()


def test_preview_frame_sha_mismatch_is_rejected_before_output(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    fixture.candidate.joinpath("half.png").write_bytes(b"changed preview bytes")

    with pytest.raises(ValueError, match="frame SHA-256 changed: half"):
        integrate_source_bound_pack(
            fixture.root,
            fixture.candidate,
            fixture.approval,
            fixture.output,
            postcheck=lambda _context: {},
        )
    assert fixture.target.read_bytes() == fixture.baseline_pack
    assert not fixture.output.exists()


def test_nonzero_face_core_change_is_rejected_before_output(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    receipt_path = fixture.candidate / "receipt.json"
    receipt = json.loads(receipt_path.read_text())
    receipt["composed_face_identity"]["frames"]["closed"]["changed_pixels"] = 1
    _write_json(fixture.candidate, "receipt.json", receipt)

    with pytest.raises(ValueError, match="face core changed in preview: closed"):
        integrate_source_bound_pack(
            fixture.root,
            fixture.candidate,
            fixture.approval,
            fixture.output,
            postcheck=lambda _context: {},
        )
    assert fixture.target.read_bytes() == fixture.baseline_pack
    assert not fixture.output.exists()


def test_postcheck_receipt_drift_rolls_back_without_success_receipt(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)

    def drifting_postcheck(_context):
        fixture.candidate.joinpath("receipt.json").write_text("{}\n", encoding="utf-8")
        return {"synthetic_postcheck": "passed"}

    with pytest.raises(ValueError, match="Candidate receipt drifted during postcheck"):
        integrate_source_bound_pack(
            fixture.root,
            fixture.candidate,
            fixture.approval,
            fixture.output,
            postcheck=drifting_postcheck,
        )
    assert fixture.target.read_bytes() == fixture.baseline_pack
    assert (fixture.output / "failed-restored.json").is_file()
    assert not (fixture.output / "receipt.json").exists()


def test_postcheck_approval_drift_rolls_back_without_success_receipt(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)

    def drifting_postcheck(_context):
        fixture.approval.write_text("{}\n", encoding="utf-8")
        return {"synthetic_postcheck": "passed"}

    with pytest.raises(ValueError, match="Approval drifted during postcheck"):
        integrate_source_bound_pack(
            fixture.root,
            fixture.candidate,
            fixture.approval,
            fixture.output,
            postcheck=drifting_postcheck,
        )
    assert fixture.target.read_bytes() == fixture.baseline_pack
    assert (fixture.output / "failed-restored.json").is_file()
    assert not (fixture.output / "receipt.json").exists()


def test_recovery_preserves_change_between_move_decision_and_move(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _fixture(tmp_path)
    original_replace = subject.os.replace
    concurrent_bytes = b"mutation immediately before quarantine move"

    def mutate_before_quarantine_move(source, target):
        if Path(source) == fixture.target and "quarantine" in Path(target).parts:
            fixture.target.write_bytes(concurrent_bytes)
        return original_replace(source, target)

    monkeypatch.setattr(subject.os, "replace", mutate_before_quarantine_move)

    def failing_postcheck(_context):
        raise RuntimeError("trigger recovery")

    with pytest.raises(ConcurrentTargetChangeError, match="preserve and inspect"):
        integrate_source_bound_pack(
            fixture.root,
            fixture.candidate,
            fixture.approval,
            fixture.output,
            postcheck=failing_postcheck,
        )
    assert fixture.target.read_bytes() == concurrent_bytes
    assert (fixture.output / "failed-concurrent-change.json").is_file()
    assert not (fixture.output / "receipt.json").exists()


def test_multi_pack_success_replaces_both_before_one_postcheck(tmp_path: Path) -> None:
    fixture = _multi_fixture(tmp_path)
    postcheck_calls = 0

    def postcheck(context):
        nonlocal postcheck_calls
        postcheck_calls += 1
        assert context.targets[PACK_TARGET].read_bytes() == fixture.single.candidate_pack
        assert context.targets[BUILTIN_PACK_TARGET].read_bytes() == fixture.candidate_makeup_pack
        assert not (context.output / "receipt.json").exists()
        return {"both_runtime_packs_verified": True}

    receipt = integrate_source_bound_packs(
        fixture.single.root,
        fixture.single.candidate,
        fixture.single.approval,
        fixture.single.output,
        postcheck=postcheck,
    )

    assert postcheck_calls == 1
    assert fixture.single.target.read_bytes() == fixture.single.candidate_pack
    assert fixture.makeup_target.read_bytes() == fixture.candidate_makeup_pack
    assert [change["path"] for change in receipt["changes"]] == [
        PACK_TARGET,
        BUILTIN_PACK_TARGET,
    ]
    assert all(change["backup"].startswith("backup/") for change in receipt["changes"])
    assert receipt["postcheck"] == {"both_runtime_packs_verified": True}
    assert receipt["release"] is False


def test_second_pack_write_failure_restores_first_without_postcheck(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _multi_fixture(tmp_path)
    original_copy = subject._atomic_copy
    postcheck_called = False

    def fail_makeup_write(source: Path, target: Path) -> None:
        if target == fixture.makeup_target:
            raise OSError("synthetic second-pack write failure")
        original_copy(source, target)

    def postcheck(_context):
        nonlocal postcheck_called
        postcheck_called = True
        return {}

    monkeypatch.setattr(subject, "_atomic_copy", fail_makeup_write)
    with pytest.raises(OSError, match="second-pack write failure"):
        integrate_source_bound_packs(
            fixture.single.root,
            fixture.single.candidate,
            fixture.single.approval,
            fixture.single.output,
            postcheck=postcheck,
        )

    assert postcheck_called is False
    assert fixture.single.target.read_bytes() == fixture.single.baseline_pack
    assert fixture.makeup_target.read_bytes() == fixture.baseline_makeup_pack
    assert (fixture.single.output / "failed-transaction.json").is_file()
    assert not (fixture.single.output / "receipt.json").exists()


def test_multi_pack_postcheck_failure_restores_both(tmp_path: Path) -> None:
    fixture = _multi_fixture(tmp_path)

    def failing_postcheck(context):
        assert all(
            context.targets[change["path"]].read_bytes()
            != (context.output / change["backup"]).read_bytes()
            for change in context.changes
        )
        raise RuntimeError("synthetic two-pack postcheck failure")

    with pytest.raises(RuntimeError, match="two-pack postcheck failure"):
        integrate_source_bound_packs(
            fixture.single.root,
            fixture.single.candidate,
            fixture.single.approval,
            fixture.single.output,
            postcheck=failing_postcheck,
        )

    assert fixture.single.target.read_bytes() == fixture.single.baseline_pack
    assert fixture.makeup_target.read_bytes() == fixture.baseline_makeup_pack
    failure = json.loads(
        fixture.single.output.joinpath("failed-transaction.json").read_text()
    )
    assert failure["status"] == "all_written_packs_restored"
    assert {outcome["status"] for outcome in failure["outcomes"]} == {"restored"}
    assert not (fixture.single.output / "receipt.json").exists()


def test_recovery_read_failure_does_not_skip_other_pack_rollback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _multi_fixture(tmp_path)
    original_read = Path.read_bytes
    failed_once = False

    def fail_one_recovery_read(path: Path) -> bytes:
        nonlocal failed_once
        if path == fixture.makeup_target and not failed_once:
            failed_once = True
            raise OSError("synthetic recovery read failure")
        return original_read(path)

    def failing_postcheck(_context):
        monkeypatch.setattr(Path, "read_bytes", fail_one_recovery_read)
        raise RuntimeError("trigger recovery")

    with pytest.raises(RuntimeError, match="rollback is incomplete"):
        integrate_source_bound_packs(
            fixture.single.root,
            fixture.single.candidate,
            fixture.single.approval,
            fixture.single.output,
            postcheck=failing_postcheck,
        )

    assert fixture.single.target.read_bytes() == fixture.single.baseline_pack
    assert fixture.makeup_target.read_bytes() == fixture.candidate_makeup_pack
    failure = json.loads(
        fixture.single.output.joinpath("failed-transaction.json").read_text()
    )
    assert failure["status"] == "rollback_incomplete"
    outcomes = {item["path"]: item["status"] for item in failure["outcomes"]}
    assert outcomes == {PACK_TARGET: "restored", BUILTIN_PACK_TARGET: "recovery_failed"}
    assert not (fixture.single.output / "receipt.json").exists()


def test_multi_pack_concurrent_makeup_change_is_preserved_while_outfit_restores(
    tmp_path: Path,
) -> None:
    fixture = _multi_fixture(tmp_path)
    concurrent = b"concurrent makeup bytes"

    def concurrent_failure(_context):
        fixture.makeup_target.write_bytes(concurrent)
        raise RuntimeError("synthetic failure after concurrent makeup write")

    with pytest.raises(ConcurrentTargetChangeError, match="Concurrent target change preserved"):
        integrate_source_bound_packs(
            fixture.single.root,
            fixture.single.candidate,
            fixture.single.approval,
            fixture.single.output,
            postcheck=concurrent_failure,
        )

    assert fixture.single.target.read_bytes() == fixture.single.baseline_pack
    assert fixture.makeup_target.read_bytes() == concurrent
    assert not (fixture.single.output / "receipt.json").exists()


def test_multi_pack_preserves_change_between_first_and_second_replace(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _multi_fixture(tmp_path)
    original_copy = subject._atomic_copy
    concurrent = b"makeup changed between pack writes"

    def mutate_after_outfit_write(source: Path, target: Path) -> None:
        original_copy(source, target)
        if target == fixture.single.target:
            fixture.makeup_target.write_bytes(concurrent)

    monkeypatch.setattr(subject, "_atomic_copy", mutate_after_outfit_write)
    with pytest.raises(ConcurrentTargetChangeError, match="Concurrent target change preserved"):
        integrate_source_bound_packs(
            fixture.single.root,
            fixture.single.candidate,
            fixture.single.approval,
            fixture.single.output,
            postcheck=lambda _context: {},
        )

    assert fixture.single.target.read_bytes() == fixture.single.baseline_pack
    assert fixture.makeup_target.read_bytes() == concurrent
    assert not (fixture.single.output / "receipt.json").exists()


@pytest.mark.parametrize("drift", ["approval", "source"])
def test_multi_pack_unapproved_or_source_drift_never_writes(
    tmp_path: Path,
    drift: str,
) -> None:
    fixture = _multi_fixture(tmp_path)
    if drift == "approval":
        approval = json.loads(fixture.single.approval.read_text())
        approval["decision"] = "not-approved"
        fixture.single.approval.write_text(json.dumps(approval), encoding="utf-8")
        message = "does not authorize"
    else:
        fixture.makeup_source.write_bytes(b"source drift")
        message = "Pinned input changed"

    with pytest.raises(ValueError, match=message):
        integrate_source_bound_packs(
            fixture.single.root,
            fixture.single.candidate,
            fixture.single.approval,
            fixture.single.output,
            postcheck=lambda _context: {},
        )

    assert fixture.single.target.read_bytes() == fixture.single.baseline_pack
    assert fixture.makeup_target.read_bytes() == fixture.baseline_makeup_pack
    assert not fixture.single.output.exists()


def test_multi_pack_requires_makeup_specific_face_evidence(tmp_path: Path) -> None:
    fixture = _multi_fixture(tmp_path)
    receipt_path = fixture.single.candidate / "receipt.json"
    receipt = json.loads(receipt_path.read_text())
    receipt["composed_face_identity"]["status"] = "same-state-face-core-identical"
    _write_json(fixture.single.candidate, "receipt.json", receipt)

    with pytest.raises(ValueError, match="composed face identity did not pass"):
        integrate_source_bound_packs(
            fixture.single.root,
            fixture.single.candidate,
            fixture.single.approval,
            fixture.single.output,
            postcheck=lambda _context: {},
        )

    assert fixture.single.target.read_bytes() == fixture.single.baseline_pack
    assert fixture.makeup_target.read_bytes() == fixture.baseline_makeup_pack
    assert not fixture.single.output.exists()
