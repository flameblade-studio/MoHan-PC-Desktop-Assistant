"""Protect authored v2 safe regions from the legacy rig generator."""

from __future__ import annotations

lazy import json
lazy from pathlib import Path

lazy import pytest

lazy from domain.outfit_pack import REQUIRED_SILHOUETTES
lazy from domain.outfit_pack_makeup import SAFE_REGION_SCHEMA_V2
lazy from tools import build_makeup_safe_regions as builder


def _authored_v2_document() -> dict[str, object]:
    return {
        "schema": SAFE_REGION_SCHEMA_V2,
        "silhouettes": {
            silhouette: {
                "canvas": [1254, 1254],
                "rig": "fixture",
                "slots": {"eyes": [], "cheeks": [], "lips": []},
                "foundation_masks": {},
                "eye_aperture_masks": {},
            }
            for silhouette in REQUIRED_SILHOUETTES
        },
    }


def _output(root: Path) -> Path:
    target = root / "assets" / "makeup-safe-regions.json"
    target.parent.mkdir(parents=True)
    return target


def _fail_if_called(_root: Path) -> dict[str, object]:
    raise AssertionError('authored masks require read-only validation')


def test_authored_v2_is_not_overwritten_before_rig_generation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    output = _output(tmp_path)
    original = json.dumps(_authored_v2_document(), ensure_ascii=False, indent=2) + "\n"
    output.write_text(original, encoding="utf-8")

    monkeypatch.setattr(builder, "build_makeup_safe_regions", _fail_if_called)
    assert builder.main(["--root", str(tmp_path), "--output", str(output)]) == 1
    assert output.read_text(encoding="utf-8") == original
    assert "REFUSED_AUTHORED_V2_OVERWRITE" in capsys.readouterr().out


def test_check_validates_authored_v2_without_regeneration(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    output = _output(tmp_path)
    output.write_text(
        json.dumps(_authored_v2_document(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(builder, "build_makeup_safe_regions", _fail_if_called)
    assert builder.main(["--root", str(tmp_path), "--output", str(output), "--check"]) == 0
    assert "VALIDATED_AUTHORED_V2" in capsys.readouterr().out
