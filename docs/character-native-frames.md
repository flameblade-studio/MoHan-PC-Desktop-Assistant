# 原生角色完整影格契約／原生角色完整帧契约／Native Character Complete-Frame Contract／ネイティブキャラクターの完全フレーム契約

## 繁體中文

### 綁定與執行期行為

角色的 `rig/runtime-bindings.json` 可在 `asset_paths` 宣告三個選填路徑：`fullbody_complete_root`、`fullbody_complete_layered`、`halfbody_complete`。墨寒使用 `assets/pose-atlas/v5-base`、`assets/pose-atlas/v5-base-layered` 與 `assets/expressions/complete-expressions`。林可芸的全身完整圖位於 `assets/characters/lin-keyun/native/full`，共用臉部動態分層位於 `assets/pose-atlas/v5-base-layered`，半身完整圖位於 `assets/characters/lin-keyun/native/half`。

執行期依全身來源路徑與共用 V5 素體路徑是否相同，判斷角色是否使用原生全身影格。墨寒沿用 V5 共用素體與既有服裝合成。林可芸的原生全身完整圖負責髮型、身體與衣服；共用 V5 分層只提供臉部動態，不繪製 V5 頭髮、身體或衣服。嘴型直接取自 V5 `complete_expression_frames`，並限制在嘴唇與口腔遮罩區域內合成，保留原生全身圖其餘像素。原生模式保留妝容與臉部動態，略過服裝、頭髮、身體覆蓋層及底圖清除，也不啟用來源綁定的 exasperated 表情提供器。沒有 V5 眨眼參照的側面與背面只需要 rest 影格。

指定 `halfbody_complete` 後，renderer 建立時會讀取該目錄的 `manifest.json`；明確指定的目錄若缺少 manifest 或影格，會立即報錯。林可芸的原生半身素材必須涵蓋 `REQUIRED_COMPLETE_POSES` 定義的 24 個實際姿勢，姿勢別名不計入這 24 個姿勢。每個姿勢都必須包含 `neutral`、`small`、`a`、`o` 四種嘴型家族，各自具備 `rest`、`half`、`closed` 三種眼睛狀態，並宣告 `whole-frame` 眨眼。`require_complete=True` 會在建構 renderer 時檢查完整姿勢與眨眼集合。墨寒使用 `require_complete=False`，保留既有的眼皮貼片式眨眼契約。

若 `halfbody_complete` 與舊版 `halfbody_complete_supplement` 同時存在，新完整目錄優先；只有新欄位不存在時才使用舊補充路徑。新路徑一旦宣告，缺檔便依新路徑契約報錯，不會由舊補充路徑掩蓋缺口。

### 美術檔案格式

全身完整影格必須是 1024×1536、8-bit RGBA PNG，內容為同一視角的完整人物圖，不是臉部貼片或衣物遮罩。檔名使用 rig 的 24 個標準 `view_id`：`<view_id>.png` 是 rest 影格；V5 manifest 指定眨眼影格的視角，另需 `<view_id>_blink_half.png` 與 `<view_id>_blink_closed.png`。目前 12 個有眨眼參照的視角共需 48 張 PNG：24 張 rest 加上 24 張眨眼影格。例如 `yaw+000-pitch+00.png`、`yaw+000-pitch+00_blink_half.png` 與 `yaw+000-pitch+00_blink_closed.png`。

半身 `manifest.json` 使用 schema `mohan.complete-halfbody-expressions.v1`。每個 `poses[pose_id`] 項目需包含非空 `source_lineage`、`blink_composition: "whole-frame"`、`frames[family][eye`]，以及可選的 `oral_masks[small|a|o`]。每張影格及口腔遮罩以 `{ "path": "relative/file.png", "sha256": "64 hexadecimal characters" }` 指定素材根目錄內的檔案；`expressions[name`] 使用 `{ "pose": "pose_id", "family": "neutral|small|a|o" }` 綁定姿勢和嘴型家族。每個姿勢都要提供四種嘴型家族。半身 PNG 必須是 1254×1254、8-bit RGBA，且同時含透明與可見像素。若某姿勢提供口腔遮罩，必須完整提供 `small`、`a`、`o` 三種。

