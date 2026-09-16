"""Local garment registration preserves seams and rejects unsafe control geometry."""

lazy import numpy as np
lazy import pytest

lazy from tools.art_pipeline.material_registration import control_map


def test_local_registration_fixes_every_edge_and_retains_wrist_shift() -> None:
    """Sparse fixed corners alone must not let a patch move at its seam."""
    target = np.array([[0, 0], [80, 0], [0, 80], [80, 80], [40, 40]], dtype=float)
    source = target.copy()
    source[-1] = [46, 36]
    map_x, map_y = control_map(source, target, (81, 81), boundary_width=12)
    yy, xx = np.indices((81, 81))
    edge = (xx == 0) | (xx == map_x.shape[1] - 1) | (yy == 0) | (yy == map_x.shape[0] - 1)
    np.testing.assert_array_equal(map_x[edge], xx[edge])
    np.testing.assert_array_equal(map_y[edge], yy[edge])
    np.testing.assert_allclose([map_x[40, 40], map_y[40, 40]], [46, 36], atol=1e-5)


def test_boundary_transition_rejects_a_moving_control_it_would_override() -> None:
    target = np.array([[0, 0], [80, 0], [0, 80], [80, 80], [5, 40]], dtype=float)
    source = target.copy()
    source[-1] = [7, 40]
    with pytest.raises(ValueError, match="Moving controls"):
        control_map(source, target, (81, 81), boundary_width=12)


def test_material_registration_rejects_a_fold() -> None:
    target = np.array([[0, 0], [20, 0], [0, 20], [20, 20]], dtype=float)
    source = target.copy()
    source[:, 0] = 20 - source[:, 0]
    with pytest.raises(ValueError, match="folds the material"):
        control_map(source, target, (21, 21))


def test_identity_registration_preserves_all_pixels_with_fixed_boundary() -> None:
    controls = np.array([[0, 0], [30, 0], [0, 30], [30, 30]], dtype=float)
    map_x, map_y = control_map(controls, controls, (31, 31), boundary_width=5)
    yy, xx = np.indices((31, 31))
    np.testing.assert_allclose(map_x, xx, atol=1e-5)
    np.testing.assert_allclose(map_y, yy, atol=1e-5)
