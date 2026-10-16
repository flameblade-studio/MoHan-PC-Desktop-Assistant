"""Report model-projected geometry with explicit artwork support and gaps.

The 478-point artifacts contain model predictions, not manually annotated
anatomical observations. Authored feature or skin layers can support their
projected locations; authored hair coverage marks occlusion. Missing support
stays unverified. Relative z is diagnostic only and never proves visibility.

Even a supported projected location does not prove a landmark's anatomical
identity or the visibility of a far-side surface. All resulting ratios remain
model-derived diagnostics, not biometric certification or appearance approval.
"""

from __future__ import annotations

lazy import math
lazy from dataclasses import dataclass
lazy from typing import Any
lazy from collections.abc import Callable, Mapping

lazy import numpy as np

SCHEMA = "mohan.pose-atlas-visible-geometry.v1"

MESH_FAMILY = "mesh_visible_observation"
OUTLINE_FAMILY = "non_canonical_image_outline"
UNSUPPORTED_FAMILY = "unsupported_source"
MODEL_DERIVED_BASIS = "model_derived_projected_measurement"

MEASURED = "measured"
OCCLUDED = "occluded"
UNSUPPORTED_SOURCE = "unsupported_source"
NOT_APPLICABLE = "not_applicable"

AUTHORED_FEATURE_SUPPORT = "authored_feature_support"
AUTHORED_SKIN_SUPPORT = "authored_skin_support"
OCCLUDED_BY_AUTHORED_LAYER = "occluded_by_authored_layer"
VISIBILITY_UNVERIFIED = "visibility_unverified"
SUPPORTED_VERTEX_STATES = (AUTHORED_FEATURE_SUPPORT, AUTHORED_SKIN_SUPPORT)
HIDDEN_VERTEX_STATES = (OCCLUDED_BY_AUTHORED_LAYER, VISIBILITY_UNVERIFIED)

EXPLICIT_MESH_POINT_COUNT = 478
CHIN_VERTEX_INDEX = 152
MASK_DIMENSIONS = 2
VERTEX_NEIGHBOURHOOD_RADIUS = 2
MIN_SKIN_RATIO = 0.5
MIN_OCCLUDER_RATIO = 0.5
MIN_FEATURE_RATIO = 0.1

NECK_WINDOW_ROWS = 240
MAX_NECK_TO_HEAD_RATIO = 0.75
MIN_NECK_WIDTH = 8
MIN_SEARCH_ROWS = 40

# Relative depth is reported as a clearly labelled model diagnostic only. It is
# never used as an occlusion verdict: an uncalibrated z ordering cannot prove
# that a far-side vertex is hidden or that a near-side vertex is painted.
RELATIVE_DEPTH_DIAGNOSTIC_PAIRS: tuple[tuple[int, int], ...] = (
    (133, 362), (145, 374), (159, 386), (105, 334),
    (129, 358), (61, 291), (234, 454), (172, 397),
)
MIDLINE_VERTICES: tuple[int, ...] = (10, 168, 2, 4, 13, 14, 9, 152)
FEATURE_VERTEX_LAYERS: Mapping[int, Mapping[str, str]] = {
    133: {"left": "iris_left", "right": "iris_right"},
    362: {"left": "iris_left", "right": "iris_right"},
    105: {"left": "brow_left", "right": "brow_right"},
    334: {"left": "brow_left", "right": "brow_right"},
}