通過檔案、schema、尺寸與摘要檢查只代表技術格式合格；角色身分、外觀與衣著仍依擁有者目前的審閱授權驗收，程式檢查不等於美術核准。

## 简体中文

### 绑定与运行时行为

角色的 `rig/runtime-bindings.json` 可在 `asset_paths` 声明三个可选路径：`fullbody_complete_root`、`fullbody_complete_layered`、`halfbody_complete`。墨寒使用 `assets/pose-atlas/v5-base`、`assets/pose-atlas/v5-base-layered` 和 `assets/expressions/complete-expressions`。林可芸的全身完整图位于 `assets/characters/lin-keyun/native/full`，共享面部动态分层位于 `assets/pose-atlas/v5-base-layered`，半身完整图位于 `assets/characters/lin-keyun/native/half`。

运行时根据全身来源路径是否与共享 V5 素体路径相同，判断角色是否使用原生全身帧。墨寒沿用 V5 共享素体和既有服装合成。林可芸的原生全身完整图负责发型、身体和衣服；共享 V5 分层只提供面部动态，不绘制 V5 头发、身体或衣服。嘴型直接取自 V5 `complete_expression_frames`，并限制在嘴唇与口腔遮罩区域内合成，保留原生全身图其余像素。原生模式保留妆容与面部动态，跳过服装、头发、身体覆盖层和底图清除，也不启用来源绑定的 exasperated 表情提供器。没有 V5 眨眼参照的侧面和背面只需要 rest 帧。

指定 `halfbody_complete` 后，renderer 创建时会读取该目录的 `manifest.json`；明确指定的目录若缺少 manifest 或帧，会立即报错。林可芸的原生半身素材必须覆盖 `REQUIRED_COMPLETE_POSES` 定义的 24 个实际姿势，姿势别名不计入这 24 个姿势。每个姿势都必须包含 `neutral`、`small`、`a`、`o` 四种嘴型家族，各自具备 `rest`、`half`、`closed` 三种眼睛状态，并声明 `whole-frame` 眨眼。`require_complete=True` 会在构建 renderer 时检查完整姿势和眨眼集合。墨寒使用 `require_complete=False`，保留既有的眼皮贴片式眨眼契约。

若 `halfbody_complete` 与旧版 `halfbody_complete_supplement` 同时存在，新完整目录优先；只有新字段不存在时才使用旧补充路径。新路径一旦声明，缺文件便按新路径契约报错，不会由旧补充路径掩盖缺口。

### 美术文件格式

全身完整帧必须是 1024×1536、8-bit RGBA PNG，内容为同一视角的完整人物图，不是面部贴片或衣物遮罩。文件名使用 rig 的 24 个标准 `view_id`：`<view_id>.png` 是 rest 帧；V5 manifest 指定眨眼帧的视角，另需 `<view_id>_blink_half.png` 和 `<view_id>_blink_closed.png`。目前 12 个有眨眼参照的视角共需 48 张 PNG：24 张 rest 加上 24 张眨眼帧。例如 `yaw+000-pitch+00.png`、`yaw+000-pitch+00_blink_half.png` 和 `yaw+000-pitch+00_blink_closed.png`。

半身 `manifest.json` 使用 schema `mohan.complete-halfbody-expressions.v1`。每个 `poses[pose_id`] 项目需包含非空 `source_lineage`、`blink_composition: "whole-frame"`、`frames[family][eye`]，以及可选的 `oral_masks[small|a|o`]。每张帧和口腔遮罩以 `{ "path": "relative/file.png", "sha256": "64 hexadecimal characters" }` 指定素材根目录内的文件；`expressions[name`] 使用 `{ "pose": "pose_id", "family": "neutral|small|a|o" }` 绑定姿势和嘴型家族。每个姿势都要提供四种嘴型家族。半身 PNG 必须是 1254×1254、8-bit RGBA，并同时含有透明与可见像素。若某姿势提供口腔遮罩，必须完整提供 `small`、`a`、`o` 三种。

