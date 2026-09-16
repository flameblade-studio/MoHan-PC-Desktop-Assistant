# 已審核原生衣裝合成／已审核原生衣装合成／Reviewed native garment composition／審査済みネイティブ衣装の合成

## 繁體中文

目前的已審核衣裝登錄表透過 `infrastructure/reviewed_garment_assets.py` 與 `ReviewedGarmentOverlayMixin` 安裝已批准的 BCC8 `cheek-rest` 來源。

### 目前安裝

- 原生身體：`assets/expressions/cheek_native_bcc8.png`
- 已安裝身體的雜湊以已審核衣裝登錄表與正式執行期預覽收據的 `native_body_sha256` 為準。
- 動作 manifest：`assets/expressions/reviewed-garments/cheek-rest/motion/manifest.json`
- 動作 `source_sha256`（BCC8）：`bcc8def1ed4dd4cad179951a3733b31addaca97f81bd5211bebce5ea6ca368fe`
- 動作 `native_body_sha256` 綁定登錄表與正式執行期預覽收據中的已安裝身體紀錄。
- 原生動作有兩個已配準端點：`closed.patch.rgba.png` 與 `speech.patch.rgba.png`。
- 動作 manifest 帶九個妝容圖層：`rest`、`closed`、`speech` 各自的 `eyes`、`cheeks`、`lips`。
- 妝容濃度只套用一次：素顏 `0`、淡妝 `0.55`、標準妝 `1`，與其他半身路徑一致。2026-09-13 的修正加強了來源綁定的眼部輪廓與腮紅；目前證據在 `scratchpad/halfbody-makeup-consistency-20260913-01/`。

渲染器在舊臉部 rig 與舊嘴型來源之前先選擇原生身體。它先畫出選定的嘴型端點再上妝，因此唇妝跟隨目前的嘴型狀態。閉眼眨眼只替換目前畫面上已配準的眼部貼片，保留既有嘴型與衣物。當有效衣物或妝容狀態改變時，`_refresh_state` 清除共用的原生畫面與閉眼快取，使卸妝能還原素顏畫面。

### 已批准來源與保留

擁有者批准的來源延伸紀錄「三項都採用」：新的閉眼眼皮、微張的說話嘴型，以及對應的黑色背心底層身體。紀錄位於 `scratchpad/cheek-unified-bare-review-20260912-01/extended-source-approval.json`。正式安裝前的檔案保存在 `scratchpad/cheek-approved-formal-integration-20260912-01/before-bcc8-install/`。

正式產品渲染器預覽記錄在 `scratchpad/cheek-approved-formal-integration-20260912-01/bcc8-runtime-preview/receipt.json`，涵蓋 24 種組合：四種動作狀態、三種妝容濃度與兩種衣物選擇。

### 邊界

- 每個 manifest 姿勢都需要 `native_source_file`（表情目錄內的單一 PNG 檔名）與精確的 `native_source_sha256`。輸入缺失或改變時載入失敗，不會默默選用較舊的臉。
- `ReviewedGarmentOverlayMixin.native_neutral` 在舊臉部 rig 之前選擇釘住的原生姿勢。身分不依賴衣物選擇。
- manifest 的衣物選擇保持精確。灰階身體可見度遮罩，以及依序的衣物、水平手部與前景袖口 RGBA 圖層，在原生 1254 畫布上合成。不以灰底肖像作為已安裝衣物或完整身體。
- 已配準的臉部動作在原生底圖之後繪製。自訂外觀維持在一般深度管線。渲染期間來源快照與呼叫端畫面保持不變。
- 其他新近復原、已批准的著裝來源仍是審閱候選。它們的三個可見分區不提供被遮住的解剖結構，不能替代完整的可拆身體，也不能替代來自不同臉的已配準眼／嘴端點。

### 權威與證據

