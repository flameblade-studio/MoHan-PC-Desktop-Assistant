"""Gate the half-body v2 rig builder and its v120 derivation end to end.

The builder runs once into a temporary directory on the three new authority
portraits and the outputs are held to the SAME numbers the runtime gates use:
``tests/test_layered_face_assets.py`` (4-px sampled reconstruction, mean
max-channel error < 6, transparent ratio < 1 %) and
``infrastructure.layered_face_calibration`` (18 facial layers non-empty,
centre escape from ``base`` <= 1 px), plus exclusive ownership and zeroed
transparent RGB.

Inputs: ``MOHAN_HALF_BODY_V2_PORTRAIT_DIR`` names the directory holding the
new ``idle.png`` / ``idle_lean.png`` / ``idle_front.png`` (default
``work/half-body-v2/authority``, an untracked staging directory).  When those
files are absent the builder runs on the shipped ``assets/expressions``
portraits instead (identity alignment) so every invariant is still exercised
on a clean checkout; ``run()`` prints which source was used.
"""

from __future__ import annotations

lazy import os
lazy import sys
lazy import tempfile
lazy from pathlib import Path

lazy import numpy as np
lazy from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
TESTS_DIR = Path(__file__).resolve().parent
for entry in (ROOT, ROOT / "tools", TESTS_DIR):
    if str(entry) not in sys.path:
        sys.path.insert(0, str(entry))

lazy from build_half_body_layered_rig import (
    AUTO_EMPTY_LAYERS,
    CANVAS,
    DEFAULT_EMPTY_LAYERS,
    LAYERS,
    POSES,
    build,
)
lazy from build_half_body_v120 import (
    FEATHER_ALPHA_THRESHOLD,
    MIN_FEATHER_PIXELS,
    MIN_VISIBLE_PIXELS,
    V120_LAYERS,
)
lazy from build_half_body_v120 import POSES as V120_POSES
lazy from build_half_body_v120 import build as build_v120
lazy from infrastructure.layered_face_assets import (
    LAYERED_FACE_DIMENSION,
    load_layered_face_assets,
)
lazy from infrastructure.layered_face_calibration import (
    FACIAL_LAYERS,
    MAX_ANCHOR_DRIFT_PIXELS,
    LayerAnchor,
    _center_escape,
)
lazy from test_layered_face_assets import (
    IDENTITY_SAMPLE_STEP,
    MAX_MEAN_CHANNEL_ERROR,
    MAX_TRANSPARENT_SAMPLE_RATIO,
)

EXPECTED_RIG_FILES = 75
EXPECTED_V120_FILES = 21
DEFAULT_PORTRAIT_DIR = ROOT / "work" / "half-body-v2" / "authority"
SHIPPED_PORTRAIT_DIR = ROOT / "assets" / "expressions"

_BUILT: dict[str, object] = {}


def _portrait_dir() -> tuple[Path, str]:
    candidate = Path(
        os.environ.get("MOHAN_HALF_BODY_V2_PORTRAIT_DIR") or DEFAULT_PORTRAIT_DIR
    )
    if all((candidate / filename).is_file() for _pose, filename in POSES):
        return candidate, "half-body-v2 portraits"
    return SHIPPED_PORTRAIT_DIR, "shipped portraits (fallback: staging dir absent)"


def _built() -> dict[str, object]:
    """Build rig + v120 once per process into a temporary directory."""
    if not _BUILT:
        portrait_dir, source = _portrait_dir()
        temp = tempfile.TemporaryDirectory(prefix="half-body-v2-rig-")
        root = Path(temp.name)
        rig_dir = root / "layered"
        v120_dir = root / "v120"
        _BUILT.update(
            temp=temp,
            portrait_dir=portrait_dir,
            source=source,
            rig_dir=rig_dir,
            v120_dir=v120_dir,
            report=build(portrait_dir, rig_dir),
            v120_report=build_v120(portrait_dir, rig_dir, v120_dir),
        )
    return _BUILT


def _rgba(path: Path) -> np.ndarray:
    return np.asarray(Image.open(path).convert("RGBA"), dtype=np.uint8)


def _anchor(mask: np.ndarray) -> LayerAnchor | None:
    ys, xs = np.nonzero(mask)
    if not xs.size:
        return None
    return LayerAnchor(int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1)


def _pose_layers(pose: str) -> dict[str, np.ndarray]:
    rig_dir = _built()["rig_dir"]
    return {layer: _rgba(rig_dir / f"{pose}_{layer}.png") for layer in LAYERS}


def _sampled_identity_error(
    composite: np.ndarray,
    authority: np.ndarray,
) -> tuple[float, float]:
    """Same sampling as tests/test_layered_face_assets._sampled_identity_error."""
    step = IDENTITY_SAMPLE_STEP
    expected = authority[::step, ::step].astype(np.int16)
    actual = composite[::step, ::step].astype(np.int16)
    opaque = expected[:, :, 3] > 0
    differences = np.abs(actual - expected).max(axis=2)[opaque]
    transparent = actual[:, :, 3][opaque] == 0
    return float(differences.mean()), float(transparent.mean())


def test_builder_writes_seventy_five_layers_at_canvas_size() -> None:
    built = _built()
    rig_dir = built["rig_dir"]
    files = sorted(rig_dir.glob("*.png"))
    assert len(files) == EXPECTED_RIG_FILES, len(files)
    assert built["report"]["files"] == EXPECTED_RIG_FILES
    assert CANVAS == LAYERED_FACE_DIMENSION
    # The runtime loader validates every name and the 1254² header itself.
    manifest = load_layered_face_assets(rig_dir)
    assert len(manifest.poses) == len(POSES)