Z_SCALE_EVIDENCE: dict[str, Any] = {
    "files": ["infrastructure/multimodal_model_provider.py"],
    "x_y_normalization": (
        "the provider builds x = left + out_x * side / FACE_MESH_MODEL_SIZE and "
        "normalizes by the canvas width (line 283); y normalizes by the canvas "
        "height, so artifact x and y restore to canvas pixels"
    ),
    "z_normalization": (
        "the provider builds z = out_z / FACE_MESH_MODEL_SIZE only (line 280), so "
        "artifact z is a fraction of the square crop side, not of the canvas"
    ),
    "crop_side": (
        "side = max(box_width, box_height) * 1.5 comes from the YuNet face box "
        "(line 415); neither side nor the crop origin is recorded in the artifact"
    ),
    "conclusion": (
        "z_pixels = z * side cannot be recovered from the artifact, so depth-based "
        "fields are unsupported_source rather than unit-mixed with pixel ratios"
    ),
    "ordinal_use": (
        "within one artifact every z shares one crop scale, so comparing two "
        "vertices' z is meaningful enough to order near and far sides"
    ),
}


class GeometryError(ValueError):
    """The authorized sources cannot support the requested measurement."""


@dataclass(frozen=True, slots=True)
class VertexEvidence:
    """Image evidence for one projected vertex."""

    index: int
    x: float
    y: float
    skin_ratio: float
    occluder_ratio: float
    feature_ratio: float
    occluder_layers: tuple[str, ...]
    feature_layers: tuple[str, ...]
    state: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "x": round(self.x, 3),
            "y": round(self.y, 3),
            "skin_ratio": round(self.skin_ratio, 3),
            "occluder_ratio": round(self.occluder_ratio, 3),
            "feature_ratio": round(self.feature_ratio, 3),
            "occluder_layers": list(self.occluder_layers),
            "feature_layers": list(self.feature_layers),
            "state": self.state,
        }


@dataclass(frozen=True, slots=True)
class ViewGeometryEvidence:
    """One view's authorized inputs for visible geometry measurement."""

    view_id: str
    yaw_degrees: int
    canvas: tuple[int, int]
    png_sha256: str
    artifact_sha256: str | None
    points: np.ndarray | None
    figure_alpha: np.ndarray
    skin_alpha: np.ndarray
    occluder_alpha: np.ndarray
    occluder_layer_alpha: Mapping[str, np.ndarray]
    feature_alpha: Mapping[str, np.ndarray]
    chin_row: int | None

    @property
    def has_mesh(self) -> bool:
        return self.points is not None and self.points.shape == (
            EXPLICIT_MESH_POINT_COUNT,
            3,
        )

    def pixel(self, index: int) -> tuple[float, float]:
        """Canvas coordinates in float, so ratios are never quantised early."""

        if self.points is None:
            raise GeometryError("native_face_landmarks_missing")
        if not 0 <= index < len(self.points):
            raise GeometryError(f"landmark_index_out_of_range:{index}")
        point = self.points[index]
        return float(point[0] * self.canvas[0]), float(point[1] * self.canvas[1])

    def sample_point(self, index: int) -> tuple[int, int]:
        """Nearest pixel used only for mask sampling."""

        x, y = self.pixel(index)
        return round(x), round(y)

    def pixel_distance(self, left: int, right: int) -> float:
        first, second = self.pixel(left), self.pixel(right)
        return float(math.hypot(first[0] - second[0], first[1] - second[1]))

    def face_width(self) -> float:
        return self.pixel_distance(234, 454)

    def face_length(self) -> float:
        return self.pixel_distance(10, 152)

    def depth(self, index: int) -> float:
        if self.points is None:
            raise GeometryError("native_face_landmarks_missing")
        return float(self.points[index][2])


def _window(mask: np.ndarray, x: int, y: int, radius: int) -> np.ndarray:
    """Sample a neighbourhood, fail closed on an out-of-canvas coordinate."""

    if mask.ndim != MASK_DIMENSIONS:
        raise GeometryError("mask_not_two_dimensional")
    if mask.size == 0:
        raise GeometryError(f"empty_sample_window:{x},{y}")
    if not (0 <= x < mask.shape[1] and 0 <= y < mask.shape[0]):
        raise GeometryError(f"sample_point_out_of_canvas:{x},{y}")
    y0, y1 = max(0, y - radius), min(mask.shape[0], y + radius + 1)
    x0, x1 = max(0, x - radius), min(mask.shape[1], x + radius + 1)
    window = mask[y0:y1, x0:x1]
    if window.size == 0:
        raise GeometryError(f"empty_sample_window:{x},{y}")
    return window