2026-09-07 批准的素顏身分與後續同來源著裝批准，仍是其他復原候選的權威。只憑姿勢名稱與尺寸相符不能確立身分。擁有者的「左二一致，採用這個托腮來源」採用了 `dressed-cheek-rest-01/dressed-cheek-rest.png` 中的 BCC8 臉，SHA-256 為 `bcc8def1ed4dd4cad179951a3733b31addaca97f81bd5211bebce5ea6ca368fe`。其釘住的批准與可見分區位於 `scratchpad/cheek-unified-bare-review-20260912-01/`；這個來源現在是正式的 `cheek-rest` 原生身體。精確的已安裝身體雜湊以登錄表與正式執行期預覽收據為準。

目前的收據、擁有者陳述、來源比較、24 張正式產品渲染器畫面與聚焦驗證位於 `scratchpad/cheek-approved-formal-integration-20260912-01/`。視覺審閱頁面為 `scratchpad/existing-material-repair-review-20260912-01/review.html`。

### 驗證範圍

#### 原生底妝契約（2026-09-13）

`mohan.reviewed-pose-motion.v2` 為每個原生狀態綁定四個槽位：底妝、眼、頰、唇。第一版仍要求原本的三個槽位。第二版要求完整的底妝圖層，並套用與其他圖層相同的 PNG、來源與雜湊檢查；只改 schema 並不足夠。底妝在色彩之前繪製。閉眼貼片先以 SourceAtop 套用自己的底妝與眼妝，再覆蓋到目前畫面，因此同時保留貼片 alpha 與目前的說話嘴型。

第一版與第二版的全域濃度、淡妝倍率 `0.55` 與各槽位濃度各套用一次。零會還原未修改的原生來源。這項執行期能力不批准新的妝容美術，也不取代已安裝的第一版 manifest。七姿勢來源目錄與目前的視覺候選位於 `scratchpad/halfbody-makeup-consistency-20260913-01/`。

#### 獨立製作的妝容變體（第三版）

`mohan.reviewed-pose-motion.v3` 的 `cosmetics` 先依 `light`／`classic` 選擇，再依 `rest`／`closed`／`speech` 選取四個槽位。兩款使用各自的素材，第三版不再乘上舊版淡妝係數 `0.55`；全域與各槽位濃度各套用一次。閉眼貼片使用自己的底妝與眼妝，保留當下說話的嘴型。不可變的來源雜湊、路徑包含與完整狀態檢查仍然適用。來源綁定的無奈外觀第三版為其四個嘴型端點提供對應的變體／狀態／槽位契約。支援這個 schema 不代表推廣新的美術。

`tests/test_reviewed_garment_assets.py` 涵蓋解碼、精確來源雜湊、路徑包含、輸入漂移與圖層順序。覆蓋層與原生臉部渲染測試涵蓋衣物獨立性、原生臉部選擇、動作順序與錯誤傳遞。動畫基準行數由 1153 降到 1152 後，外觀門面的循環／大小閘門通過。

正式執行期預覽收據記錄 24 張產品渲染器畫面、妝容往返還原、alpha 保留、淡妝 19,728 個變更像素與標準妝 20,167 個變更像素。已安裝動作目前提供一個微張的說話嘴型端點與一個閉眼端點。完整的 `CompanionWindow` 互動與完整物理動畫尚未驗證；本文件不批准其他候選或發行。

## 简体中文

目前的已审核衣装登录表通过 `infrastructure/reviewed_garment_assets.py` 与 `ReviewedGarmentOverlayMixin` 安装已批准的 BCC8 `cheek-rest` 来源。

### 目前安装

