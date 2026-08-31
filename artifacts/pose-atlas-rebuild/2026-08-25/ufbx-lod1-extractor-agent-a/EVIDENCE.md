# Evidence record

## Official upstream reads

All upstream research was read-only. No archive or source file was downloaded.

- `https://github.com/ufbx/ufbx/tags` resolves `v0.23.0` to short SHA `fcc5d6b`.
- `https://github.com/ufbx/ufbx/commit/fcc5d6ba444cfd3eb80677dba5e37e493941abe5` provides the full commit.
- `https://github.com/ufbx/ufbx/blob/v0.23.0/LICENSE` contains Alternative A, MIT License.
- `https://github.com/ufbx/ufbx/blob/v0.23.0/ufbx.h` reports version `0.23.0`.
- `https://ufbx.github.io/elements/meshes/` documents logical vertices, face corner indices, vertex attributes, and `ufbx_triangulate_face()`.

## Local commands and results

Input identity command:

```powershell
Get-Item -LiteralPath $fbx
Get-FileHash -Algorithm SHA256 -LiteralPath $fbx
Format-Hex -LiteralPath $fbx -Count 32
```

Exit code: `0`

Result:

```text
Length=7884560
SHA256=D66FBCA815BCDE6532F728F1F63071003C5D43FF44F56E263A0807BAEC1AE055
Header=Kaydara FBX Binary
FBX version=7700
```

Independent topology probe command used the existing MHR MIT repository's `web-viewer/tools/build_lod_topology.py` reader through the InstantMesh Python environment. It selected the geometry whose `Vertices` array contained exactly 18,439 control points.

Exit code: `0`

Result:

```text
shape=(36874, 3)
dtype=uint32
min=0 max=18438
degenerate=0
polygon_count=36874
polygon_size_hist={3: 36874}
corner_count=110622
```

The initial system-Python probe returned exit code `1` because that interpreter lacked NumPy. A second attempt with the InstantMesh Python initially returned exit code `1` because the dynamic import was not inserted into `sys.modules` before evaluating a dataclass. The corrected probe inserted the module into `sys.modules` and returned exit code `0`. Neither failed probe modified any file.

## What has not been tested

- ufbx has not been downloaded into this project.
- `extract_lod1.c` has not been compiled.
- No ufbx-based output exists yet.
- No full face-order comparison exists yet.
- No equality claim is made between static FBX rest vertices and the MHR TorchScript neutral output.