def relative_depth_diagnostic(evidence: ViewGeometryEvidence) -> dict[str, float]:
    """Uncalibrated model depth ordering, reported as a diagnostic only."""

    if not evidence.has_mesh:
        return {}
    return {
        f"{left}-{right}": round(
            abs(evidence.depth(left) - evidence.depth(right)), 6
        )
        for left, right in RELATIVE_DEPTH_DIAGNOSTIC_PAIRS
    }


def classify_vertex(
    evidence: ViewGeometryEvidence, index: int, *, radius: int = VERTEX_NEIGHBOURHOOD_RADIUS
) -> VertexEvidence:
    """Classify one projected vertex from authored artwork evidence only.

    A painted hair or ornament layer over the point is evidence of occlusion. An
    authored feature layer painting at an eye or brow vertex is evidence that the
    view draws that feature there. Otherwise only authored bare-skin coverage can
    support the point, and anything else stays ``visibility_unverified`` - an
    empty layer is never read as "nothing occludes this".
    """

    canvas_x, canvas_y = evidence.pixel(index)
    x, y = evidence.sample_point(index)
    try:
        skin = float(_window(evidence.skin_alpha, x, y, radius).mean())
        occluder = float(_window(evidence.occluder_alpha, x, y, radius).mean())
    except GeometryError:
        return VertexEvidence(
            index, canvas_x, canvas_y, 0.0, 0.0, 0.0, (), (), VISIBILITY_UNVERIFIED
        )
    occluder_layers = tuple(
        name
        for name, mask in evidence.occluder_layer_alpha.items()
        if float(_window(mask, x, y, radius).mean()) >= MIN_OCCLUDER_RATIO
    )
    feature_layers: list[str] = []
    feature_ratio = 0.0
    for layer in FEATURE_VERTEX_LAYERS.get(index, {}).values():
        mask = evidence.feature_alpha.get(layer)
        if mask is None:
            continue
        ratio = float(_window(mask, x, y, radius).mean())
        if ratio >= MIN_FEATURE_RATIO:
            feature_layers.append(layer)
            feature_ratio = max(feature_ratio, ratio)
    if occluder_layers:
        state = OCCLUDED_BY_AUTHORED_LAYER
    elif FEATURE_VERTEX_LAYERS.get(index):
        state = AUTHORED_FEATURE_SUPPORT if feature_layers else VISIBILITY_UNVERIFIED
    elif skin >= MIN_SKIN_RATIO:
        state = AUTHORED_SKIN_SUPPORT
    else:
        state = VISIBILITY_UNVERIFIED
    return VertexEvidence(
        index, canvas_x, canvas_y, skin, occluder, feature_ratio,
        occluder_layers, tuple(feature_layers), state,
    )


@dataclass(frozen=True, slots=True)
class FormulaSpec:
    """A named derivation for one canonical signature field or diagnostic."""

    field: str
    formula_id: str
    family: str
    vertices: tuple[int, ...]
    expression: str
    compute: Callable[[ViewGeometryEvidence], float] | None
    method: str
    note: str = ""
    unsupported_reason: str | None = None


def _ratio(numerator: float, denominator: float, label: str) -> float:
    if not math.isfinite(denominator) or denominator <= 0.0:
        raise GeometryError(f"degenerate_denominator:{label}")
    value = numerator / denominator
    if not math.isfinite(value):
        raise GeometryError(f"non_finite_result:{label}")
    return value


def _eye_balance(evidence: ViewGeometryEvidence) -> float:
    left = evidence.pixel_distance(159, 145)
    right = evidence.pixel_distance(386, 374)
    wider = max(left, right)
    if wider <= 0.0:
        raise GeometryError("degenerate_eye_aperture")
    return min(left, right) / wider


