# MHR Body Morph Candidate-2 Result

Status: **SECTION TARGETS PASS — DETERMINISTIC GEOMETRY CANDIDATE — SECTION HEIGHTS NOT ANATOMICALLY VALIDATED**

The zero-neutral MHR/ufbx mesh was uniformly scaled from `172.68145751953125 cm` to exactly `168 cm`, then modified only in one connected central-torso region. Head, arms outside the torso envelope, and legs outside the vertical support retained zero influence and byte-equivalent float coordinates.

The local X/Z scale is one C2 SciPy `CubicSpline`. It uses four measurement anchors and linearly densified interpolation knots to suppress cubic overshoot. Its scale returns smoothly to 1.0 with zero first derivative at both support endpoints. No Y coordinate or topology changed.

| Candidate section | Target (cm) | Actual (cm) | Signed error (cm) |
|---|---:|---:|---:|
| Bust | 86.0000 | 86.3666 | +0.3666 |
| Underbust | 71.0000 | 70.9963 | -0.0037 |
| Waist | 62.0000 | 62.1988 | +0.1988 |
| Hip | 90.0000 | 90.0861 | +0.0861 |

All four candidate-section errors are within `0.5 cm`. The minimum sampled local scale is `0.6287612104`, close to the waist anchor `0.6290318595`; the earlier overshooting attempt with minimum `0.579` was overwritten and is not accepted.

The selected central-torso component contains 1,731 vertices; 16,708 zero-weight vertices are preserved exactly. Topology remains 18,439 vertices and 36,874 triangles.

This is a traceable geometry deformation, not clothing and not a generated body. The four fixed height fractions remain candidate measurement planes and require anatomical landmark validation before this mesh can become an authority.
