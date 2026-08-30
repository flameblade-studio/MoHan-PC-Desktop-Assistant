# MHR zero-neutral horizontal section candidates

Run date: 2026-08-25  
Result: geometry extraction **PASS**; anatomical validation **NOT PERFORMED**.

## Command and exit

```cmd
cmd.exe /d /c "D:\FlamebladeStudio\CodexProjects\2026-08-13\mohan-multisensory-vision\artifacts\pose-atlas-rebuild\2026-08-25\ufbx-lod1-extractor-agent-a\run-slice-candidates.cmd"
```

- Outer exit code: `0`
- Tool exit-code file: `0`
- stderr: `0 bytes`

## Inputs

- Exact ufbx vertices TSV, 18,439 indexed rows.
- Exact ufbx faces TSV, 36,874 indexed triangle rows.
- MHR TorchScript zero-neutral vertices preserved in the previously generated neutral OBJ, 18,439 rows.
- Candidate heights copied exactly from the existing pointcloud contact-sheet summary.

No garment mesh was supplied. `clothing_geometry_present=false` means only that this source is the neutral MHR body geometry; it is not a clothing-segmentation result.

## Candidate sections

All circumferences below are in MHR model units. They must not be described as certified tape-measure centimeters until a separate scale and landmark contract is validated.

| Candidate | Plane Y | Closed loops | Open components | Largest torso loop perimeter | Limb/hand-like secondary loops | Clothing geometry |
|---|---:|---:|---:|---:|---:|---|
| bust | 127.725694924891 | 3 | 0 | 108.142983239990 | 2 | absent from source |
| underbust | 120.818436624110 | 3 | 0 | 93.964444932845 | 2 | absent from source |
| waist | 107.003920022547 | 5 | 0 | 101.310755500302 | 4 | absent from source |
| hip | 86.282145120204 | 1 | 0 | 108.936265847844 | 0 | absent from source |

Interpretation limits:

- Bust and underbust planes intersect the torso plus two arm sections.
- Waist intersects the torso plus four hand/finger or arm-related sections in the zero-pose geometry.
- Hip produces one central closed loop and no detected limb-like secondary loop.
- The largest-perimeter closed component is reported as the torso candidate. This is a geometric heuristic, not an anatomical landmark detector.
- All four planes had zero open components, zero coplanar edges, and zero ambiguous triangle intersections for this exact mesh and these exact heights.
- The source proportions are the zero-parameter MHR neutral body, not the approved dressed MoHan artwork and not the requested 168/54/86/71/62/90 fitted body.

## Outputs

- `cross-sections/section-report.json`: numeric report and provenance.
- `cross-sections/section-loops.json`: complete closed-loop X/Z coordinates.
- `cross-sections/mhr-horizontal-section-candidates.png`: front-height and top-loop overlay, clearly labelled as candidate geometry only.
- `cross-sections/stdout.json`, `stderr.txt`, and `exit-code.txt`: real command evidence.