- 原生身体：`assets/expressions/cheek_native_bcc8.png`
- 已安装身体的哈希以已审核衣装登录表与正式运行期预览收据的 `native_body_sha256` 为准。
- 动作 manifest：`assets/expressions/reviewed-garments/cheek-rest/motion/manifest.json`
- 动作 `source_sha256`（BCC8）：`bcc8def1ed4dd4cad179951a3733b31addaca97f81bd5211bebce5ea6ca368fe`
- 动作 `native_body_sha256` 绑定登录表与正式运行期预览收据中的已安装身体记录。
- 原生动作有两个已配准端点：`closed.patch.rgba.png` 与 `speech.patch.rgba.png`。
- 动作 manifest 带九个妆容图层：`rest`、`closed`、`speech` 各自的 `eyes`、`cheeks`、`lips`。
- 妆容浓度只应用一次：素颜 `0`、淡妆 `0.55`、标准妆 `1`，与其他半身路径一致。2026-09-13 的修正加强了来源绑定的眼部轮廓与腮红；目前证据在 `scratchpad/halfbody-makeup-consistency-20260913-01/`。

渲染器在旧脸部 rig 与旧嘴型来源之前先选择原生身体。它先画出选定的嘴型端点再上妆，因此唇妆跟随当前的嘴型状态。闭眼眨眼只替换当前画面上已配准的眼部贴片，保留既有嘴型与衣物。当有效衣物或妆容状态改变时，`_refresh_state` 清除共享的原生画面与闭眼缓存，使卸妆能还原素颜画面。

### 已批准来源与保留

所有者批准的来源延伸记录“三項都採用”：新的闭眼眼皮、微张的说话嘴型，以及对应的黑色背心底层身体。记录位于 `scratchpad/cheek-unified-bare-review-20260912-01/extended-source-approval.json`。正式安装前的文件保存在 `scratchpad/cheek-approved-formal-integration-20260912-01/before-bcc8-install/`。

正式产品渲染器预览记录在 `scratchpad/cheek-approved-formal-integration-20260912-01/bcc8-runtime-preview/receipt.json`，涵盖 24 种组合：四种动作状态、三种妆容浓度与两种衣物选择。

### 边界

- 每个 manifest 姿势都需要 `native_source_file`（表情目录内的单一 PNG 文件名）与精确的 `native_source_sha256`。输入缺失或改变时加载失败，不会默默选用较旧的脸。
- `ReviewedGarmentOverlayMixin.native_neutral` 在旧脸部 rig 之前选择钉住的原生姿势。身份不依赖衣物选择。
- manifest 的衣物选择保持精确。灰度身体可见度遮罩，以及依序的衣物、水平手部与前景袖口 RGBA 图层，在原生 1254 画布上合成。不以灰底肖像作为已安装衣物或完整身体。
- 已配准的脸部动作在原生底图之后绘制。自定义外观保持在一般深度管线。渲染期间来源快照与调用端画面保持不变。
- 其他新近复原、已批准的着装来源仍是审阅候选。它们的三个可见分区不提供被遮住的解剖结构，不能替代完整的可拆身体，也不能替代来自不同脸的已配准眼／嘴端点。

### 权威与证据

2026-09-07 批准的素颜身份与后续同来源着装批准，仍是其他复原候选的权威。只凭姿势名称与尺寸相符不能确立身份。所有者的“左二一致，採用這個托腮來源”采用了 `dressed-cheek-rest-01/dressed-cheek-rest.png` 中的 BCC8 脸，SHA-256 为 `bcc8def1ed4dd4cad179951a3733b31addaca97f81bd5211bebce5ea6ca368fe`。其钉住的批准与可见分区位于 `scratchpad/cheek-unified-bare-review-20260912-01/`；这个来源现在是正式的 `cheek-rest` 原生身体。精确的已安装身体哈希以登录表与正式运行期预览收据为准。

目前的收据、所有者陈述、来源比较、24 张正式产品渲染器画面与聚焦验证位于 `scratchpad/cheek-approved-formal-integration-20260912-01/`。视觉审阅页面为 `scratchpad/existing-material-repair-review-20260912-01/review.html`。

### 验证范围

#### 原生底妆契约（2026-09-13）

`mohan.reviewed-pose-motion.v2` 为每个原生状态绑定四个槽位：底妆、眼、颊、唇。第一版仍要求原本的三个槽位。第二版要求完整的底妆图层，并应用与其他图层相同的 PNG、来源与哈希检查；只改 schema 并不足够。底妆在色彩之前绘制。闭眼贴片先以 SourceAtop 应用自己的底妆与眼妆，再覆盖到当前画面，因此同时保留贴片 alpha 与当前的说话嘴型。

