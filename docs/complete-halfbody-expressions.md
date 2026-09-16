# Complete half-body expression sources

繁體中文：`complete_halfbody_expressions.py` 載入完整半身表情，`complete_halfbody_renderer.py` 保留目前畫面嘴型與眨眼的對應，`LayeredParametricFaceRenderer` 負責選擇新來源或既有路徑。衣裝、妝容與髮型仍由外觀合成器處理。此路徑正在 staging 驗證；目前沒有正式安裝的 manifest。原圖批准、接合批准、技術驗證及正式安裝必須分別記錄。

简体中文：完整半身表情由独立模块加载，显示中的嘴型保有自己的眨眼状态，衣装、妆容与发型仍独立合成。目前仅在 staging 验证，尚未正式安装。原图批准、接合批准、技术验证及正式安装分别记录。

English: Complete source frames preserve coherent facial expressions while appearance remains separately composed. The displayed speech endpoint owns its blink state even after the next mouth has been rendered. This optional path is being validated in staging; no production manifest is installed. Original-source acceptance, fitted-frame acceptance, runtime verification and formal installation are separate evidence states.

日本語：完全な半身表情を独立モジュールで読み込み、表示中の口形に対応する瞬きを保持します。衣装・化粧・髪型は別に合成します。現在は staging 検証のみで、正式 manifest は未導入です。原画承認、接合承認、技術検証、正式導入を個別に記録します。

## Installation contract

The optional manifest is `authority_dir/complete-expressions/manifest.json` with schema `mohan.complete-halfbody-expressions.v1`. An absent directory preserves legacy rendering. An existing directory with a missing or invalid manifest fails explicitly.

- `poses` may include the seven names in `detachable_halfbody_assets.POSES`.
- Every included pose requires nonempty `source_lineage`, four complete families (`neutral`, `small`, `a`, `o`), and all three eye states (`rest`, `half`, `closed`).
- Each source is a relative portable path and SHA-256 record for a 1254 × 1254, 8-bit RGBA PNG containing both transparent and visible pixels. Paths cannot leave the manifest directory. Source bytes are validated and frozen at load time.
- `expressions` explicitly maps existing expression names to a pose and mouth family. Every installed pose must expose all four families. Unknown expression names keep the legacy route; arbitrary emotions are not silently mapped to a neutral face.
- Removing this optional directory restores the legacy route after constructing a new renderer. Do not edit a loaded source set in place.

## Rendering and ownership

`render` selects a complete open-eye endpoint; zero mouth aperture selects its neutral family. Existing half-body animation timers request discrete blinking through `render_overlay`. Pixmap cache keys retain the displayed endpoint's pose and mouth family, including copies made by speech transitions. The context cache holds two full sets of seven poses × four mouth families × three eye states; decoded source images have a separate 24-image LRU limit.

Appearance adapters receive a copy of each source and the current eye state. Eye makeup slots are suppressed during half/closed blinking. Both combined `apply` and atomic `apply_animated` contracts are covered by focused adapter tests. Full wardrobe-store selection, old core-body restoration, all makeup looks and every appearance combination still require source-specific integration evidence; those tests alone do not establish that coverage.

Whole-head fitting must replace the old head's complete alpha footprint, including both ears. Merely overlaying a new head can expose old features outside its silhouette. In the approved front-crossed repair, native-body alpha is zero above row 620 and returns smoothly by row 638, before the canonical neck alpha fade begins at row 640. These coordinates are specific to that registered pose and must not be reused for other angles. The approved face pixels, neck below the join, and separate garment/hand layers are independently checked.

## Evidence and limitations

The canonical scope and source approvals are in `scratchpad/mohan-canonical-hairline-18/global-authority.json`; view/action coverage is in `scratchpad/mohan-canonical-global-progress-32/coverage.json`. The duplicate-ear repair and its owner approval are in `scratchpad/mohan-canonical-halfbody-ear-repair-50`.

The current source family provides SMALL, A and O. I/E/U use existing aliases and are not independently authored sources. No full 24-view / seven-action / four-makeup completeness or production readiness is implied by the frontal staging render.
