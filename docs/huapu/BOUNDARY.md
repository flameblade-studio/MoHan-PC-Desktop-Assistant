# 炎劍畫譜邊界／炎剑画谱边界／Flameblade Huapu Boundary／炎剣画譜の境界

狀態／状态／Status／状態：H1 repository-internal extraction boundary, 2026-10-08.

## 路徑清冊／路径清册／Path inventory／パス一覧

分類代碼／分类代码／Class codes／分類コード：

- `C`：畫譜核心候選或已完成的中立核心／画谱核心候选或已完成的中立核心／product-neutral Huapu core or core candidate／製品中立な画譜コアまたは候補。
- `A`：墨寒設定、契約或 adapter／墨寒设置、契约或 adapter／MoHan configuration, contract, or adapter／墨寒の設定、契約、adapter。
- `S`：留在墨寒的產品殼／留在墨寒的产品壳／MoHan product shell／墨寒に残す製品シェル。

`C` candidate means that extraction still requires injected paths, schemas, dimensions, and output policy. It does not claim that every candidate module is already portable.

| Path | Class | Boundary note |
|---|:---:|---|
| `tools/art_pipeline/__init__.py` | C | Package marker; future exports stay product-neutral. |
| `tools/art_pipeline/align_ref_to_base.py` | C | Image alignment algorithm; dimensions and naming become settings. |
| `tools/art_pipeline/align_to_template.py` | C | Template alignment algorithm; reference policy is injected. |
| `tools/art_pipeline/approved_asset_install.py` | A | Thin MoHan-compatible facade over `huapu.approved_install`. |
| `tools/art_pipeline/approved_cosmetics.py` | A | MoHan cosmetic approval schemas and paths. |
| `tools/art_pipeline/assemble_set.py` | C | Set assembly algorithm; asset roles become settings. |
| `tools/art_pipeline/consolidate_partitions.py` | A | Current reviewed-partition names and output contract are MoHan-owned. |
| `tools/art_pipeline/constants.py` | A | Current MoHan canvases, colors, partitions, and path constants. |
| `tools/art_pipeline/cosmetic_residual.py` | C | Generic pixel residual calculation. |
| `tools/art_pipeline/derive_variants.py` | C | Generic image derivation with injected variant policy. |
| `tools/art_pipeline/extract_layers.py` | C | Generic layer extraction with injected partition contract. |
| `tools/art_pipeline/flatten_magenta.py` | C | Generic image cleanup operation. |
| `tools/art_pipeline/four_look_makeup_pack.py` | A | Four approved MoHan makeup looks and outfit-pack policy. |
| `tools/art_pipeline/image_ops.py` | C | Shared image operations. |
| `tools/art_pipeline/integrate_detachable_halfbody.py` | A | MoHan detachable half-body layout and runtime contract. |
| `tools/art_pipeline/make_ref_crops.py` | C | Generic crop generation with injected regions. |
| `tools/art_pipeline/MATERIAL_REGISTRATION.md` | A | MoHan material-registration operating record. |
| `tools/art_pipeline/material_registration.py` | A | Current registration schema and repository paths. |
| `tools/art_pipeline/native_cosmetic_palette.py` | A | MoHan native palette authority. |
| `tools/art_pipeline/native_identity_guard.py` | A | MoHan identity geometry and owner-approved thresholds. |
| `tools/art_pipeline/output_guard.py` | A | Current output roots and MoHan evidence contract. |
| `tools/art_pipeline/partition_coverage.py` | A | Current MoHan reviewed-partition coverage. |
| `tools/art_pipeline/partition_layers.py` | C | Generic partitioning algorithm with injected labels and order. |
| `tools/art_pipeline/PARTITION_REVIEW.md` | A | MoHan review procedure and accepted regions. |
| `tools/art_pipeline/qc_drift.py` | C | Generic before/after drift measurement. |
| `tools/art_pipeline/README.md` | A | Current MoHan pipeline guide; future Huapu guide is separate. |
| `tools/art_pipeline/references.py` | C | Generic reference-image data types. |
| `tools/art_pipeline/render_detachable_runtime_audit.py` | A | MoHan detachable runtime composition adapter. |
| `tools/art_pipeline/REVIEWED_PARTITIONS.md` | A | Canonical MoHan asset contract; it is data/configuration, not neutral code. |
| `tools/art_pipeline/reviewed_partitions.py` | A | Parser for the current MoHan reviewed-partition authority. |
| `tools/art_pipeline/source_bound_identity.py` | A | MoHan source-bound identity policy. |
| `tools/art_pipeline/source_bound_integrate.py` | A | MoHan source-bound integration workflow. |
| `tools/art_pipeline/source_bound_makeup.py` | A | MoHan makeup authority and slots. |
| `tools/art_pipeline/source_bound_makeup_pack.py` | A | MoHan outfit-pack assembly policy. |
| `tools/art_pipeline/source_bound_manifest.py` | A | Current source-bound schema. |
| `tools/art_pipeline/source_bound_material_guard.py` | A | MoHan material constraints. |
| `tools/art_pipeline/source_bound_pack_scope.py` | A | MoHan pack and approval scope. |
| `tools/art_pipeline/SOURCE_BOUND_PREVIEW.md` | A | MoHan preview operating record. |
| `tools/art_pipeline/source_bound_preview.py` | A | MoHan preview configuration. |
| `tools/art_pipeline/source_bound_reference.py` | A | MoHan source authority adapter. |
| `tools/art_pipeline/source_bound_stage.py` | A | MoHan staging layout and evidence paths. |
| `tools/art_pipeline/test_output_guard.py` | A | Co-located tests for the current MoHan output contract. |
| `tools/art_pipeline/vision.py` | C | Generic computer-vision helpers. |
| `huapu/**` | C | Implemented product-neutral APIs; imports are architecture-gated. |
| `tools/build_character_inventory.py` | A | Thin CLI; MoHan scan rules live in `tools/mohan_character_inventory.py`. |
| `tools/build_character_pack.py` | A | Thin CLI and MoHan build settings over `huapu.character_pack_builder`. |
| `tools/verify_character_pack_lock.py` | A | Thin CLI and private MoHan release settings over `huapu.character_pack_lock`. |
| `tools/fetch_character_pack.py` | S | Private repository transport, token handling, and installation policy. |
| `tools/audit_pose_atlas_working.py` | A | Thin hand-evidence adapter over `huapu.pose_audit`. |
| `tools/check_pose_atlas_release.py` | A | Thin CLI over `huapu.pose_release`; runtime composition is isolated in `tools/huapu_mohan_pose_release.py`. |
| `tools/golden_render.py` | A | MoHan headless-render adapter; settings are injectable, but renderer extraction remains. |
| `tools/capture_blink_layer_audit.py`, `capture_control_center_reference.py`, `capture_eye_alignment_preview.py`, `capture_first_run_wizard.py`, `capture_media_contract.py`, `capture_motion_transition_audit.py`, `capture_mouth_continuity_preview.py`, `capture_mouth_layer_audit.py`, `capture_readme_media.py`, `capture_startup_opacity_preview.py`, `capture_v120_flagship_preview.py`, `tachyon_capture.py` | S | Complete product UI, README, onboarding, dashboard, and marketing capture family. |
| `tools/audit_face_layer_asymmetry.py`, `audit_full_body_layer_pack.py`, `audit_layered_full_body_semantics.py`, `audit_pose_atlas_identity.py`, `audit_pose_atlas_working.py`, `audit_profile_nose_lip_contract.py`, `audit_profile_source_candidate.py`, `audit_yaw000_golden_template.py`, `audit_yaw000_layer_runtime.py` | A | Complete MoHan visual-asset audit family; neutral measurements move behind injected settings. |
| `tools/build_full_body_golden_batch.py`, `build_makeup_safe_regions.py`, `build_pose_atlas_identity_candidate.py`, `build_pose_atlas_identity_measurements.py`, `build_pose_atlas_release_assets.py`, `build_pose_contact_sheet.py`, `build_yaw000_golden_template.py`, `generate_expression_speech_assets.py`, `rebuild_pose_atlas_mouth_layers.py`, `recalibrate_mouth_authority.py`, `render_gesture_speech_assets.py`, `scaffold_makeup_pack_manifest.py` | A | Complete MoHan asset-generation and regression adapter family. |
| `tools/assemble_official_default_pack.py` | S | MoHan official product-pack assembly and release contents. |
| `tools/audit_public_release.py`, `audit_python315_compatibility.py`, `audit_python315_idioms.py`, `audit_speech_runtime_chain.py` | S | Product and code release gates, not character-asset management. |
| `tools/check_python_licenses.py`, `tools/quality_licenses.json` | S | Python dependency release policy, distinct from character-asset licensing. |
| `tests/golden/golden-manifest.json` | A | MoHan's approved 352-cell regression configuration. |
| `docs/release-evidence/**` | A | Scope-bound MoHan evidence; never treated as blanket distribution permission. |