def _face_width_ratio(left: int, right: int, label: str) -> Callable[[ViewGeometryEvidence], float]:
    return lambda view: _ratio(view.pixel_distance(left, right), view.face_width(), label)


def _face_length_ratio(
    left: int, right: int, label: str
) -> Callable[[ViewGeometryEvidence], float]:
    return lambda view: _ratio(view.pixel_distance(left, right), view.face_length(), label)


def _unsupported(reason: str) -> Callable[[ViewGeometryEvidence], float]:
    def compute(_view: ViewGeometryEvidence) -> float:
        raise GeometryError(reason)

    return compute


DEPTH_UNSUPPORTED_REASON = (
    "z_scale_factor_not_recorded: artifact z is a fraction of the unrecorded model "
    "crop side while x and y are canvas-normalized, so a depth-over-pixel ratio has "
    "no dimensionally consistent value"
)
OUTLINE_WITHHELD_REASON = (
    "canonical_value_withheld: only a hair-inclusive image-outline proxy is "
    "measurable, so the canonical field reports no value"
)
EAR_UNSUPPORTED_REASON = (
    "the declared FaceMesh468+iris model has no ear vertex and no authored ear "
    "annotation exists"
)
HAIRLINE_UNSUPPORTED_REASON = (
    "the contract names no hairline or nape pair and neither the declared model nor "
    "the authored layers expose one"
)


METHOD_BY_FAMILY = {
    MESH_FAMILY: "ratio of two or more landmark distances in canvas pixels",
    UNSUPPORTED_FAMILY: "withheld",
    OUTLINE_FAMILY: "alpha-outline rows and widths of the native PNG",
}
FIELD_NOTES: dict[str, str] = {
    "image_outline_head_height_over_width": (
        "diagnostic only: the outline includes the adopted hair and is not a "
        "canonical signature field"
    ),
    "image_outline_neck_over_head_width": (
        "diagnostic only; in profile views the narrowest row is usually the jaw "
        "line, so this bounds neck width"
    ),
}


def _spec(
    name: str,
    formula_id: str,
    vertices: tuple[int, ...],
    expression: str,
    compute: Callable[[ViewGeometryEvidence], float] | None,
    family: str = MESH_FAMILY,
    unsupported_reason: str | None = None,
) -> FormulaSpec:
    return FormulaSpec(
        name, formula_id, family, vertices, expression, compute,
        METHOD_BY_FAMILY[family], FIELD_NOTES.get(name, ""), unsupported_reason,
    )


SUPPORTED_SPECS: tuple[FormulaSpec, ...] = (
    _spec("face_length_width", "mesh468.face_length_width.v1", (10, 152, 234, 454),
          "norm(P10-P152) / norm(P234-P454)",
          lambda view: _ratio(view.face_length(), view.face_width(), "face_length_width")),
    _spec("eye_spacing_width", "mesh468.eye_spacing_width.v1", (133, 362, 234, 454),
          "norm(P133-P362) / norm(P234-P454)",
          _face_width_ratio(133, 362, "eye_spacing_width")),
    _spec("eye_height_balance", "mesh468.eye_height_balance.v1", (159, 145, 386, 374),
          "min(|P159-P145|, |P386-P374|) / max(same)", _eye_balance),
    _spec("brow_eye_spacing", "mesh468.brow_eye_spacing.v1",
          (105, 159, 334, 386, 10, 152),
          "mean(norm(P105-P159), norm(P334-P386)) / norm(P10-P152)",
          lambda view: _ratio(
              0.5 * (view.pixel_distance(105, 159) + view.pixel_distance(334, 386)),
              view.face_length(), "brow_eye_spacing")),
    _spec("nose_length_face", "mesh468.nose_length_face.v1", (168, 2, 10, 152),
          "norm(P168-P2) / norm(P10-P152)",
          _face_length_ratio(168, 2, "nose_length_face")),
    _spec("nose_width_face", "mesh468.nose_width_face.v1", (129, 358, 234, 454),
          "norm(P129-P358) / norm(P234-P454)",
          _face_width_ratio(129, 358, "nose_width_face")),
    _spec("mouth_width_face", "mesh468.mouth_width_face.v1", (61, 291, 234, 454),
          "norm(P61-P291) / norm(P234-P454)",
          _face_width_ratio(61, 291, "mouth_width_face")),
    _spec("nose_mouth_spacing", "mesh468.nose_mouth_spacing.v1", (2, 13, 10, 152),
          "norm(P2-P13) / norm(P10-P152)",
          _face_length_ratio(2, 13, "nose_mouth_spacing")),
    _spec("chin_length_face", "mesh468.chin_length_face.v1", (14, 152, 10, 152),
          "norm(P14-P152) / norm(P10-P152)",
          _face_length_ratio(14, 152, "chin_length_face")),
    _spec("jaw_taper", "mesh468.jaw_taper.v1", (172, 397, 234, 454),
          "norm(P172-P397) / norm(P234-P454)",
          _face_width_ratio(172, 397, "jaw_taper")),
)