通过文件、schema、尺寸和摘要检查只代表技术格式合格；角色身份、外观和衣着仍按所有者当前的审阅授权验收，程序检查不等于美术批准。

## English

### Bindings and runtime behavior

A character's `rig/runtime-bindings.json` may declare three optional `asset_paths`: `fullbody_complete_root`, `fullbody_complete_layered`, and `halfbody_complete`. MoHan uses `assets/pose-atlas/v5-base`, `assets/pose-atlas/v5-base-layered`, and `assets/expressions/complete-expressions`. Lin Keyun's complete full-body frames live in `assets/characters/lin-keyun/native/full`, shared facial-motion layers use `assets/pose-atlas/v5-base-layered`, and complete half-body frames live in `assets/characters/lin-keyun/native/half`.

Runtime identifies native full-body frames by comparing their source path with the shared V5 body path. MoHan keeps the shared V5 body and its existing outfit composition. Lin Keyun's native full-body images own the hair, body, and clothing; shared V5 layers provide facial motion only and do not draw V5 hair, body, or clothes. Mouth shapes come directly from V5 `complete_expression_frames` and are composited only inside the lip and oral-mask regions, preserving the rest of the native frame. Native mode keeps makeup and facial motion while skipping clothing, hair, body overlays, and base clearing. It also disables the source-bound exasperated expression provider. Side and rear views without a V5 blink reference need only a rest frame.

When `halfbody_complete` is explicitly bound, the renderer loads that directory's `manifest.json` during construction; a declared directory with a missing manifest or frame fails immediately. Lin Keyun's native half-body package must cover the 24 actual poses in `REQUIRED_COMPLETE_POSES`; aliases do not count as additional poses. Each pose has all four mouth families, `neutral`, `small`, `a`, and `o`, with `rest`, `half`, and `closed` eye frames for each family, plus `whole-frame` blinks. `require_complete=True` checks the full pose and blink sets when the renderer is constructed. MoHan uses `require_complete=False` and retains its existing eye-patch blink contract.

When both `halfbody_complete` and the legacy `halfbody_complete_supplement` are present, the new complete root takes priority. The legacy supplement is used only when the new field is absent. Once the new root is declared, missing data fails under that root's contract instead of being hidden by the legacy supplement.

### Artwork format

Each full-body frame must be a complete 1024×1536, 8-bit RGBA PNG for one view, not a face patch or clothing mask. Filenames use the rig's 24 canonical `view_id` values: `<view_id>.png` is the rest frame; views with a blink reference in the V5 manifest also need `<view_id>_blink_half.png` and `<view_id>_blink_closed.png`. The current 12 blink-reference views require 48 PNGs total: 24 rest frames and 24 blink frames. For example: `yaw+000-pitch+00.png`, `yaw+000-pitch+00_blink_half.png`, and `yaw+000-pitch+00_blink_closed.png`.

The half-body `manifest.json` uses schema `mohan.complete-halfbody-expressions.v1`. Every `poses[pose_id`] entry contains non-empty `source_lineage`, `blink_composition: "whole-frame"`, `frames[family][eye`], and optional `oral_masks[small|a|o`]. Each frame and oral-mask record points below the asset root using `{ "path": "relative/file.png", "sha256": "64 hexadecimal characters" }`. `expressions[name`] binds a pose and family with `{ "pose": "pose_id", "family": "neutral|small|a|o" }`. Every pose supplies all four mouth families. Half-body PNGs must be 1254×1254, 8-bit RGBA, and contain both transparent and visible pixels. If an oral mask is supplied for a pose, provide all three `small`, `a`, and `o` masks.

File, schema, dimension, and digest checks establish technical conformance only. Character identity, appearance, and clothing still require acceptance under the owner's current review authorization; passing program checks does not approve the artwork.

## 日本語

### バインディングと実行時の動作

