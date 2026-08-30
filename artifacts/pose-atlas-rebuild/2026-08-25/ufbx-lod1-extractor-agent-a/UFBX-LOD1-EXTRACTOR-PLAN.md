# ufbx v0.23.0 MHR LOD1 extractor plan

Audit date: 2026-08-25  
Status: design and command draft only; ufbx was not downloaded or compiled in this task.

## Fixed upstream identity and license

- Project: `ufbx/ufbx`
- Official tag: `v0.23.0`
- Tag commit: `fcc5d6ba444cfd3eb80677dba5e37e493941abe5`
- Upstream repository: `https://github.com/ufbx/ufbx`
- Pinned tree: `https://github.com/ufbx/ufbx/tree/fcc5d6ba444cfd3eb80677dba5e37e493941abe5`
- Pinned header: `https://raw.githubusercontent.com/ufbx/ufbx/fcc5d6ba444cfd3eb80677dba5e37e493941abe5/ufbx.h`
- Pinned source: `https://raw.githubusercontent.com/ufbx/ufbx/fcc5d6ba444cfd3eb80677dba5e37e493941abe5/ufbx.c`
- Pinned license: `https://raw.githubusercontent.com/ufbx/ufbx/fcc5d6ba444cfd3eb80677dba5e37e493941abe5/LICENSE`
- License selection for this project: **Alternative A, MIT License**. Preserve the complete upstream `LICENSE` and explicitly record that Alternative A was selected. Do not rely on Alternative B/Unlicense for this pipeline.
- Required vendored files after separate download approval: `ufbx.c`, `ufbx.h`, and `LICENSE`. `misc/ufbx.natvis` is optional debugging metadata and is not required by the extractor.

Official evidence:

- The official tag list associates `v0.23.0` with short SHA `fcc5d6b` and date 2026-06-21.
- The official commit page resolves that tag to `fcc5d6ba444cfd3eb80677dba5e37e493941abe5`.
- The pinned header defines `UFBX_HEADER_VERSION` as `0.23.0`.
- The official setup says to copy `ufbx.h` and `ufbx.c`; `ufbx.c` compiles as C99/C++11 or later. The official platform list includes Windows MSVC x64/x86.
- The pinned `LICENSE` offers MIT as Alternative A and requires retaining its copyright and permission notice.

## Local MHR LOD1 facts

- Input: `D:\FlamebladeStudio\CodexProjects\2026-08-13\mohan-multisensory-vision\artifacts\third-party-downloads\MHR-v1.0.1-assets\extracted\assets\lod1.fbx`
- Bytes: `7,884,560`
- SHA256: `D66FBCA815BCDE6532F728F1F63071003C5D43FF44F56E263A0807BAEC1AE055`
- Header/version: binary FBX, version `7700`
- Expected MHR model output: `18,439 x 3` vertices.
- Geometry selected by exact control-point count: `18,439`.
- Polygon count: `36,874`; polygon-size histogram: `{3: 36874}`; corner count: `110,622`.
- Directly decoded control-point triangle indices span `0..18438`; no degenerate triangle was observed.

These topology facts were read with the existing MIT MHR repository's binary-FBX inspection helper only as an independent local probe. The production extractor below depends only on ufbx plus the C runtime.

## Minimal deterministic output contract

The extractor produces two UTF-8/ASCII-compatible, LF-delimited TSV files and emits a one-line JSON summary to stdout:

1. `<prefix>.vertices.tsv`
   - No header.
   - One row per control point in original `ufbx_mesh.vertices[]` order.
   - Columns: `vertex_id x y z`.
   - `vertex_id` is zero-based and must equal the row number.
   - Coordinates use `%.17g`, preserving round-trip precision for default double-precision `ufbx_real`.
   - Coordinates remain in mesh/control-point geometry space. No node/world transform, axis conversion, skinning, subdivision, or unit normalization is applied.
2. `<prefix>.faces.tsv`
   - No header.
   - One row per original triangle, in `ufbx_mesh.faces[]` order.
   - Columns: `face_id vertex_id_0 vertex_id_1 vertex_id_2`.
   - Vertex IDs come directly from `ufbx_mesh.vertex_indices[]`; they index the control-point rows above.
3. stdout JSON
   - Records mesh element ID, vertex/face/index counts, `reversed_winding`, and the verified ufbx version. Paths remain explicit in the invocation and evidence manifest, avoiding platform-path escaping inside this minimal C writer.

Downstream packaging may convert TSV to NumPy, but conversion must preserve row order and use `float64` for vertices plus `uint32` for faces. The TSV pair is deliberately simple, inspectable, dependency-free, and does not require zlib/NPZ code inside the trusted C extractor.

## Vertex-order and topology risks

MHR identity, blendshapes, skinning, segmentation, and LOD barycentric mappings are indexed against a fixed logical control-point order. The following operations would silently break that contract and are prohibited:

- Do not output per-corner `ufbx_get_vertex_vec3()` results as new vertices. UV/normal seams duplicate logical points.
- Do not call `ufbx_generate_indices()`, deduplicate, weld, sort, optimize, or reindex.
- Do not output `vertex_position.indices[]` as a new vertex order. Output `mesh->vertices[]` once, then map each face corner through `mesh->vertex_indices[]`.
- Do not use `skinned_position`, subdivision output, blendshape evaluation, or node `geometry_to_world` for the topology authority.
- Do not silently choose the first mesh. Require exactly one mesh with `num_vertices == 18439`; fail on zero or multiple matches.
- Do not silently triangulate N-gons. This exact MHR file currently contains only triangles. Fail if any face has a size other than three, because a triangulation policy could differ from MHR's existing mapping authority.
- Fail if `mesh->reversed_winding` is true until the resulting face orientation has been compared against the independent raw FBX topology.

Required validation before accepting output:

- ufbx header and linked source both report `0.23.0`.
- Input SHA256 matches the value above.
- Exact counts: vertices `18439`, faces `36874`, indices `110622`.
- Vertex IDs are all in `0..18438`; no degenerate face.
- Compare SHA256 of the complete `faces.tsv` against a separately decoded reference produced from the pinned MHR FBX.
- Compare sampled vertices and the full vertex bounding box against neutral MHR output only after documenting whether the MHR model and FBX share the same rest pose and coordinate scale. Equal count alone does not prove semantic equivalence.

## Windows/MSVC build and run

The command draft is `build-and-run.cmd.template`. It intentionally expects an already approved, pinned vendor directory containing `ufbx.c`, `ufbx.h`, and `LICENSE`; this task does not fetch them.

Compile the third-party translation unit separately at `/W3`, then compile the small extractor at `/W4 /WX`. This prevents weakening first-party warnings merely because a vendored single-file library has its own warning policy. Preserve stdout, stderr, outer process exit code, compiler version, source hashes, input hash, and output hashes in the eventual evidence directory.

## Current limitation

No claim is made that the draft has compiled or extracted MHR LOD1. ufbx is not present locally in the prepared directory, and no download was authorized in this task. The first real acceptance point is a build exit code 0 followed by extractor exit code 0 and an exact face-order comparison.
