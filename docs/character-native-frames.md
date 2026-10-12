# 原生角色完整影格契約／原生角色完整帧契约／Native Character Complete-Frame Contract／ネイティブキャラクターの完全フレーム契約

## 繁體中文

### 綁定與執行期行為

預設造型使用成對的 `asset_paths.default_look_fullbody` 與 `asset_paths.default_look_halfbody`。路徑由角色綁定宣告；本 PR 保持墨寒與林可芸的已發布素材與綁定，新外觀日後以素體包與角色圖層另案安裝。既有完整影格欄位保留相容性。既有外觀解析器比對服裝、髮型與頭飾的有效選擇與角色官方套裝；全新使用者或明確選取官方預設且解析符合時，使用角色完整影格，只疊加妝容與共用 V5 臉部動態。素體選擇 `builtin/none/none`、其他服裝包或另選髮型／頭飾使用共用 V5 素體與既有分層合成。兩個角色依同一規則切換；外觀選擇改變時清除半身影格快取。完整影格模式的 exasperated 表情由完整半身圖提供。

預設完整半身影格使用 `require_complete=True`，須涵蓋 `REQUIRED_COMPLETE_POSES` 的 24 個實際姿勢；各姿勢具 `neutral`、`small`、`a`、`o` 四家族與 `rest`、`half`、`closed` 三眼態，宣告 `whole-frame` 眨眼。素體半身維持 `assets/expressions/complete-expressions` 與 `require_complete=False`。選中的預設來源缺少目錄、manifest 或影格，會在 renderer 建構或來源切換時明確失敗。golden 維持既有素體合成設定，以 `GOLDEN_MATCH` 驗收。美術交件前的假資料限於 `.quality-tmp/mohan-look-engine/`，正式外觀另依擁有者審閱。

若 `halfbody_complete` 與舊版 `halfbody_complete_supplement` 同時存在，新完整目錄優先；只有新欄位不存在時才使用舊補充路徑。新路徑一旦宣告，缺檔便依新路徑契約報錯，不會由舊補充路徑掩蓋缺口。

### 美術檔案格式

全身完整影格必須是 1024×1536、8-bit RGBA PNG，內容為同一視角的完整人物圖，不是臉部貼片或衣物遮罩。檔名使用 rig 的 24 個標準 `view_id`：`<view_id>.png` 是 rest 影格；V5 manifest 指定眨眼影格的視角，另需 `<view_id>_blink_half.png` 與 `<view_id>_blink_closed.png`。目前 12 個有眨眼參照的視角共需 48 張 PNG：24 張 rest 加上 24 張眨眼影格。例如 `yaw+000-pitch+00.png`、`yaw+000-pitch+00_blink_half.png` 與 `yaw+000-pitch+00_blink_closed.png`。

半身 `manifest.json` 使用 schema `mohan.complete-halfbody-expressions.v1`。每個 `poses[pose_id`] 項目需包含非空 `source_lineage`、`blink_composition: "whole-frame"`、`frames[family][eye`]，以及可選的 `oral_masks[small|a|o`]。每張影格及口腔遮罩以 `{ "path": "relative/file.png", "sha256": "64 hexadecimal characters" }` 指定素材根目錄內的檔案；`expressions[name`] 使用 `{ "pose": "pose_id", "family": "neutral|small|a|o" }` 綁定姿勢和嘴型家族。每個姿勢都要提供四種嘴型家族。半身 PNG 必須是 1254×1254、8-bit RGBA，且同時含透明與可見像素。若某姿勢提供口腔遮罩，必須完整提供 `small`、`a`、`o` 三種。

通過檔案、schema、尺寸與摘要檢查只代表技術格式合格；角色身分、外觀與衣著仍依擁有者目前的審閱授權驗收，程式檢查不等於美術核准。

素體依附與角色圖層契約見 [body-pack.md](body-pack.md)。

## 简体中文

### 绑定与运行时行为

默认造型使用成对的 `asset_paths.default_look_fullbody` 与 `asset_paths.default_look_halfbody`。路径由角色绑定声明；本 PR 保持墨寒与林可芸的已发布素材与绑定，新外观日后以素体包与角色图层另案安装。现有完整帧字段保留兼容性。现有外观解析器比对服装、发型与头饰的有效选择与角色官方套装；新用户或明确选择官方默认且解析符合时，使用角色完整帧，只叠加妆容与共享 V5 面部动态。素体选择 `builtin/none/none`、其他服装包或另选发型／头饰使用共享 V5 素体与现有分层合成。两个角色按相同规则切换；外观改变时清除半身帧缓存。完整帧模式的 exasperated 表情由完整半身图提供。

