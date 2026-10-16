"""Coverage verifies export evidence; source labels retain descriptive scope."""

lazy import hashlib
lazy import json

lazy import pytest

lazy from domain.character_pose import CANONICAL_YAWS
lazy from tests.test_consolidate_partitions import make_batch
lazy from tools.art_pipeline.partition_coverage import partition_coverage
lazy from tools.art_pipeline.reviewed_partitions import integrate_batch


def test_verified_partial_counts_missing_views_without_promoting(tmp_path):
    manifest, batch = make_batch(tmp_path / "input", "visible_shorts")
    before = {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    result = partition_coverage(manifest, batch)
    assert result["visible_components"] == result["source_identifiers"] == 1
    assert result["yaw_source_identifiers_present"] == ["yaw-165"]
    assert len(result["yaw_source_identifiers_missing"]) == len(CANONICAL_YAWS) - 1
    assert result["entries"][0]["missing_visible_roles"] == [
        "visible_core_hair", "visible_left_hand", "visible_right_hand", "visible_upper_garment",
    ]
    assert all(result[key] is False for key in (
        "complete_24_600", "production_runtime_ready", "hidden_body_complete",
        "exact_yaw_calibrated",
    ))
    assert before == {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}


def test_halfbody_pose_is_not_counted_as_yaw(tmp_path):
    manifest, _ = make_batch(tmp_path / "input", "visible_core_hair")
    spec = json.loads(manifest.read_text(encoding="utf-8"))
    spec["entries"][0]["id"] = "front-eureka"
    other = manifest.with_name("halfbody.json")
    other.write_text(json.dumps(spec), encoding="utf-8")
    batch = tmp_path / "halfbody"
    integrate_batch(other, batch)
    result = partition_coverage(other, batch)
    assert result["other_source_identifiers"] == ["front-eureka"]
    assert result["yaw_source_identifiers_present"] == []
    assert len(result["yaw_source_identifiers_missing"]) == len(CANONICAL_YAWS)


@pytest.mark.parametrize("failure", ["receipt_missing", "pixels_changed", "duplicate_id"])
def test_bad_exports_cannot_produce_coverage(tmp_path, failure):
    manifest, batch = make_batch(tmp_path / "input", "visible_shorts")
    receipt_path = batch / "receipt.json"
    if failure == "receipt_missing":
        receipt_path.unlink()
    elif failure == "pixels_changed":
        (batch / "yaw-165/visible_shorts.png").write_bytes(b"invalid PNG")
    else:
        spec = json.loads(manifest.read_text(encoding="utf-8"))
        spec["entries"] *= 2
        manifest.write_text(json.dumps(spec), encoding="utf-8")
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        receipt["entries"] *= 2
        receipt["manifest_sha256"] = hashlib.sha256(manifest.read_bytes()).hexdigest()
        receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
    with pytest.raises((ValueError, OSError)):
        partition_coverage(manifest, batch)