第一版与第二版的全局浓度、淡妆倍率 `0.55` 与各槽位浓度各应用一次。零会还原未修改的原生来源。这项运行期能力不批准新的妆容美术，也不取代已安装的第一版 manifest。七姿势来源目录与当前的视觉候选位于 `scratchpad/halfbody-makeup-consistency-20260913-01/`。

#### 独立制作的妆容变体（第三版）

`mohan.reviewed-pose-motion.v3` 的 `cosmetics` 先按 `light`／`classic` 选择，再按 `rest`／`closed`／`speech` 选取四个槽位。两款使用各自的素材，第三版不再乘上旧版淡妆系数 `0.55`；全局与各槽位浓度各应用一次。闭眼贴片使用自己的底妆与眼妆，保留当下说话的嘴型。不可变的来源哈希、路径包含与完整状态检查仍然适用。来源绑定的无奈外观第三版为其四个嘴型端点提供对应的变体／状态／槽位契约。支持这个 schema 不代表推广新的美术。

`tests/test_reviewed_garment_assets.py` 覆盖解码、精确来源哈希、路径包含、输入漂移与图层顺序。覆盖层与原生脸部渲染测试覆盖衣物独立性、原生脸部选择、动作顺序与错误传递。动画基准行数由 1153 降到 1152 后，外观门面的循环／大小关卡通过。

正式运行期预览收据记录 24 张产品渲染器画面、妆容往返还原、alpha 保留、淡妆 19,728 个变更像素与标准妆 20,167 个变更像素。已安装动作目前提供一个微张的说话嘴型端点与一个闭眼端点。完整的 `CompanionWindow` 交互与完整物理动画尚未验证；本文档不批准其他候选或发布。

## English

The current reviewed-garment registry installs the approved BCC8 `cheek-rest` source through `infrastructure/reviewed_garment_assets.py` and `ReviewedGarmentOverlayMixin`.

### Current installation

- Native body: `assets/expressions/cheek_native_bcc8.png`
- The installed body digest is canonical in the reviewed-garment registry and the formal runtime-preview receipt under `native_body_sha256`.
- Motion manifest: `assets/expressions/reviewed-garments/cheek-rest/motion/manifest.json`
- Motion `source_sha256` (BCC8): `bcc8def1ed4dd4cad179951a3733b31addaca97f81bd5211bebce5ea6ca368fe`
- Motion `native_body_sha256` is bound to the installed body record in the registry and the formal runtime-preview receipt.
- Native motion has two registered endpoints: `closed.patch.rgba.png` and `speech.patch.rgba.png`.
- The motion manifest carries nine cosmetic layers: `rest`, `closed` and `speech`, each with `eyes`, `cheeks` and `lips`.
- Makeup strengths are applied once: bare `0`, light `0.55` and classic `1`, matching the other half-body routes. The 2026-09-13 correction strengthens source-bound eye definition and blush; current evidence is in `scratchpad/halfbody-makeup-consistency-20260913-01/`.

The renderer selects the native body before the legacy face rig and the old mouth source. It paints the selected mouth endpoint before makeup, so lip cosmetics follow the active mouth state. A closed blink replaces only the registered eye patch on the current frame and preserves the existing mouth and clothing. When the active clothing or makeup state changes, `_refresh_state` clears the shared native frame and closed-eye caches so that removing makeup can restore the bare frame.

### Approved sources and preservation

The owner-approved source extension records “三項都採用” for the new closed eyelids, the gently parted speaking mouth and the matching black tank underlying body. The record is `scratchpad/cheek-unified-bare-review-20260912-01/extended-source-approval.json`. The formal pre-install files are preserved under `scratchpad/cheek-approved-formal-integration-20260912-01/before-bcc8-install/`.