默认完整半身帧使用 `require_complete=True`，须覆盖 `REQUIRED_COMPLETE_POSES` 的 24 个实际姿势；各姿势具 `neutral`、`small`、`a`、`o` 四家族与 `rest`、`half`、`closed` 三眼态，声明 `whole-frame` 眨眼。素体半身维持 `assets/expressions/complete-expressions` 与 `require_complete=False`。选中的默认来源缺少目录、manifest 或帧，会在 renderer 构建或来源切换时明确失败。golden 维持现有素体合成设置，以 `GOLDEN_MATCH` 验收。美术交付前的假数据限于 `.quality-tmp/mohan-look-engine/`，正式外观另按所有者审阅。

若 `halfbody_complete` 与旧版 `halfbody_complete_supplement` 同时存在，新完整目录优先；只有新字段不存在时才使用旧补充路径。新路径一旦声明，缺文件便按新路径契约报错，不会由旧补充路径掩盖缺口。

### 美术文件格式

全身完整帧必须是 1024×1536、8-bit RGBA PNG，内容为同一视角的完整人物图，不是面部贴片或衣物遮罩。文件名使用 rig 的 24 个标准 `view_id`：`<view_id>.png` 是 rest 帧；V5 manifest 指定眨眼帧的视角，另需 `<view_id>_blink_half.png` 和 `<view_id>_blink_closed.png`。目前 12 个有眨眼参照的视角共需 48 张 PNG：24 张 rest 加上 24 张眨眼帧。例如 `yaw+000-pitch+00.png`、`yaw+000-pitch+00_blink_half.png` 和 `yaw+000-pitch+00_blink_closed.png`。

半身 `manifest.json` 使用 schema `mohan.complete-halfbody-expressions.v1`。每个 `poses[pose_id`] 项目需包含非空 `source_lineage`、`blink_composition: "whole-frame"`、`frames[family][eye`]，以及可选的 `oral_masks[small|a|o`]。每张帧和口腔遮罩以 `{ "path": "relative/file.png", "sha256": "64 hexadecimal characters" }` 指定素材根目录内的文件；`expressions[name`] 使用 `{ "pose": "pose_id", "family": "neutral|small|a|o" }` 绑定姿势和嘴型家族。每个姿势都要提供四种嘴型家族。半身 PNG 必须是 1254×1254、8-bit RGBA，并同时含有透明与可见像素。若某姿势提供口腔遮罩，必须完整提供 `small`、`a`、`o` 三种。

通过文件、schema、尺寸和摘要检查只代表技术格式合格；角色身份、外观和衣着仍按所有者当前的审阅授权验收，程序检查不等于美术批准。

素体依附与角色图层契约见 [body-pack.md](body-pack.md)。

## English

### Bindings and runtime behavior

Default looks use paired `asset_paths.default_look_fullbody` and `asset_paths.default_look_halfbody` fields. Character bindings declare the paths. This PR preserves the published MoHan and Lin Keyun assets and bindings; new appearances will be installed separately using body packs and character layers. Existing complete-frame fields retain compatibility. The existing appearance resolver matches effective garment, hairstyle and headwear selections against the character's official ensemble. Fresh profiles and explicit official-default selections use complete frames when resolved selections match, with makeup and shared V5 facial motion applied. Bare `builtin/none/none`, other outfit packs, and changed hair or headwear use the shared V5 base and existing layered composition. Both characters follow the same switching rule; selection changes clear half-body frame caches. Complete half-body art supplies exasperated expressions in native mode.

Default half-body frames use `require_complete=True` and cover all 24 actual `REQUIRED_COMPLETE_POSES`, each with `neutral`, `small`, `a`, and `o` families, `rest`, `half`, and `closed` eyes, and `whole-frame` blinks. Bare half-body rendering keeps `assets/expressions/complete-expressions` with `require_complete=False`. Missing selected default directories, manifests or frames fail explicitly during renderer construction or source switching. Golden retains its existing base composition settings and requires `GOLDEN_MATCH`. Pre-delivery synthetic data stays inside `.quality-tmp/mohan-look-engine/`; official appearance follows owner review.

When both `halfbody_complete` and the legacy `halfbody_complete_supplement` are present, the new complete root takes priority. The legacy supplement is used only when the new field is absent. Once the new root is declared, missing data fails under that root's contract instead of being hidden by the legacy supplement.

### Artwork format

Each full-body frame must be a complete 1024×1536, 8-bit RGBA PNG for one view, not a face patch or clothing mask. Filenames use the rig's 24 canonical `view_id` values: `<view_id>.png` is the rest frame; views with a blink reference in the V5 manifest also need `<view_id>_blink_half.png` and `<view_id>_blink_closed.png`. The current 12 blink-reference views require 48 PNGs total: 24 rest frames and 24 blink frames. For example: `yaw+000-pitch+00.png`, `yaw+000-pitch+00_blink_half.png`, and `yaw+000-pitch+00_blink_closed.png`.