## 繁體中文

### 已建立的核心

採用 `huapu/` 作為套件名，因為「炎劍畫譜」已由擁有者核定，短名稱可在下一工作包原樣搬到獨立 repository。套件只依賴標準函式庫與公開的 `domain.character_pack` 契約；它不得匯入 presentation、application、infrastructure、integrations、其他 domain 私有模組或 `tools`。

公開 API 分為：`SchemaVersion` 與 `HUAPU_API_VERSION`；`FileDigest`、`digest_file`、`sha256_bytes`；`Receipt` 與 deterministic receipt renderer；`AssetInventoryConfig`、`AssetSpec`、`build_asset_inventory`；呼叫端注入的 `LicensePolicy` 與白名單檢查；`CharacterPackBuildSettings`／builder；`CharacterPackLockSettings`／load、verify、update；以及唯一視覺邊界 `HeadlessRenderer` Protocol。設定決定 schema、角色 ID、根目錄、媒體型別、語言、引擎版本、授權分類、release repository 與 tag；核心沒有墨寒 fallback。

### 相容入口與未完成項目

既有六個命令／模組保留原名稱、函式簽章、CLI 參數、退出碼與輸出標記，改為薄入口。墨寒預設仍由 adapter 注入，所以現有 CI 與 workflow 不必改。`golden_render.py` 雖已可讀角色設定，仍直接組合墨寒 renderer；capture 工具仍建立產品 widget。它們留在墨寒 adapter／產品殼，直到 headless renderer 可完整覆蓋 352 格、核准與快取語意；本包不以介面雛形冒充完成搬移。

