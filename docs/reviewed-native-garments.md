# Reviewed native garment composition

The current reviewed-garment registry installs the approved BCC8 `cheek-rest`
source through `infrastructure/reviewed_garment_assets.py` and
`ReviewedGarmentOverlayMixin`.

## Current installation

- Native body: `assets/expressions/cheek_native_bcc8.png`
- The installed body digest is canonical in the reviewed-garment registry and
  the formal runtime-preview receipt under `native_body_sha256`.
- Motion manifest: `assets/expressions/reviewed-garments/cheek-rest/motion/manifest.json`
- Motion `source_sha256` (BCC8):
  `bcc8def1ed4dd4cad179951a3733b31addaca97f81bd5211bebce5ea6ca368fe`
- Motion `native_body_sha256` is bound to the installed body record in the
  registry and formal runtime-preview receipt.
- Native motion has two registered endpoints: `closed.patch.rgba.png` and
  `speech.patch.rgba.png`.
- The motion manifest carries nine cosmetic layers: `rest`, `closed`, and
  `speech`, each with `eyes`, `cheeks`, and `lips`.
- Makeup strengths are applied once: bare `0`, light `0.55`, and classic `1`, matching the other half-body routes. The 2026-09-13 correction strengthens source-bound eye definition and blush; current evidence is in `scratchpad/halfbody-makeup-consistency-20260913-01/`.

The renderer selects the native body before the legacy face rig and old mouth
source. It paints the selected mouth endpoint before makeup, so lip cosmetics
follow the active mouth state. A closed blink replaces only the registered eye
patch on the current frame and preserves the existing mouth and clothing.
When the active clothing or makeup state changes, `_refresh_state` clears the
shared native frame and closed-eye caches so removing makeup can restore the
bare frame.

## Approved sources and preservation

The owner-approved source extension records “三項都採用” for the new closed
eyelids, the gently parted speaking mouth, and the matching black tank
underlying body. The record is
`scratchpad/cheek-unified-bare-review-20260912-01/extended-source-approval.json`.
The formal pre-install files are preserved under
`scratchpad/cheek-approved-formal-integration-20260912-01/before-bcc8-install/`.

The formal product-renderer preview is recorded in
`scratchpad/cheek-approved-formal-integration-20260912-01/bcc8-runtime-preview/receipt.json`
and covers 24 combinations: four motion states, three makeup levels, and two
clothing selections.

## Boundaries

- Every manifest pose requires `native_source_file`, a single PNG basename in
  the expression directory, and the exact `native_source_sha256`. Missing or
  changed input fails loading rather than selecting an older face silently.
- `ReviewedGarmentOverlayMixin.native_neutral` selects the pinned native pose
  before the old face rig. Identity does not depend on the garment selection.
- The manifest garment selection remains exact. A grayscale body visibility
  mask and ordered garment, horizontal hand, and foreground cuff RGBA layers
  are composed at the native 1254 canvas. No gray-background portrait is used
  as an installed garment or complete body.
- Registered facial motion is painted after the native base. Custom appearance
  remains in the normal depth pipeline. Source snapshots and caller frames
  remain unchanged during rendering.
- The other newly recovered approved dressed sources remain review candidates.
  Their three visible partitions do not provide hidden anatomy. They cannot
  be substituted for a complete detachable body or for registered eye/mouth
  endpoints from a different face.

## Authority and evidence

The 2026-09-07 approved bare identity and later same-source dressed approvals
remain the authority for the other recovered candidates. Pose names and
matching dimensions alone do not establish identity. The owner's statement,
“左二一致，採用這個托腮來源”, adopts the BCC8 face in
`dressed-cheek-rest-01/dressed-cheek-rest.png`, SHA-256
`bcc8def1ed4dd4cad179951a3733b31addaca97f81bd5211bebce5ea6ca368fe`.
Its pinned approval and visible partitions are in
`scratchpad/cheek-unified-bare-review-20260912-01/`; this source is now the
formal `cheek-rest` native body. The exact installed body digest remains
canonical in the registry and formal runtime-preview receipt.

Current receipts, owner statements, source comparisons, 24 formal
product-renderer frames, and focused validation are in
`scratchpad/cheek-approved-formal-integration-20260912-01/`.
The visual review page is
`scratchpad/existing-material-repair-review-20260912-01/review.html`.

## Validation scope

### Native foundation contract (2026-09-13)

`mohan.reviewed-pose-motion.v2` binds four slots for each native state:
foundation, eyes, cheeks and lips. Version 1 still requires its original three
slots. Version 2 requires a complete foundation layer with the same PNG, source
and digest checks as the other layers; changing the schema alone is insufficient.
Foundation is painted before pigment. A closed eye patch receives its own
foundation and eye pigment with SourceAtop before covering the current frame,
so it preserves both the patch alpha and the current speaking mouth.

For version 1 and version 2, global intensity, the light multiplier of 0.55, and individual slot intensity
each apply once. Zero restores the untouched native source. This runtime
capability does not approve new makeup artwork or replace an installed version
1 manifest. The seven-pose source catalog and current visual candidates are in
`scratchpad/halfbody-makeup-consistency-20260913-01/`.

### Independently authored makeup variants (version 3)

**繁體中文。** `mohan.reviewed-pose-motion.v3` 的 `cosmetics` 先依
`light`／`classic` 選擇，再依 `rest`／`closed`／`speech` 選取四個槽位。
兩款使用各自的素材，v3 不再乘上舊版淡妝係數 `0.55`；全域與各槽位濃度
各套用一次。閉眼遮片使用自己的底妝與眼妝，保留當下說話的嘴型。

**简体中文。** v3 为淡妆与标准妆分别保存完整的原生状态与四槽素材，
不再用同一张标准妆乘 `0.55`。旧版 v1／v2 的读取和行为保持兼容。

**English.** Version 3 requires complete `light` and `classic` native-state
maps, each with foundation, eyes, cheeks and lips. It selects a distinct authored
variant before applying global and slot intensities once. The legacy light
multiplier remains confined to version 1 and version 2. Immutable source hashes,
path containment and complete-state checks still apply. Source-bound exasperated
appearance version 3 provides the corresponding variant/state/slot contract for
its four mouth endpoints. Supporting this schema does not promote new artwork.

**日本語。** v3 は薄化粧・標準化粧それぞれに原生状態別の 4 レイヤーを
持ち、旧版の `0.55` 係数を適用しません。全体と各部位の濃度は一度ずつ
適用し、閉眼パッチは独自のベースと目元を使います。新素材の承認とは別です。

`tests/test_reviewed_garment_assets.py` covers decoding, exact source hashes,
path containment, input drift and layer order. The overlay and native face
rendering tests cover outfit independence, native face selection, motion
ordering and error propagation. The facade cycle/size gate passed after
lowering the animation baseline from 1153 to 1152 lines.

The formal runtime-preview receipt records 24 product-renderer frames,
makeup round-trip restoration, alpha preservation, 19,728 changed pixels for
light makeup, and 20,167 for classic makeup.
The installed motion currently provides one gently parted speaking-mouth
endpoint and one closed-eye endpoint. Full `CompanionWindow` interaction and
complete physics animation remain unverified; this documentation does not
approve other candidates or a release.
