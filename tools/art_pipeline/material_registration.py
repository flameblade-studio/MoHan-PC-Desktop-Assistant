"""Register material-only layers with explicit control pairs; never warp the body.

The inverse thin-plate map interpolates authored source/target landmarks.
Corner and fixed-body anchors keep distant hair tips and clothing stable.
Invalid controls, a singular solution, or a folded map are hard failures.
"""

from __future__ import annotations

lazy import numpy as np

COORDINATE_DIMENSIONS = 2
MIN_CONTROL_POINTS = 3
MAP_CHUNK_ROWS = 32
KERNEL_EPSILON = 1e-15


def _kernel(first: np.ndarray, second: np.ndarray) -> np.ndarray:
    squared = np.square(first[:, None, :] - second[None, :, :]).sum(axis=2)
    return squared * np.log(np.maximum(squared, KERNEL_EPSILON))


def _validate_controls(source: np.ndarray, target: np.ndarray) -> None:
    if (
        source.shape != target.shape
        or source.ndim != COORDINATE_DIMENSIONS
        or source.shape[1] != COORDINATE_DIMENSIONS
        or len(source) < MIN_CONTROL_POINTS
    ):
        raise ValueError("Controls must be matching N-by-2 arrays with at least three points.")
    if not np.isfinite(source).all() or not np.isfinite(target).all():
        raise ValueError("Control coordinates must be finite.")
    if len(np.unique(target, axis=0)) != len(target):
        raise ValueError("Target controls must be unique.")


def control_map(
    source: np.ndarray, target: np.ndarray, shape: tuple[int, int]
) -> tuple[np.ndarray, np.ndarray]:
    """Return inverse maps for the explicit target canvas (height, width)."""
    source = np.asarray(source, dtype=np.float64)
    target = np.asarray(target, dtype=np.float64)
    _validate_controls(source, target)
    height, width = shape
    if min(height, width) < COORDINATE_DIMENSIONS:
        raise ValueError("Canvas must be at least two pixels in each dimension.")
    scale = float(max(shape))
    normalized_source, normalized_target = source / scale, target / scale
    affine = np.column_stack((np.ones(len(target)), normalized_target))
    system = np.block([
        [_kernel(normalized_target, normalized_target), affine],
        [affine.T, np.zeros((MIN_CONTROL_POINTS, MIN_CONTROL_POINTS))],
    ])
    values = np.vstack((normalized_source, np.zeros((MIN_CONTROL_POINTS, COORDINATE_DIMENSIONS))))
    try:
        coefficients = np.linalg.solve(system, values)
    except np.linalg.LinAlgError as error:
        raise ValueError("Control geometry is singular.") from error
    maps = np.empty((height, width, COORDINATE_DIMENSIONS), dtype=np.float32)
    for start in range(0, height, MAP_CHUNK_ROWS):
        stop = min(start + MAP_CHUNK_ROWS, height)
        yy, xx = np.mgrid[start:stop, :width]
        query = np.column_stack((xx.ravel(), yy.ravel())) / scale
        basis = np.column_stack((_kernel(query, normalized_target), np.ones(len(query)), query))
        maps[start:stop] = (basis @ coefficients * scale).reshape(stop - start, width, COORDINATE_DIMENSIONS)
    map_x, map_y = maps[:, :, 0], maps[:, :, 1]
    if not np.isfinite(maps).all():
        raise ValueError("Registration produced non-finite coordinates.")
    jacobian = (
        np.gradient(map_x, axis=1) * np.gradient(map_y, axis=0)
        - np.gradient(map_x, axis=0) * np.gradient(map_y, axis=1)
    )
    if float(jacobian.min()) <= 0:
        raise ValueError("Registration folds the material; revise control geometry.")
    return map_x, map_y