角色素材授權與 DLC 關係仍待擁有者決定。`huapu.licenses` 只執行呼叫端提供的 allowlist；`owner_decision_pending` 不會自動變成可公開或可再散布。墨寒角色包維持私有、可獨立下載的既有裁定。

## 简体中文

### 已建立的核心

采用 `huapu/` 作为包名，因为“炎剑画谱”已经由所有者核定，短名称可在下一工作包原样移到独立 repository。该包只依赖标准库与公开的 `domain.character_pack` 契约；不得导入 presentation、application、infrastructure、integrations、其他 domain 私有模块或 `tools`。

公开 API 包括：`SchemaVersion` 与 `HUAPU_API_VERSION`；`FileDigest`、`digest_file`、`sha256_bytes`；`Receipt` 与确定性 receipt renderer；`AssetInventoryConfig`、`AssetSpec`、`build_asset_inventory`；调用方注入的 `LicensePolicy` 与白名单检查；`CharacterPackBuildSettings`／builder；`CharacterPackLockSettings`／load、verify、update；以及唯一视觉边界 `HeadlessRenderer` Protocol。schema、角色 ID、根目录、媒体类型、语言、引擎版本、授权分类、release repository 与 tag 均由设置提供；核心没有墨寒 fallback。

### 兼容入口与未完成项目

