# ufbx MHR LOD1 strict extractor run result

Run date: 2026-08-25  
Result: **PASS**

The earlier `UFBX-LOD1-EXTRACTOR-PLAN.md` records the pre-download design state. This file records the subsequent real compile and extraction requested by the main agent.

## Fixed inputs

- ufbx clone: `artifacts/third-party-downloads/ufbx-v0.23.0`
- HEAD: `fcc5d6ba444cfd3eb80677dba5e37e493941abe5`
- Git status: clean
- Compiler: MSVC x64 `19.51.36252.0`
- MHR input SHA256: `D66FBCA815BCDE6532F728F1F63071003C5D43FF44F56E263A0807BAEC1AE055`

## Real command

```cmd
cmd.exe /d /c "D:\FlamebladeStudio\CodexProjects\2026-08-13\mohan-multisensory-vision\artifacts\pose-atlas-rebuild\2026-08-25\ufbx-lod1-extractor-agent-a\run-fixed-clone.cmd"
```

Outer exit code: `0`

Step exit codes:

- `vcvars`: `0`
- compile `ufbx.c`: `0`
- compile `extract_lod1.c` with `/W4 /WX`: `0`
- link: `0`
- extractor: `0`
- independent exact verifier: `0`
- compiler-version probe compile: `0`

The primary compile, link, extraction, and verification stderr files are all zero bytes. The `/Bv` compiler probe intentionally writes version details to its stderr stream and still returned exit code `0`.

## Extractor gates and output

- mesh element ID: `205`
- `vertices=18439`
- `faces=36874`
- `indices=110622`
- `reversed_winding=false`
- `ufbx_version=0.23.0`
- degenerate faces: `0`

Outputs:

- `run-fixed-clone/mhr-lod1.vertices.tsv`
  - bytes: `1,154,972`
  - rows: `18,439`
  - SHA256: `4C1C4828E4E8672B5B1AC9FF1E179FDAE1A7758A9595F934D6F254D404136C34`
- `run-fixed-clone/mhr-lod1.faces.tsv`
  - bytes: `807,149`
  - rows: `36,874`
  - SHA256: `9680016AECE8D43BA4FF621F57D045870FDD1E7DC78541173B1AB44A449465F0`
- `run-fixed-clone/extract_lod1.exe`
  - bytes: `561,152`
  - SHA256: `A26AF31C6306F6C6A6A6D6872BDC040791AFE8C6326043FFF1CF6F3662BC51F3`

## Independent exact comparison

The verifier read the raw binary FBX using the existing MHR MIT topology helper and compared it with the ufbx TSV output:

- vertex row IDs exact: `true`
- face row IDs exact: `true`
- all vertex coordinates survive TSV round-trip exactly: `true`
- all face indices and face order exact: `true`
- vertex shape: `[18439, 3]`
- face shape: `[36874, 3]`
- face index range: `0..18438`

Canonical evidence is `run-fixed-clone/run-evidence.json`, SHA256 `75998A50A7904DEB5BED6B38DF52716F1890C41E81F3BB8F7B9D2DD96177E22D` at generation time. No formal asset directory or main-agent artifact was modified.