The formal product-renderer preview is recorded in `scratchpad/cheek-approved-formal-integration-20260912-01/bcc8-runtime-preview/receipt.json` and covers 24 combinations: four motion states, three makeup levels and two clothing selections.

### Boundaries

- Every manifest pose requires `native_source_file`, a single PNG basename in the expression directory, and the exact `native_source_sha256`. Missing or changed input fails loading rather than selecting an older face silently.
- `ReviewedGarmentOverlayMixin.native_neutral` selects the pinned native pose before the old face rig. Identity does not depend on the garment selection.
- The manifest garment selection remains exact. A grayscale body visibility mask and ordered garment, horizontal hand and foreground cuff RGBA layers are composed at the native 1254 canvas. No gray-background portrait is used as an installed garment or complete body.
- Registered facial motion is painted after the native base. Custom appearance remains in the normal depth pipeline. Source snapshots and caller frames remain unchanged during rendering.
- The other newly recovered approved dressed sources remain review candidates. Their three visible partitions do not provide hidden anatomy. They cannot be substituted for a complete detachable body or for registered eye/mouth endpoints from a different face.

### Authority and evidence

The 2026-09-07 approved bare identity and the later same-source dressed approvals remain the authority for the other recovered candidates. Pose names and matching dimensions alone do not establish identity. The owner's statement “左二一致，採用這個托腮來源” adopts the BCC8 face in `dressed-cheek-rest-01/dressed-cheek-rest.png`, SHA-256 `bcc8def1ed4dd4cad179951a3733b31addaca97f81bd5211bebce5ea6ca368fe`. Its pinned approval and visible partitions are in `scratchpad/cheek-unified-bare-review-20260912-01/`; this source is now the formal `cheek-rest` native body. The exact installed body digest remains canonical in the registry and the formal runtime-preview receipt.

Current receipts, owner statements, source comparisons, 24 formal product-renderer frames and focused validation are in `scratchpad/cheek-approved-formal-integration-20260912-01/`. The visual review page is `scratchpad/existing-material-repair-review-20260912-01/review.html`.

### Validation scope

#### Native foundation contract (2026-09-13)

`mohan.reviewed-pose-motion.v2` binds four slots for each native state: foundation, eyes, cheeks and lips. Version 1 still requires its original three slots. Version 2 requires a complete foundation layer with the same PNG, source and digest checks as the other layers; changing the schema alone is insufficient. Foundation is painted before pigment. A closed eye patch receives its own foundation and eye pigment with SourceAtop before covering the current frame, so it preserves both the patch alpha and the current speaking mouth.

For version 1 and version 2, the global intensity, the light multiplier of `0.55` and each slot intensity apply once. Zero restores the untouched native source. This runtime capability does not approve new makeup artwork or replace an installed version 1 manifest. The seven-pose source catalog and the current visual candidates are in `scratchpad/halfbody-makeup-consistency-20260913-01/`.

#### Independently authored makeup variants (version 3)

The `cosmetics` of `mohan.reviewed-pose-motion.v3` select `light`／`classic` first, then the four slots for `rest`／`closed`／`speech`. Each look uses its own artwork, and version 3 no longer multiplies by the legacy light factor `0.55`; global and per-slot intensities apply once. The closed-eye patch uses its own foundation and eye pigment and preserves the current speaking mouth. Immutable source hashes, path containment and complete-state checks still apply. Source-bound exasperated appearance version 3 provides the corresponding variant/state/slot contract for its four mouth endpoints. Supporting this schema does not promote new artwork.

`tests/test_reviewed_garment_assets.py` covers decoding, exact source hashes, path containment, input drift and layer order. The overlay and native face rendering tests cover outfit independence, native face selection, motion ordering and error propagation. The facade cycle/size gate passed after lowering the animation baseline from 1153 to 1152 lines.

The formal runtime-preview receipt records 24 product-renderer frames, makeup round-trip restoration, alpha preservation, 19,728 changed pixels for light makeup and 20,167 for classic makeup. The installed motion currently provides one gently parted speaking-mouth endpoint and one closed-eye endpoint. Full `CompanionWindow` interaction and complete physics animation remain unverified; this documentation does not approve other candidates or a release.