The half-body `manifest.json` uses schema `mohan.complete-halfbody-expressions.v1`. Every `poses[pose_id`] entry contains non-empty `source_lineage`, `blink_composition: "whole-frame"`, `frames[family][eye`], and optional `oral_masks[small|a|o`]. Each frame and oral-mask record points below the asset root using `{ "path": "relative/file.png", "sha256": "64 hexadecimal characters" }`. `expressions[name`] binds a pose and family with `{ "pose": "pose_id", "family": "neutral|small|a|o" }`. Every pose supplies all four mouth families. Half-body PNGs must be 1254×1254, 8-bit RGBA, and contain both transparent and visible pixels. If an oral mask is supplied for a pose, provide all three `small`, `a`, and `o` masks.

File, schema, dimension, and digest checks establish technical conformance only. Character identity, appearance, and clothing still require acceptance under the owner's current review authorization; passing program checks does not approve the artwork.

See [body-pack.md](body-pack.md) for body dependencies and character layers.

## 日本語

### バインディングと実行時の動作

既定外観は対の `asset_paths.default_look_fullbody` と `asset_paths.default_look_halfbody` を使います。パスはキャラクターのバインディングで宣言します。本 PR は公開済みの墨寒と林可芸の素材とバインディングを維持し、新しい外観は素体パックとキャラクターレイヤーで別途導入します。既存の完成フレームフィールドは互換性を維持します。既存の外観リゾルバーで衣装、髪型、頭飾りの有効選択と公式セットを比較し、新規ユーザーや明示的な公式既定の選択が一致した場合、完成フレームにメイクと共有 V5 の顔動作を合成します。素体の `builtin/none/none`、他の衣装パック、個別変更した髪型や頭飾りは共有 V5 素体と既存レイヤー合成を使います。両キャラクターが同じ規則で切り替え、選択変更時に半身キャッシュを消去します。完成モードの exasperated 表情は完成半身画像が提供します。

既定半身は `require_complete=True` を使い、`REQUIRED_COMPLETE_POSES` の実際の24ポーズすべてに `neutral`、`small`、`a`、`o` と `rest`、`half`、`closed`、`whole-frame` のまばたきを用意します。素体半身は `assets/expressions/complete-expressions` と `require_complete=False` を維持します。選択した既定ソースのディレクトリ、manifest、フレームが欠ける場合、renderer の構築または切替時に明確に失敗します。golden は既存の素体合成設定を維持し、`GOLDEN_MATCH` を要求します。納品前の仮データは `.quality-tmp/mohan-look-engine/` 内に置き、正式外観は所有者の審査に従います。

`halfbody_complete` と旧 `halfbody_complete_supplement` が両方ある場合は、新しい完成ディレクトリを優先します。新しいフィールドがない場合だけ旧補助パスを使います。新しいパスを指定した後に不足があれば、その契約に従ってエラーにし、旧補助パスで不足を隠しません。

### 素材形式

全身フレームは同じ視点の人物全体を描いた 1024×1536、8-bit RGBA PNG とし、顔パッチや衣服マスクにはしません。ファイル名は rig の24個の標準 `view_id` を使います。`<view_id>.png` が rest フレームです。V5 manifest にまばたき参照がある視点には `<view_id>_blink_half.png` と `<view_id>_blink_closed.png` も用意します。現在、まばたき参照がある12視点では、rest 24枚とまばたき24枚の合計48枚が必要です。例：`yaw+000-pitch+00.png`、`yaw+000-pitch+00_blink_half.png`、`yaw+000-pitch+00_blink_closed.png`。

半身 `manifest.json` の schema は `mohan.complete-halfbody-expressions.v1` です。各 `poses[pose_id`] には、空でない `source_lineage`、`blink_composition: "whole-frame"`、`frames[family][eye`]、任意の `oral_masks[small|a|o`] を記載します。フレームと口腔マスクの各レコードは `{ "path": "relative/file.png", "sha256": "64 hexadecimal characters" }` で素材ルート内のファイルを指定します。`expressions[name`] は `{ "pose": "pose_id", "family": "neutral|small|a|o" }` でポーズと口形ファミリーを結び付けます。各ポーズには四つの口形ファミリーをすべて用意します。半身 PNG は 1254×1254、8-bit RGBA とし、透明画素と不透明画素の両方を含めます。口腔マスクを使う場合は、ポーズごとに `small`、`a`、`o` の三種類すべてを用意します。

ファイル・schema・寸法・digest の検証は技術形式への適合だけを示します。キャラクターの身元、外観、衣服は、現在の所有者審査権限に基づく検収が別途必要です。プログラム検査の合格は美術承認を意味しません。

素体依存とレイヤー契約は [body-pack.md](body-pack.md) を参照してください。
