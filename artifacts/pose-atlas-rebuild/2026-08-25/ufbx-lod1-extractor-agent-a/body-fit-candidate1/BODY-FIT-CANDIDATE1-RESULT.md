# MHR Body Fit Candidate-1 Result

Status: **CANDIDATE ONLY — CIRCUMFERENCE TARGETS NOT MET — NOT ANATOMICALLY VALIDATED**

## Method

- Optimized body identity coefficients 0–19 only, each constrained to `[-3, 3]`.
- Coefficients 20–44 remained exactly zero.
- Used 1600 PyTorch Adam iterations, then 31 SciPy bounded least-squares evaluations.
- Identity coefficients were used for shape only. Every candidate recomputed its own unscaled height and applied a separate uniform scale `168 / current_height` before circumference measurement.
- Objective used the largest closed torso loop only; secondary loops were excluded.
- L2 coefficient prior weight: `0.05`; symmetry weight: `0.02`.
- Topology remained 18,439 vertices and 36,874 triangles.

## Final measurements

| Measurement | Target (cm) | Actual (cm) | Signed error (cm) |
|---|---:|---:|---:|
| Height | 168.0000 | 168.0000 | +0.0000 |
| Bust candidate | 86.0000 | 94.0933 | +8.0933 |
| Underbust candidate | 71.0000 | 76.9003 | +5.9003 |
| Waist candidate | 62.0000 | 84.0009 | +22.0009 |
| Hip candidate | 90.0000 | 98.9547 | +8.9547 |

Unscaled candidate height: `172.7875828215717 cm`

Independent uniform scale: `0.9722920898400692`

Ten of the first twenty coefficients reached `abs(coefficient) >= 2.95`. The requested circumference targets therefore cannot be claimed as achieved in this first-20, bounded, regularized coefficient space. The largest miss is the waist at `+22.0009 cm`.

## Section evidence

| Section | Closed loops | Open components | Largest torso loop (cm) |
|---|---:|---:|---:|
| Bust candidate | 3 | 0 | 94.0933 |
| Underbust candidate | 3 | 0 | 76.9003 |
| Waist candidate | 5 | 0 | 84.0009 |
| Hip candidate | 1 | 0 | 98.9547 |

Visual inspection of `candidate1-wireframe-sections.png` confirms a complete front/side body wireframe and four displayed closed maximum-perimeter torso loops. It does not prove that the candidate height fractions are anatomically correct.

## Reproducibility evidence

Fit command:

```text
cmd.exe /d /c "D:\FlamebladeStudio\CodexProjects\2026-08-13\mohan-multisensory-vision\artifacts\pose-atlas-rebuild\2026-08-25\ufbx-lod1-extractor-agent-a\run-body-fit-candidate1.cmd"
```

Fit exit code: `0`; `stderr.txt` is empty.

ufbx-only reconstruction and verification command:

```text
cmd.exe /d /c "D:\FlamebladeStudio\CodexProjects\2026-08-13\mohan-multisensory-vision\artifacts\pose-atlas-rebuild\2026-08-25\ufbx-lod1-extractor-agent-a\run-candidate1-ufbx-verify.cmd"
```

Reconstruction exit code: `0`; verification exit code: `0`; both stderr files are empty.

The ufbx-only linear-offset reconstruction, followed by the separately recorded uniform scale, matches the saved OBJ with RMS coordinate error `8.593152182606011e-15` and maximum vertex error `1.145853433319398e-13` (`allclose` at `1e-12`: true).

The TorchScript oracle comparison is evidence of the existing ufbx offset equivalence only: RMS coordinate error `1.2469606955601551e-05`, maximum vertex error `0.00015632882597533848`. The production reconstruction contract remains ufbx base vertices plus linear offsets and the separate uniform scale.

## Honest conclusion

The optimizer, independent height scaling, exact section extraction, candidate OBJ generation, and ufbx-only reconstruction all completed. The requested body circumference fit did not pass. This file must not be treated as a final body authority or as an anatomically validated result.