## 日本語

現在の審査済み衣装レジストリは、`infrastructure/reviewed_garment_assets.py` と `ReviewedGarmentOverlayMixin` を通じて承認済みの BCC8 `cheek-rest` ソースを導入します。

### 現在の導入

- ネイティブボディ：`assets/expressions/cheek_native_bcc8.png`
- 導入済みボディのダイジェストは、審査済み衣装レジストリと正式なランタイムプレビュー receipt の `native_body_sha256` を正とします。
- モーション manifest：`assets/expressions/reviewed-garments/cheek-rest/motion/manifest.json`
- モーションの `source_sha256`（BCC8）：`bcc8def1ed4dd4cad179951a3733b31addaca97f81bd5211bebce5ea6ca368fe`
- モーションの `native_body_sha256` は、レジストリと正式なランタイムプレビュー receipt の導入済みボディ記録に束縛されます。
- ネイティブモーションには二つの登録済みエンドポイントがあります：`closed.patch.rgba.png` と `speech.patch.rgba.png`。
- モーション manifest は九つの化粧レイヤーを持ちます：`rest`、`closed`、`speech` それぞれの `eyes`、`cheeks`、`lips`。
- 化粧の強さは一度だけ適用します：素顔 `0`、薄化粧 `0.55`、標準化粧 `1` で、他の半身経路と一致します。2026-09-13 の修正はソース束縛の目元の輪郭と頬紅を強めました。現在の証拠は `scratchpad/halfbody-makeup-consistency-20260913-01/` にあります。

レンダラーは旧顔リグと旧口ソースより先にネイティブボディを選びます。選んだ口エンドポイントを化粧より先に描くため、唇の化粧は現在の口状態に追従します。閉眼の瞬きは現在のフレーム上の登録済み目パッチだけを置き換え、既存の口と衣服を保持します。有効な衣服または化粧状態が変わると、`_refresh_state` が共有ネイティブフレームと閉眼キャッシュを消去し、化粧を外せば素顔フレームへ戻れるようにします。

### 承認済みソースと保全

所有者承認のソース拡張は、新しい閉眼まぶた、軽く開いた発話の口、対応する黒いタンクトップの下地ボディについて「三項都採用」と記録しています。記録は `scratchpad/cheek-unified-bare-review-20260912-01/extended-source-approval.json` です。正式導入前のファイルは `scratchpad/cheek-approved-formal-integration-20260912-01/before-bcc8-install/` に保全されています。

正式な製品レンダラープレビューは `scratchpad/cheek-approved-formal-integration-20260912-01/bcc8-runtime-preview/receipt.json` に記録され、四つのモーション状態、三つの化粧レベル、二つの衣服選択の 24 通りを網羅します。

### 境界

- manifest の各ポーズには `native_source_file`（表情ディレクトリ内の単一 PNG ファイル名）と正確な `native_source_sha256` が必要です。入力が欠落または変更された場合は読み込みが失敗し、古い顔を黙って選ぶことはありません。
- `ReviewedGarmentOverlayMixin.native_neutral` は旧顔リグより先に固定されたネイティブポーズを選びます。同一性は衣装の選択に依存しません。
- manifest の衣装選択は正確なままです。グレースケールのボディ可視マスクと、順序付けされた衣装・水平の手・前景の袖口の RGBA レイヤーをネイティブ 1254 キャンバスで合成します。灰色背景の肖像を導入済み衣装や完全なボディとして使うことはありません。
- 登録済みの顔モーションはネイティブベースの後に描きます。カスタム外観は通常の深度パイプラインに留まります。描画中、ソースのスナップショットと呼び出し側フレームは変更されません。
- 新たに復元された他の承認済み着装ソースは審査候補のままです。その三つの可視パーティションは隠れた解剖構造を提供せず、完全な着脱可能ボディや別の顔の登録済み目／口エンドポイントの代替にはなりません。

