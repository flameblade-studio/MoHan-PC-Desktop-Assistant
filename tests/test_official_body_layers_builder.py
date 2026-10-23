"""The official splitter keeps native alpha and delegates face weights to runtime."""
from __future__ import annotations

lazy import hashlib
lazy from io import BytesIO
lazy from pathlib import Path
lazy import pytest
lazy import numpy as np
lazy from PIL import Image
lazy from tools import build_official_body_layers as builder


def test_existing_reuse_hash_mismatch_fails_closed(tmp_path: Path) -> None:
    relative = "assets/characters/mohan/body/views/front/hair-back.png"
    source = tmp_path / "hair-back.png"
    source.write_bytes(b"changed layer")
    manifest = {
        "layer_views": {
            "front": {
                "layers": [{"path": relative, "sha256": "0" * 64}],
                "base_hide": {"path": "assets/characters/mohan/body/views/front/base-hide.png"},
            }
        }
    }

    with pytest.raises(ValueError, match="hash"):
        builder._validate_existing_layer_hash(manifest, relative, source)


def test_soft_alpha_is_repainted_even_when_identical_to_bald_base(tmp_path: Path) -> None:
    base = np.zeros((4, 4, 4), dtype=np.uint8)
    base[0, 0] = (100, 80, 60, 120)
    base[1, 1] = (80, 70, 60, 255)
    approved = base.copy()
    approved[1, 1] = (20, 30, 40, 255)
    approved[2, 2] = (10, 20, 30, 80)
    payload = BytesIO()
    Image.fromarray(base).save(payload, format="PNG")

    class Body:
        def load_frame(self, *_args: object, **_options: object) -> bytes:
            return payload.getvalue()

    source = tmp_path / "front-crossed"
    source.mkdir()
    Image.fromarray(approved).save(source / "A.png")
    for name in builder.SOURCE_KINDS.values():
        Image.fromarray(np.zeros_like(base)).save(source / (name + ".png"))
    output = tmp_path / "layers"
    plan, receipt = builder.build_view(Body(), source, output, "front-crossed",
                                       halfbody=True, candidate=False)
    mask = builder.pixels(output / plan["base_hide"]["path"])
    expected_hide = (base[..., 3] > 0) & (approved[..., 3] < builder.OPAQUE_ALPHA)
    assert np.array_equal(mask[..., 3] > 0, expected_hide)
    cleared = base.copy()
    cleared[expected_hide] = 0
    result = Image.fromarray(cleared)
    for record in plan["layers"]:
        path = output / record["path"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == record["sha256"]
        result = Image.alpha_composite(result, Image.open(path))
    assert np.array_equal(np.asarray(result), approved)
    assert receipt["face_core_precleared"] is False