现有六个命令／模块保留原名称、函数签名、CLI 参数、退出码与输出标记，并改成薄入口。墨寒默认值仍由 adapter 注入，因此现有 CI 与 workflow 无需修改。`golden_render.py` 虽可读取角色设置，仍直接组合墨寒 renderer；capture 工具仍建立产品 widget。它们保留在墨寒 adapter／产品壳，直到 headless renderer 完整覆盖 352 格、批准与缓存语义；本工作包不会把接口雏形描述为已完成搬移。

角色素材授权与 DLC 关系仍待所有者决定。`huapu.licenses` 只执行调用方提供的 allowlist；`owner_decision_pending` 不会自动变成可公开或可再分发。墨寒角色包继续遵循私有、可独立下载的既有决定。

## English

### Established core

The package is named `huapu/` because the owner approved Flameblade Huapu as the product name, and the short import can move unchanged in the next repository-extraction package. It depends only on the standard library and the public `domain.character_pack` contract. It must not import presentation, application, infrastructure, integrations, other private domain modules, or `tools`.

The public APIs are `SchemaVersion` and `HUAPU_API_VERSION`; `FileDigest`, `digest_file`, and `sha256_bytes`; `Receipt` and deterministic receipt rendering; `AssetInventoryConfig`, `AssetSpec`, and `build_asset_inventory`; caller-injected `LicensePolicy` allowlist checks; `CharacterPackBuildSettings` and the builder; `CharacterPackLockSettings` with load, verify, and update; and the sole visual boundary, the `HeadlessRenderer` Protocol. Settings own schemas, character IDs, roots, media types, languages, engine versions, license classification, release repositories, and tags. The core has no MoHan fallback.

### Compatibility entries and remaining work

Six existing commands or modules retain their names, function signatures, CLI arguments, exit codes, and output markers as thin entries. MoHan defaults are injected by adapters, so current CI and workflows remain unchanged. Although `golden_render.py` reads character settings, it still composes MoHan renderers directly, and capture tools still construct product widgets. They remain MoHan adapters or product shell until the headless renderer covers all 352 cells plus approval and cache semantics. This package does not present a Protocol scaffold as a completed renderer extraction.

Character-asset licensing and the DLC relationship remain owner decisions. `huapu.licenses` enforces only a caller-supplied allowlist; `owner_decision_pending` never becomes permission to publish or redistribute. The existing decision that the independently downloadable MoHan pack lives in a private repository remains unchanged.

## 日本語

### 構築済みのコア

所有者が「炎剣画譜」を正式名称として承認しており、次の repository 分離作業でも短い import 名を変更せず使えるため、package 名を `huapu/` とします。この package は標準ライブラリと公開された `domain.character_pack` 契約だけに依存します。presentation、application、infrastructure、integrations、その他の非公開 domain module、`tools` を import しません。

公開 API は `SchemaVersion` と `HUAPU_API_VERSION`、`FileDigest`／`digest_file`／`sha256_bytes`、`Receipt` と決定的な receipt 出力、`AssetInventoryConfig`／`AssetSpec`／`build_asset_inventory`、呼出側が注入する `LicensePolicy` の allowlist 検査、`CharacterPackBuildSettings` と builder、`CharacterPackLockSettings` と load／verify／update、視覚処理の唯一の境界である `HeadlessRenderer` Protocol です。schema、character ID、root、media type、言語、engine version、license 分類、release repository、tag は設定側が所有し、コアには墨寒 fallback がありません。

### 互換入口と残作業

既存の六つの command／module は、名称、関数 signature、CLI 引数、終了コード、出力 marker を維持した薄い入口です。墨寒の既定値は adapter が注入するため、既存 CI と workflow の変更は不要です。`golden_render.py` は character 設定を読み込めますが、現在も墨寒 renderer を直接構成し、capture tool も製品 widget を生成します。headless renderer が 352 cell、承認、cache の意味をすべて扱えるまでは墨寒 adapter／製品シェルに残します。この作業では Protocol の雛形を renderer 分離完了とは扱いません。

character asset の license と DLC の関係は所有者の決定待ちです。`huapu.licenses` は呼出側が指定した allowlist だけを検査し、`owner_decision_pending` を公開や再配布の許可へ変更しません。独立 download 可能な墨寒 pack を private repository に置く既存決定も維持します。
