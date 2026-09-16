"""Register material-only layers with explicit control pairs while retaining body geometry.

The inverse thin-plate map interpolates authored source/target landmarks.
Corner and fixed-body anchors keep distant hair tips and clothing stable.
Registration proceeds with valid controls, a solvable system, and a fold-free map; validation errors remain explicit.
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


def _validate_boundary(
    source: np.ndarray, target: np.ndarray, shape: tuple[int, int], boundary_width: int
) -> None:
    if isinstance(boundary_width, bool) or not isinstance(boundary_width, int) or boundary_width < 0:
        raise ValueError("Boundary width must be a nonnegative integer.")
    if boundary_width:
        height, width = shape
        moving = np.any(source != target, axis=1)
        distances = np.minimum.reduce([
            target[:, 0], target[:, 1], width - 1 - target[:, 0], height - 1 - target[:, 1],
        ])
        if np.any(distances[moving] < boundary_width):
            raise ValueError("Moving controls must lie beyond the fixed boundary transition.")


def _fix_patch_boundary(
    map_x: np.ndarray, map_y: np.ndarray, boundary_width: int
) -> tuple[np.ndarray, np.ndarray]:
    height, width = map_x.shape
    yy, xx = np.indices(map_x.shape, dtype=np.float32)
    distance = np.minimum.reduce([xx, yy, width - 1 - xx, height - 1 - yy])
    weight = np.clip(distance / boundary_width, 0, 1)
    weight = weight * weight * (3 - 2 * weight)
    return xx + (map_x - xx) * weight, yy + (map_y - yy) * weight


def control_map(
    source: np.ndarray,
    target: np.ndarray,
    shape: tuple[int, int],
    *,
    boundary_width: int = 0,
) -> tuple[np.ndarray, np.ndarray]:
    """Return inverse maps, optionally fixing the entire local patch boundary.

    A positive boundary width smoothly reduces displacement to zero at every
    edge pixel. Moving controls belong beyond that transition band so their
    authored positions remain authoritative. The final map must stay fold-free.
    """
    source = np.asarray(source, dtype=np.float64)
    target = np.asarray(target, dtype=np.float64)
    _validate_controls(source, target)
    height, width = shape
    if min(height, width) < COORDINATE_DIMENSIONS:
        raise ValueError("Canvas must be at least two pixels in each dimension.")
    _validate_boundary(source, target, shape, boundary_width)
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
    if boundary_width:
        map_x, map_y = _fix_patch_boundary(map_x, map_y, boundary_width)
    if not np.isfinite(maps).all():
        raise ValueError("Registration produced non-finite coordinates.")
    jacobian = (
        np.gradient(map_x, axis=1) * np.gradient(map_y, axis=0)
        - np.gradient(map_x, axis=0) * np.gradient(map_y, axis=1)
    )
    if float(jacobian.min()) <= 0:
        raise ValueError("Registration folds the material; revise control geometry.")
    return map_x, map_y