def test_facial_layers_are_non_empty_and_anchored_to_base() -> None:
    for pose, _filename in POSES:
        layers = _pose_layers(pose)
        base = _anchor(layers["base"][:, :, 3] > 0)
        assert base is not None, pose
        for layer in FACIAL_LAYERS:
            anchor = _anchor(layers[layer][:, :, 3] > 0)
            assert anchor is not None, f"{pose}_{layer} is empty"
            escape = _center_escape(base, anchor)
            assert escape <= MAX_ANCHOR_DRIFT_PIXELS, (pose, layer, escape)


def test_exclusive_ownership_and_zero_transparent_rgb() -> None:
    portrait_dir = _built()["portrait_dir"]
    for pose, filename in POSES:
        layers = _pose_layers(pose)
        owners = np.zeros((CANVAS, CANVAS), np.uint8)
        for layer, array in layers.items():
            visible = array[:, :, 3] > 0
            owners += visible
            assert not array[~visible, :3].any(), f"{pose}_{layer} transparent RGB != 0"
        foreground = _rgba(portrait_dir / filename)[:, :, 3] > 0
        assert int((owners > 1).sum()) == 0, f"{pose}: pixels owned twice"
        assert int((foreground & (owners == 0)).sum()) == 0, f"{pose}: unowned pixels"
        assert int((~foreground & (owners > 0)).sum()) == 0, f"{pose}: owned outside"


def test_neutral_composite_reconstructs_authority() -> None:
    portrait_dir = _built()["portrait_dir"]
    for pose, filename in POSES:
        authority = _rgba(portrait_dir / filename)
        layers = _pose_layers(pose)
        composite = np.zeros_like(authority)
        for layer in LAYERS:  # bottom-to-top Z-order, exclusive cutouts
            array = layers[layer]
            visible = array[:, :, 3] > 0
            composite[visible] = array[visible]
        mean_error, transparent_ratio = _sampled_identity_error(composite, authority)
        assert mean_error < MAX_MEAN_CHANNEL_ERROR, (pose, mean_error)
        assert transparent_ratio < MAX_TRANSPARENT_SAMPLE_RATIO, (pose, transparent_ratio)


def test_report_declares_empty_layers_and_alignment_evidence() -> None:
    report = _built()["report"]
    for pose_report in report["poses"]:
        assert set(DEFAULT_EMPTY_LAYERS) <= set(pose_report["empty_layers"])
        for layer in pose_report["empty_layers"]:
            assert pose_report["layer_pixels"][layer] == 0, (pose_report["pose"], layer)
        for layer in AUTO_EMPTY_LAYERS:
            decision = pose_report["auto_empty"][layer]
            assert {"transparent_ratio", "hair_colour_ratio", "empty"} <= set(decision)
            assert decision["empty"] == (pose_report["layer_pixels"][layer] == 0)
        assert pose_report["reconstruction"]["unowned_opaque_pixels"] == 0
        assert pose_report["reconstruction"]["multi_owned_pixels"] == 0
        assert pose_report["max_facial_center_escape_px"] <= MAX_ANCHOR_DRIFT_PIXELS
        assert pose_report["alignment"]["method"] == "yunet-5-point-affine"


def test_v120_cutouts_keep_authority_colours_and_report_empties() -> None:
    built = _built()
    v120_dir = built["v120_dir"]
    v120_report = built["v120_report"]
    files = sorted(v120_dir.glob("v120_*.png"))
    assert len(files) == EXPECTED_V120_FILES, len(files)
    assert v120_report["files"] == EXPECTED_V120_FILES
    failing = set(v120_report["integrity_contract"]["files_failing_visible_or_feather_clause"])
    for pose, suffix, filename in V120_POSES:
        authority = _rgba(built["portrait_dir"] / filename)
        for name in V120_LAYERS:
            path = v120_dir / f"v120_{name}{suffix}.png"
            array = _rgba(path)
            assert array.shape == authority.shape, (pose, path.name)
            visible = array[:, :, 3] > 0
            assert (array[visible, :3] == authority[visible, :3]).all(), (pose, path.name)
            assert not array[~visible, :3].any(), (pose, path.name)
            visible_count = int(visible.sum())
            if path.name in failing:
                # Only genuinely empty rig layers may fail the contract; a
                # partially populated cutout failing it would be a bug.
                assert visible_count == 0, (pose, path.name, visible_count)
                continue
            feather = int((visible & (array[:, :, 3] < FEATHER_ALPHA_THRESHOLD)).sum())
            assert visible_count > MIN_VISIBLE_PIXELS, (pose, path.name, visible_count)
            assert feather > MIN_FEATHER_PIXELS, (pose, path.name, feather)


def run() -> None:
    try:
        built = _built()
        print(f"HALF_BODY_V2_RIG_SOURCE: {built['source']} ({built['portrait_dir']})")
        test_builder_writes_seventy_five_layers_at_canvas_size()
        test_facial_layers_are_non_empty_and_anchored_to_base()
        test_exclusive_ownership_and_zero_transparent_rgb()
        test_neutral_composite_reconstructs_authority()
        test_report_declares_empty_layers_and_alignment_evidence()
        test_v120_cutouts_keep_authority_colours_and_report_empties()
    finally:
        temp = _BUILT.get("temp")
        if temp is not None:
            temp.cleanup()
    print("BUILD_HALF_BODY_LAYERED_RIG_OK")


if __name__ == "__main__":
    run()