UNSUPPORTED_SPECS: tuple[FormulaSpec, ...] = (
    _spec("nose_projection", "mesh468.nose_projection.v1", (168, 4, 234, 454),
          "(z168 - z4) / norm(P234-P454)", _unsupported(DEPTH_UNSUPPORTED_REASON),
          family=UNSUPPORTED_FAMILY, unsupported_reason=DEPTH_UNSUPPORTED_REASON),
    _spec("lip_projection", "mesh468.lip_projection.v1", (152, 13, 234, 454),
          "(z152 - z13) / norm(P234-P454)", _unsupported(DEPTH_UNSUPPORTED_REASON),
          family=UNSUPPORTED_FAMILY, unsupported_reason=DEPTH_UNSUPPORTED_REASON),
    _spec("chin_projection", "mesh468.chin_projection.v1", (152, 10, 234, 454),
          "(z152 - z10) / norm(P234-P454)", _unsupported(DEPTH_UNSUPPORTED_REASON),
          family=UNSUPPORTED_FAMILY, unsupported_reason=DEPTH_UNSUPPORTED_REASON),
    _spec("forehead_slope", "mesh468.forehead_slope.v1", (9, 10, 152),
          "(z9 - z10) / norm(P10-P152)", _unsupported(DEPTH_UNSUPPORTED_REASON),
          family=UNSUPPORTED_FAMILY, unsupported_reason=DEPTH_UNSUPPORTED_REASON),
    _spec("cranial_height_width", "withheld.image-outline-only.v1", (),
          "no canonical evidence", _unsupported(OUTLINE_WITHHELD_REASON),
          family=UNSUPPORTED_FAMILY, unsupported_reason=OUTLINE_WITHHELD_REASON),
    _spec("ear_height_head", "withheld.no-ear-source.v1", (),
          "no ear vertex or annotation", _unsupported(EAR_UNSUPPORTED_REASON),
          family=UNSUPPORTED_FAMILY, unsupported_reason=EAR_UNSUPPORTED_REASON),
    _spec("jaw_neck_transition", "withheld.image-outline-only.v1", (),
          "no canonical evidence", _unsupported(OUTLINE_WITHHELD_REASON),
          family=UNSUPPORTED_FAMILY, unsupported_reason=OUTLINE_WITHHELD_REASON),
    _spec("hairline_nape", "withheld.no-hairline-source.v1", (),
          "no hairline or nape pair", _unsupported(HAIRLINE_UNSUPPORTED_REASON),
          family=UNSUPPORTED_FAMILY, unsupported_reason=HAIRLINE_UNSUPPORTED_REASON),
)

FORMULA_BY_FIELD: dict[str, FormulaSpec] = {
    spec.field: spec for spec in (*SUPPORTED_SPECS, *UNSUPPORTED_SPECS)
}


