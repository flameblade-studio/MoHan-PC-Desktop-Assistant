"""Regression coverage for closed torso sections and complete decision queues."""
from __future__ import annotations

lazy import importlib
lazy import json
lazy import sys
lazy from pathlib import Path

lazy import numpy as np
import pytest

lazy from tools.second_gen_body.probes import decision_queue

ROOT = Path(__file__).resolve().parents[1]
CANDIDATES = (
    "morph_limbs_candidate4",
    "repose_arms_candidate5",
    "repose_arms_candidate6_dqs",
)


@pytest.fixture
def geometry(monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / "tools/second_gen_body"))
    return importlib.import_module("pose_engine")


def tetrahedron():
    vertices = np.asarray([[0., 0., 0.], [1., 0., 0.], [0., 1., 0.], [0., 0., 1.]])
    faces = np.asarray([[0, 2, 1], [0, 1, 3], [0, 3, 2], [1, 2, 3]])
    return vertices, faces


def section_results(subject, state):
    values = [(official, True) for _, official in subject.TORSO_SECTIONS.values()]
    if state == "missing":
        values[-1] = None
    elif state == "open":
        values[-1] = (values[-1][0], False)
    elif state in {"nan", "inf", "0"}:
        values[-1] = (float(state), True)
    return iter(values + [(1.0, True)] * len(values))


@pytest.mark.parametrize("state", ("missing", "open", "nan", "inf", "0", "closed"))
def test_pose_engine_requires_every_torso_section(geometry, monkeypatch, state):
    vertices, faces = tetrahedron()
    measurements = section_results(geometry, state)
    monkeypatch.setattr(geometry, "plane_loop", lambda *_: next(measurements))
    accepted = geometry.validate(vertices, vertices.copy(), faces, label=state)
    assert bool(accepted) == (state == "closed")


def test_motion_pose_retains_explicit_section_exemption(geometry, monkeypatch):
    vertices, faces = tetrahedron()

    def forbidden_section(*_args):
        raise AssertionError("motion poses explicitly skip torso circumference checks")

    monkeypatch.setattr(geometry, "plane_loop", forbidden_section)
    assert geometry.validate(vertices, vertices.copy(), faces, label="motion", check_sections=False)


def test_plane_loop_distinguishes_missing_open_and_closed(geometry):
    vertices, faces = tetrahedron()
    normal = np.asarray([0., 1., 0.])
    assert geometry.plane_loop(vertices, faces, np.asarray([0., 2., 0.]), normal) is None
    opened = geometry.plane_loop(vertices, faces[:1], np.asarray([0., .5, 0.]), normal)
    closed = geometry.plane_loop(vertices, faces, np.asarray([0., .5, 0.]), normal)
    assert opened is not None and opened[0] > 0 and not opened[1]
    assert closed is not None and closed[0] > 0 and closed[1]


def configure_candidate(subject, monkeypatch, tmp_path):
    vertices, faces = tetrahedron()
    monkeypatch.setattr(subject, "VERTEX_COUNT", len(vertices))
    monkeypatch.setattr(subject, "FACE_COUNT", len(faces))
    monkeypatch.setattr(subject, "load_obj", lambda _path: (vertices.copy(), faces))
    monkeypatch.setattr(subject.np, "loadtxt", lambda *_args, **_kwargs: np.column_stack((np.arange(len(vertices)), vertices)))
    joints = {}
    for side in ("l", "r"):
        for limb in (("uparm", "lowarm", "wrist"), ("upleg", "lowleg", "foot")):
            for index, bone in enumerate(limb):
                joints[f"{side}_{bone}"] = np.asarray([0., 3. - index, 0.])
    monkeypatch.setattr(subject, "load_joints", lambda *_: joints)
    if subject.__name__ == "morph_limbs_candidate4":
        monkeypatch.setattr(subject, "OUT", tmp_path)
        monkeypatch.setattr(subject, "load_part_ids", lambda *_: np.zeros(len(vertices), dtype=np.int32))
        monkeypatch.setattr(subject, "sha256", lambda _path: "synthetic-test-input")
        arguments = [subject.__name__, "--percentile", "25", "--tag", "test"]
    else:
        monkeypatch.setattr(subject, "LIMB", tmp_path)
        monkeypatch.setattr(subject, "load_hierarchy", lambda *_: {})
        monkeypatch.setattr(subject, "load_weights", lambda *_: [{} for _ in vertices])
        arguments = [subject.__name__, "--tag", "test"]
    monkeypatch.setattr(sys, "argv", arguments)


@pytest.mark.parametrize("module_name", CANDIDATES)
@pytest.mark.parametrize("state", ("missing", "open", "nan", "inf", "0", "closed"))
def test_candidate_requires_closed_sections_before_output(geometry, monkeypatch, tmp_path, module_name, state):
    subject = importlib.import_module(module_name)
    configure_candidate(subject, monkeypatch, tmp_path)
    measurements = section_results(subject, state)
    monkeypatch.setattr(subject, "plane_loop", lambda *_: next(measurements))
    if state == "closed":
        subject.main()
        assert list(tmp_path.glob("*.obj"))
        assert list(tmp_path.glob("*.json"))
    else:
        with pytest.raises(SystemExit) as failure:
            subject.main()
        assert failure.value.code != 0
        assert not list(tmp_path.glob("*.obj"))
        assert not list(tmp_path.glob("*.json"))


@pytest.mark.parametrize("index", (0, 20, 40))
@pytest.mark.parametrize("nested", (False, True))
def test_pending_hits_scans_every_array_entry(tmp_path, index, nested):
    entries = [{"status": "ACCEPTED"} for _ in range(41)]
    entries[index] = {"status": "PENDING_REVIEW"}
    data = {"batches": [{"views": entries}]} if nested else entries
    path = tmp_path / "evidence.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    assert decision_queue.pending_hits(path) == ["status=PENDING_REVIEW"]


def test_queue_emits_late_pending_entries_and_honors_final_verdict(tmp_path, monkeypatch):
    root = tmp_path / "artifacts"
    for name in ("pending", "decided"):
        folder = root / name
        folder.mkdir(parents=True)
        data = [{} for _ in range(20)] + [{"status": "PENDING_REVIEW"}]
        (folder / "evidence.json").write_text(json.dumps(data), encoding="utf-8")
    (root / "decided/REPORT.md").write_text("REJECTED", encoding="utf-8")
    output = tmp_path / "queue.tsv"
    monkeypatch.setattr(decision_queue, "ROOT", root)
    monkeypatch.setattr(decision_queue, "OUT", output)
    decision_queue.main()
    rows = output.read_text(encoding="utf-8").splitlines()
    assert rows == ["dir\timage\tstatus", "pending\t\tstatus=PENDING_REVIEW"]
