# MHR Body Morph Candidate-3 Result

Status: **BONE-BOUNDED PLAUSIBILITY AND MESH-INTEGRITY GATES PASS — SURFACE LANDMARKS STILL LIMITED**

Candidate-2 was rejected because scaling around its surface-loop centroid changed front/back depth relative to the official skeleton axis excessively: waist `2.4241 -> 5.0815`, underbust `3.3994 -> 6.0823`.

Candidate-3 uses the same deterministic C2 local torso morph, but centers X/Z scaling on the official MHR FBX skeleton axis interpolated from mean `l_upleg/r_upleg` through `c_spine0..c_spine3`.

| Section | Target (cm) | Actual (cm) | Error (cm) |
|---|---:|---:|---:|
| Bust | 86.0000 | 86.3105 | +0.3105 |
| Underbust | 71.0000 | 70.9700 | -0.0300 |
| Waist | 62.0000 | 62.2139 | +0.2139 |
| Hip | 90.0000 | 90.0693 | +0.0693 |

All section errors remain within `0.5 cm`; height remains exactly `168 cm`.

Mesh-integrity audit on 3,618 changed triangles:

- Degenerate triangles: `0`
- Triangle flips: `0`
- Normal flips: `0`
- Local Jacobian determinant range: `0.5730846 .. 1.5749203`
- Surface singular-value range: `0.6133627 .. 1.5973558`
- Strict non-coplanar local self-intersections: `0` across 1,336 narrow-phase pairs
- Maximum displacement outside vertical morph support: `0`

Front/back ratio change relative to the official skeleton axis is `-0.0008` hip, `+0.0035` waist, `-0.0164` underbust, and `-0.0234` bust; all pass the `0.25` gate.

The four plane heights fall in explicit skeleton-bounded regions, but the 127-joint skeleton does not provide breast apex, inframammary fold, rib margin, iliac crest, or greater-trochanter surface landmarks. This remains bounded plausibility, not clinical or tailoring-grade anatomical validation.