def _head_silhouette(evidence: ViewGeometryEvidence) -> dict[str, int]:
    """Crown, widest head row, and neck constriction inside the native alpha."""

    if evidence.figure_alpha.ndim != MASK_DIMENSIONS:
        raise GeometryError("silhouette_not_two_dimensional")
    if evidence.chin_row is None:
        raise GeometryError("chin_anchor_missing")
    widths = np.count_nonzero(evidence.figure_alpha, axis=1)
    rows = np.flatnonzero(widths)
    if not len(rows):
        raise GeometryError("empty_native_silhouette")
    top = int(rows[0])
    chin = int(evidence.chin_row)
    if chin <= top:
        raise GeometryError("chin_anchor_not_below_crown")
    head_width = float(widths[top : chin + 1].max())
    if head_width <= 0.0:
        raise GeometryError("degenerate_head_width")
    ledge = widths[chin : chin + NECK_WINDOW_ROWS]
    if ledge.size < MIN_SEARCH_ROWS:
        raise GeometryError("silhouette_too_short_for_neck_search")
    neck_width = float(ledge.min())
    if neck_width < MIN_NECK_WIDTH:
        raise GeometryError("degenerate_neck_width")
    if neck_width > head_width * MAX_NECK_TO_HEAD_RATIO:
        raise GeometryError("neck_not_narrower_than_head")
    return {
        "top": top,
        "widest_row": top + int(np.argmax(widths[top : chin + 1])),
        "head_width": round(head_width),
        "neck_row": chin + int(np.argmin(ledge)),
        "neck_width": round(neck_width),
    }


OUTLINE_SPECS: tuple[FormulaSpec, ...] = (
    _spec("image_outline_head_height_over_width",
          "image-outline.head_height_over_width.v1", (),
          "(neck_row - crown_row) / widest_row_width_above_the_measured_chin",
          lambda view: _ratio(
              float(_head_silhouette(view)["neck_row"] - _head_silhouette(view)["top"]),
              float(_head_silhouette(view)["head_width"]),
              "image_outline_head_height_over_width"),
          family=OUTLINE_FAMILY),
    _spec("image_outline_neck_over_head_width",
          "image-outline.neck_over_head_width.v1", (),
          "narrowest_row_width_below_the_measured_chin / widest_row_width_above_it",
          lambda view: _ratio(
              float(_head_silhouette(view)["neck_width"]),
              float(_head_silhouette(view)["head_width"]),
              "image_outline_neck_over_head_width"),
          family=OUTLINE_FAMILY),
)


def signature_field_order() -> tuple[str, ...]:
    """The canonical 18-field order declared by the existing strict contract."""

    from domain.character_identity_audit import SIGNATURE_FIELDS

    return tuple(SIGNATURE_FIELDS)


def measure_view_fields(
    evidence: ViewGeometryEvidence,
    *,
    applicable_fields: tuple[str, ...] | None = None,
) -> dict[str, Any]:
    """Measure every canonical field plus the outline diagnostics for one view."""

    vertices = (
        {index: classify_vertex(evidence, index) for index in _used_vertices()}
        if evidence.has_mesh
        else {}
    )
    fields: dict[str, dict[str, Any]] = {}
    for name in signature_field_order():
        spec = FORMULA_BY_FIELD[name]
        fields[name] = _measure_field(evidence, spec, vertices, applicable_fields)
    diagnostics = {
        spec.field: _measure_field(evidence, spec, vertices, None)
        for spec in OUTLINE_SPECS
    }
    for record in diagnostics.values():
        record["canonical"] = False
    return {
        "schema": SCHEMA,
        "view_id": evidence.view_id,
        "yaw_degrees": evidence.yaw_degrees,
        "canvas": list(evidence.canvas),
        "source": {
            "png_sha256": evidence.png_sha256,
            "artifact_sha256": evidence.artifact_sha256,
        },
        "z_scale_evidence": Z_SCALE_EVIDENCE,
        "relative_depth_diagnostic": relative_depth_diagnostic(evidence),
        "relative_depth_note": (
            "model diagnostic only: artifact z is uncalibrated, so this ordering "
            "is never used as an occlusion or visibility verdict"
        ),
        "measurement_basis": MODEL_DERIVED_BASIS,
        "vertices": {str(index): record.to_dict() for index, record in vertices.items()},
        "fields": fields,
        "image_outline_diagnostics": diagnostics,
    }


