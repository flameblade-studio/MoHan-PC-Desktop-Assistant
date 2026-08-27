from __future__ import annotations

lazy import json
lazy from pathlib import Path

lazy import cv2
lazy import numpy as np

lazy from tools import audit_full_body_layer_pack as audit_mod


def _write(path: Path, image: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    assert cv2.imwrite(str(path), image)


def test_pixel_rules_classify_deterministic_and_rebuild_defects(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(audit_mod, "VIEW_IDS", ("yaw+000-pitch+00",))
    monkeypatch.setattr(audit_mod, "LAYER_NAMES", ("lip_upper", "teeth_tongue"))
    monkeypatch.setattr(audit_mod, "EXPECTED_WH", (8, 8))
    lip = np.zeros((8, 8, 4), dtype=np.uint8)
    lip[3, 3] = (120, 220, 20, 255)  # conspicuous green in BGRA
    lip[0, 0] = (1, 2, 3, 0)         # hidden RGB must be zero
    teeth = np.zeros_like(lip)
    _write(tmp_path / "yaw+000-pitch+00_lip_upper.png", lip)
    _write(tmp_path / "yaw+000-pitch+00_teeth_tongue.png", teeth)
    semantic = tmp_path / "semantic.json"
    semantic.write_text(json.dumps({"issues": []}), encoding="utf-8")

    report, manifest = audit_mod.audit_pack(tmp_path, semantic)
    codes = {(f["classification"], f["code"]) for f in report["findings"]}
    assert ("A", "transparent_rgb_nonzero") in codes
    assert ("A", "lip_green_cyan_contamination") in codes
    assert ("C", "neutral_teeth_empty") in codes
    assert not report["passed"]
    assert not manifest["promotable"]


def test_missing_file_is_fail_closed_class_b(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(audit_mod, "VIEW_IDS", ("yaw+000-pitch+00",))
    monkeypatch.setattr(audit_mod, "LAYER_NAMES", ("body",))
    semantic = tmp_path / "semantic.json"
    semantic.write_text(json.dumps({"issues": []}), encoding="utf-8")
    report, _ = audit_mod.audit_pack(tmp_path, semantic)
    assert report["exit_code"] == 1
    assert report["findings"][0]["classification"] == "B"
    assert report["findings"][0]["code"] == "missing_file"


def test_semantic_teeth_issue_is_class_c_not_rebuild(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(audit_mod, "VIEW_IDS", ())
    semantic = tmp_path / "semantic.json"
    semantic.write_text(json.dumps({"issues": [{
        "code": "teeth_tongue_all_views_empty", "view_id": "yaw+000-pitch+00",
        "layer": "teeth_tongue", "path": "teeth.png", "metrics": {},
    }]}), encoding="utf-8")
    report, manifest = audit_mod.audit_pack(tmp_path, semantic)
    assert report["passed"]
    assert len(manifest["classes"]["C"]["actions"]) == 1