### 権威と証拠

2026-09-07 に承認された素顔の同一性と、その後の同一ソースの着装承認が、他の復元候補の権威であり続けます。ポーズ名と寸法の一致だけでは同一性は確立しません。所有者の「左二一致，採用這個托腮來源」という発言により、`dressed-cheek-rest-01/dressed-cheek-rest.png` の BCC8 の顔、SHA-256 `bcc8def1ed4dd4cad179951a3733b31addaca97f81bd5211bebce5ea6ca368fe` が採用されました。その固定された承認と可視パーティションは `scratchpad/cheek-unified-bare-review-20260912-01/` にあり、このソースが現在の正式な `cheek-rest` ネイティブボディです。正確な導入済みボディのダイジェストはレジストリと正式なランタイムプレビュー receipt を正とします。

現在の receipt、所有者の発言、ソース比較、24 枚の正式な製品レンダラーフレーム、焦点を絞った検証は `scratchpad/cheek-approved-formal-integration-20260912-01/` にあります。視覚レビューページは `scratchpad/existing-material-repair-review-20260912-01/review.html` です。

### 検証範囲

#### ネイティブファンデーション契約（2026-09-13）

`mohan.reviewed-pose-motion.v2` は各ネイティブ状態にファンデーション、目、頬、唇の四つのスロットを束縛します。バージョン 1 は元の三つのスロットを引き続き要求します。バージョン 2 は他のレイヤーと同じ PNG・ソース・ダイジェスト検査を備えた完全なファンデーションレイヤーを要求し、schema を変えるだけでは不十分です。ファンデーションは顔料より先に描きます。閉眼パッチは現在のフレームを覆う前に SourceAtop で独自のファンデーションと目の顔料を受け取るため、パッチの alpha と現在の発話の口を両方保持します。

バージョン 1 と 2 では、全体の強さ、薄化粧の倍率 `0.55`、各スロットの強さがそれぞれ一度だけ適用されます。ゼロは未加工のネイティブソースを復元します。このランタイム機能は新しい化粧アートワークを承認せず、導入済みのバージョン 1 manifest を置き換えません。七ポーズのソースカタログと現在の視覚候補は `scratchpad/halfbody-makeup-consistency-20260913-01/` にあります。

#### 独立に制作された化粧バリアント（バージョン 3）

`mohan.reviewed-pose-motion.v3` の `cosmetics` は、まず `light`／`classic` を選び、次に `rest`／`closed`／`speech` の四つのスロットを選びます。各ルックは独自の素材を使い、バージョン 3 は旧来の薄化粧係数 `0.55` を乗じません。全体と各スロットの強さは一度だけ適用します。閉眼パッチは独自のファンデーションと目の顔料を使い、現在の発話の口を保持します。不変のソースハッシュ、パスの包含、完全状態の検査は引き続き適用されます。ソース束縛の困惑表情バージョン 3 は、その四つの口エンドポイントに対応するバリアント／状態／スロット契約を提供します。この schema への対応は新しいアートワークの承認を意味しません。

`tests/test_reviewed_garment_assets.py` はデコード、正確なソースハッシュ、パスの包含、入力の変動、レイヤー順序を網羅します。オーバーレイとネイティブ顔描画のテストは衣装の独立性、ネイティブ顔の選択、モーション順序、エラー伝播を網羅します。アニメーション基準行数を 1153 から 1152 に下げた後、外観ファサードの循環／サイズゲートは合格しました。

正式なランタイムプレビュー receipt は 24 枚の製品レンダラーフレーム、化粧の往復復元、alpha の保持、薄化粧 19,728 画素と標準化粧 20,167 画素の変化を記録しています。導入済みモーションは現在、軽く開いた発話の口エンドポイント一つと閉眼エンドポイント一つを提供します。完全な `CompanionWindow` 操作と完全な物理アニメーションは未検証で、本文書は他の候補やリリースを承認しません。