def _used_vertices() -> tuple[int, ...]:
    used: set[int] = set(MIDLINE_VERTICES)
    for spec in (*SUPPORTED_SPECS,):
        used.update(spec.vertices)
    return tuple(sorted(used))


def _measure_field(
    evidence: ViewGeometryEvidence,
    spec: FormulaSpec,
    vertices: Mapping[int, VertexEvidence],
    applicable_fields: tuple[str, ...] | None,
) -> dict[str, Any]:
    base: dict[str, Any] = {
        "formula_id": spec.formula_id,
        "family": spec.family,
        "method": spec.method,
        "expression": spec.expression,
        "required_vertices": list(spec.vertices),
        "source_path": (
            f"assets/pose-atlas/v5-base/{evidence.view_id}.native-landmarks.json"
            if spec.family == MESH_FAMILY
            else f"assets/pose-atlas/v5-base/{evidence.view_id}.png"
        ),
        "source_sha256": (
            evidence.artifact_sha256 if spec.family == MESH_FAMILY
            else evidence.png_sha256
        ),
        "note": spec.note,
    }
    if applicable_fields is not None and spec.field not in applicable_fields:
        return {**base, "status": NOT_APPLICABLE, "reason": "outside_view_visibility_band"}
    if spec.compute is None or spec.family == UNSUPPORTED_FAMILY:
        return {
            **base,
            "status": UNSUPPORTED_SOURCE,
            "value": None,
            "reason": spec.unsupported_reason or "unsupported_source",
        }
    if not evidence.has_mesh:
        return {
            **base,
            "status": UNSUPPORTED_SOURCE,
            "value": None,
            "reason": "native_face_landmarks_missing",
        }
    try:
        value: float | None = float(spec.compute(evidence))
    except GeometryError as error:
        value = None
        computation_reason = str(error)
    else:
        computation_reason = None
    hidden = {
        str(index): vertices[index].state
        for index in spec.vertices
        if index in vertices and vertices[index].state in HIDDEN_VERTEX_STATES
    }
    if value is None and not hidden:
        return {**base, "status": UNSUPPORTED_SOURCE, "value": None,
                "reason": computation_reason or "not_computable"}
    occluded = [
        index for index in spec.vertices
        if vertices.get(index) is not None
        and vertices[index].state == OCCLUDED_BY_AUTHORED_LAYER
    ]
    unverified = [
        index for index in spec.vertices
        if vertices.get(index) is not None
        and vertices[index].state == VISIBILITY_UNVERIFIED
    ]
    if unverified:
        return {
            **base,
            "status": UNSUPPORTED_SOURCE,
            "value": None,
            "unverified_vertices": unverified,
            "occluded_vertices": occluded,
            "vertex_states": hidden,
            "model_inferred_value": value,
            "reason": "visibility_unverified:"
            + ",".join(str(index) for index in unverified),
        }
    if occluded:
        return {
            **base,
            "status": OCCLUDED,
            "value": None,
            "unverified_vertices": [],
            "occluded_vertices": occluded,
            "vertex_states": hidden,
            "model_inferred_value": value,
            "reason": "occluded_by_authored_layer:"
            + ",".join(str(index) for index in occluded),
            "supported_vertices": [
                index for index in spec.vertices
                if vertices[index].state in SUPPORTED_VERTEX_STATES
            ],
        }
    return {
        **base,
        "status": MEASURED,
        "value": value,
        "measurement_basis": MODEL_DERIVED_BASIS,
        "supported_vertices": list(spec.vertices),
    }