キャラクターの `rig/runtime-bindings.json` では、`asset_paths` に三つの任意パス `fullbody_complete_root`、`fullbody_complete_layered`、`halfbody_complete` を指定できます。墨寒は `assets/pose-atlas/v5-base`、`assets/pose-atlas/v5-base-layered`、`assets/expressions/complete-expressions` を使用します。林可芸の全身完成フレームは `assets/characters/lin-keyun/native/full`、共有の顔動作用レイヤーは `assets/pose-atlas/v5-base-layered`、半身完成フレームは `assets/characters/lin-keyun/native/half` を使用します。

実行時は全身ソースのパスと共通 V5 素体のパスを比較し、ネイティブ全身フレームを使うか判定します。墨寒は共通 V5 素体と既存の衣装合成を維持します。林可芸のネイティブ全身画像が髪型・身体・衣服を担い、共通 V5 レイヤーは顔の動きだけを提供します。V5 の髪・身体・衣服は描画しません。口形は V5 の `complete_expression_frames` から取得し、唇と口腔マスクの範囲内だけに合成して、ネイティブ全身画像の他の画素を保ちます。ネイティブモードではメイクと顔の動きを維持し、衣服・髪・身体のオーバーレイとベース消去を省略します。また、source-bound の exasperated 表情プロバイダーを無効にします。V5 にまばたき参照がない横向き・後ろ向きの視点には rest フレームだけが必要です。

`halfbody_complete` を明示すると、renderer の構築時にそのディレクトリの `manifest.json` を読み込みます。明示したディレクトリに manifest やフレームがない場合は直ちにエラーになります。林可芸のネイティブ半身素材には `REQUIRED_COMPLETE_POSES` が定義する実際の24ポーズをすべて含めます。別名は追加ポーズとして数えません。各ポーズには四つの口形ファミリー `neutral`、`small`、`a`、`o` を用意し、それぞれに `rest`、`half`、`closed` の目のフレームと `whole-frame` のまばたきを用意します。`require_complete=True` は renderer の構築時にポーズとまばたきの全件を検証します。墨寒は `require_complete=False` を使い、既存の目パッチ方式のまばたきを維持します。

`halfbody_complete` と旧 `halfbody_complete_supplement` が両方ある場合は、新しい完成ディレクトリを優先します。新しいフィールドがない場合だけ旧補助パスを使います。新しいパスを指定した後に不足があれば、その契約に従ってエラーにし、旧補助パスで不足を隠しません。

### 素材形式

全身フレームは同じ視点の人物全体を描いた 1024×1536、8-bit RGBA PNG とし、顔パッチや衣服マスクにはしません。ファイル名は rig の24個の標準 `view_id` を使います。`<view_id>.png` が rest フレームです。V5 manifest にまばたき参照がある視点には `<view_id>_blink_half.png` と `<view_id>_blink_closed.png` も用意します。現在、まばたき参照がある12視点では、rest 24枚とまばたき24枚の合計48枚が必要です。例：`yaw+000-pitch+00.png`、`yaw+000-pitch+00_blink_half.png`、`yaw+000-pitch+00_blink_closed.png`。

半身 `manifest.json` の schema は `mohan.complete-halfbody-expressions.v1` です。各 `poses[pose_id`] には、空でない `source_lineage`、`blink_composition: "whole-frame"`、`frames[family][eye`]、任意の `oral_masks[small|a|o`] を記載します。フレームと口腔マスクの各レコードは `{ "path": "relative/file.png", "sha256": "64 hexadecimal characters" }` で素材ルート内のファイルを指定します。`expressions[name`] は `{ "pose": "pose_id", "family": "neutral|small|a|o" }` でポーズと口形ファミリーを結び付けます。各ポーズには四つの口形ファミリーをすべて用意します。半身 PNG は 1254×1254、8-bit RGBA とし、透明画素と不透明画素の両方を含めます。口腔マスクを使う場合は、ポーズごとに `small`、`a`、`o` の三種類すべてを用意します。

ファイル・schema・寸法・digest の検証は技術形式への適合だけを示します。キャラクターの身元、外観、衣服は、現在の所有者審査権限に基づく検収が別途必要です。プログラム検査の合格は美術承認を意味しません。
