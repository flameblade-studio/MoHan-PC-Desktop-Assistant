# 可拆卸粉底、衣裝妝容遮擋與動態前髮深度契約／可拆卸粉底、衣装妆容遮挡与动态前发深度契约／Detachable foundation, garment makeup occlusion, and animated front-hair depth contract／着脱式ファンデーション、衣装メイク遮蔽、動的前髪の奥行き契約

## 繁體中文

### 文件與素材所有權

- `tools/build_makeup_safe_regions.py` 的生成範圍限定為 legacy v1 安全區；v2 是人工編寫的素材。`--check` 會原地驗證 v2 文件與所有參照遮罩，成功時回報 `VALIDATED_AUTHORED_V2`；人工編寫的 v2 由一般生成流程完整保護。
- `mohan.makeup-safe-regions.v2` 為每個剪影綁定 `foundation_masks` 與 `eye_aperture_masks`。匯入與執行期的允收條件要求欄位及狀態齊全、狀態表一致，且全畫布 RGBA PNG 的尺寸與錨點相符。

### 妝容狀態與安全區

- 妝容可分別選用 `eyes`、`cheeks`、`lips` 與 `foundation`；`foundation_silhouettes` 明確啟用第四槽。需要粉底的剪影必須同時提供 `rest`、`half`、`closed` 狀態，半閉眼與閉眼會一起替換粉底和眼妝。
- 執行期依目前狀態的安全區裁切妝容，保護可見虹膜與口腔；`SourceAtop` 保留原生角色 Alpha，包括半透明臉部像素。變體濃度與使用者設定的濃度相乘，零濃度必須回到素體畫面。

### 動態分段深度順序

- `AppearanceLayerStack` 將後髮放在 `behind_body`，其餘外觀放在 `foreground`；`paint_behind_body` 以 `DestinationOver` 先畫後髮。`front_hair_indices` 只標記前髮，`split_front_hair` 只把前髮延後，garment、headwear 與其他配件仍維持既有順序。
- `apply_animated` 依序準備畫布、合成後髮與核心身體／手部覆層、先畫 garment／headwear／配件，再執行 `paint_motion`，用 `SourceAtop` 套用妝容，最後以 `SourceOver` 將前髮各畫一次。既有 `apply` 仍維持完整合成順序，並以 `makeup_prefix_count` 保留妝容的 SourceAtop 邊界。

### 失敗回退與驗證

- 外觀階段或妝容階段遇到 `OSError`、`ValueError`、`OutfitPackError` 或壞掉的 ZIP 時，`_AppearanceCompositionError` 會讓 `apply_animated` 放棄部分畫面、呼叫 `_invalidate_view` 清除該視角快取，再在原始 `frame` 上重播 `paint_motion`。核心動作 callback 自身的程式錯誤仍會向外傳遞。
- `tests/test_animated_makeup_depth.py` 驗證後髮、身體、妝容與前髮的像素順序，以及妝容失敗時的動作重播；`test_active_outfit_overlay_makeup.py`、`test_rear_hair_composition.py`、`test_installed_outfit_blink_roundtrip.py` 與 `test_installed_outfit_cache.py` 負責相鄰回歸。像素與契約測試提供技術證據；外觀核可仍是獨立的必要閘門。

### 設定與驗收界線

- `makeup.json` 保存整張已驗證的強度表；切換四槽與三槽剪影或 `light` 變體時保留各槽值，legacy 剪影可略過 `foundation` 顯示，同時完整保留其設定值。未知鍵或無效值沿用上一個有效設定並通知呼叫端。
- 技術驗證應逐一比較 `rest`、`half`、`closed` 與素體、確認 Alpha、零濃度、單槽控制及回到初始狀態的可重現性。技術證據與擁有者的美術外觀核可分開記錄；長髮圖像仍須等待擁有者確認。

### 衣裝妝容遮擋 v2

- `occludes_makeup` 是衣裝資產的可選布林欄位，適用範圍限定為 `GARMENT_SLOTS`；省略時等同 `false`。更新後的讀取器接受 `GARMENT_SLOTS` 上的布林值與已知欄位。這項宣告須由支援它的讀取器載入，讓深度契約始終完整保留。
- 靜態 `apply` 以 `makeup_prefix_count` 維持妝容的 `SourceAtop` 前綴，前景圖層仍按宣告的 `z-order` 合成，所以既有靜態順序不變。動畫 `apply_animated` 透過 `split_makeup_depth` 把 `front_hair_indices` 與 `makeup_occluder_indices` 延後到動作與妝容之後，並保留每個階段內的順序。
- `occludes_makeup` 為 `true` 的前景衣裝資產只在動畫流程成為妝容遮擋層；省略或為 `false` 時留在 `legacy` 的前段。後髮仍在 `behind_body`，並維持後髮角色。
- 遮擋依 `RGBA` 非零 `Alpha` 判定：`Alpha` 為 `0` 才是透明，任何部分透明 `Alpha` 也參與遮擋，門檻涵蓋不透明與部分透明像素。幾何、`Alpha` 通道、雜湊、畫布／錨點限制、核心身分區與安全妝容遮罩仍採 `fail-closed`。這個欄位的作用範圍限定為 paint depth；protected identity 與手部安全界線維持完整；衣裝仍須通過既有 Alpha、遮罩與幾何驗證。
- 擴充由 `tests/test_garment_makeup_occlusion.py` 和相鄰深度測試覆蓋。解析器、像素與回歸測試通過代表技術證據；素材外觀、外觀包品質與擁有者的美術驗收仍各自獨立記錄。

## 简体中文

### 文档与素材所有权

- `tools/build_makeup_safe_regions.py` 的生成范围限定为 legacy v1 安全区；v2 是人工编写的素材。`--check` 会原地验证 v2 文档与所有引用遮罩，成功时报告 `VALIDATED_AUTHORED_V2`；人工编写的 v2 由普通生成流程完整保护。
- `mohan.makeup-safe-regions.v2` 为每个剪影绑定 `foundation_masks` 与 `eye_aperture_masks`。导入与运行时的接收条件要求字段及状态齐全、状态表一致，且全画布 RGBA PNG 的尺寸与锚点相符。

### 妆容状态与安全区

- 妆容可分别选用 `eyes`、`cheeks`、`lips` 与 `foundation`；`foundation_silhouettes` 明确启用第四槽。需要粉底的剪影必须同时提供 `rest`、`half`、`closed` 状态，半闭眼与闭眼会一起替换粉底和眼妆。
- 运行时依当前状态的安全区裁剪妆容，保护可见虹膜与口腔；`SourceAtop` 保留原生角色 Alpha，包括半透明面部像素。变体浓度与用户设置的浓度相乘，零浓度必须回到素体画面。

### 动态分段深度顺序

- `AppearanceLayerStack` 将后发放在 `behind_body`，其余外观放在 `foreground`；`paint_behind_body` 以 `DestinationOver` 先画后发。`front_hair_indices` 只标记前发，`split_front_hair` 只把前发延后，garment、headwear 与其他配件仍保持既有顺序。
- `apply_animated` 依次准备画布、合成后发与核心身体／手部覆盖层、先画 garment／headwear／配件，再执行 `paint_motion`，用 `SourceAtop` 套用妆容，最后以 `SourceOver` 将前发各画一次。既有 `apply` 仍保持完整合成顺序，并以 `makeup_prefix_count` 保留妆容的 SourceAtop 边界。

### 失败回退与验证

- 外观阶段或妆容阶段遇到 `OSError`、`ValueError`、`OutfitPackError` 或损坏的 ZIP 时，`_AppearanceCompositionError` 会让 `apply_animated` 放弃部分画面、调用 `_invalidate_view` 清除该视角缓存，再在原始 `frame` 上重播 `paint_motion`。核心动作 callback 自身的程序错误仍会向外传递。
- `tests/test_animated_makeup_depth.py` 验证后发、身体、妆容与前发的像素顺序，以及妆容失败时的动作重播；`test_active_outfit_overlay_makeup.py`、`test_rear_hair_composition.py`、`test_installed_outfit_blink_roundtrip.py` 与 `test_installed_outfit_cache.py` 负责相邻回归。像素与契约测试提供技术证据；外观批准仍是独立的必要关卡。

### 设置与验收界线

- `makeup.json` 保存整张已验证的强度表；切换四槽与三槽剪影或 `light` 变体时保留各槽值，legacy 剪影可略过 `foundation` 显示，同时完整保留其设置值。未知键或无效值沿用上一有效设置并通知调用端。
- 技术验证应逐一比较 `rest`、`half`、`closed` 与素体、确认 Alpha、零浓度、单槽控制及回到初始状态的可重现性。技术证据与拥有者的美术外观核可分开记录；长发图像仍须等待拥有者确认。

### 衣装妆容遮挡 v2

- `occludes_makeup` 是衣装资源的可选布尔字段，适用范围限定为 `GARMENT_SLOTS`；省略时等同 `false`。更新后的读取器接受 `GARMENT_SLOTS` 上的布尔值与已知字段。该声明须由支持它的读取器加载，使深度契约始终完整保留。
- 静态 `apply` 以 `makeup_prefix_count` 维持妆容的 `SourceAtop` 前缀，前景图层仍按声明的 `z-order` 合成，所以既有静态顺序不变。动画 `apply_animated` 通过 `split_makeup_depth` 把 `front_hair_indices` 与 `makeup_occluder_indices` 延后到动作与妆容之后，并保留每个阶段内的顺序。
- `occludes_makeup` 为 `true` 的前景衣装资源只在动画流程成为妆容遮挡层；省略或为 `false` 时留在 `legacy` 的前段。后发仍在 `behind_body`，并维持后发角色。
- 遮挡依 `RGBA` 非零 `Alpha` 判定：`Alpha` 为 `0` 才是透明，任何部分透明 `Alpha` 也参与遮挡，门槛涵盖不透明与部分透明像素。几何、`Alpha` 通道、哈希、画布／锚点限制、核心身份区与安全妆容遮罩仍采用 `fail-closed`。该字段的作用范围限定为 paint depth；protected identity 与手部安全边界维持完整；衣装仍须通过既有 Alpha、遮罩与几何验证。
- 扩展由 `tests/test_garment_makeup_occlusion.py` 和相邻深度测试覆盖。解析器、像素与回归测试通过代表技术证据；素材外观、外观包质量与拥有者的美术验收仍各自独立记录。

## English

### Document and asset ownership

- The generation scope of `tools/build_makeup_safe_regions.py` is limited to legacy v1 safe regions; v2 is authored input. `--check` validates the v2 document and every referenced mask in place and reports `VALIDATED_AUTHORED_V2` on success. Ordinary generation fully protects the authored v2 input.
- `mohan.makeup-safe-regions.v2` binds `foundation_masks` and `eye_aperture_masks` for each silhouette. Import and runtime acceptance requires complete fields and states, consistent state maps, and full-canvas RGBA PNGs with matching dimensions and anchors.

### Makeup states and safe regions

- Makeup exposes independent `eyes`, `cheeks`, `lips`, and `foundation` slots; `foundation_silhouettes` opts a silhouette into the fourth slot. A foundation silhouette must provide `rest`, `half`, and `closed` states, with half-closed and closed eyes replacing foundation and eye makeup together.
- Runtime clips makeup to the safe region for the current state while protecting the visible iris and oral cavity; `SourceAtop` preserves native character Alpha, including translucent facial pixels. Variant intensity multiplies user intensity, and zero intensity must reproduce the bare frame.

### Animated split-phase depth order

- `AppearanceLayerStack` stores rear hair in `behind_body` and other appearance in `foreground`; `paint_behind_body` draws rear hair first with `DestinationOver`. `front_hair_indices` marks only front hair, and `split_front_hair` delays only those layers, leaving garment, headwear, and other accessories in their established order.
- `apply_animated` prepares the canvas, composites rear hair and core body or hand overlays, draws garment, headwear, and accessories first, runs `paint_motion`, applies makeup with `SourceAtop`, and draws each front-hair layer once with `SourceOver`. The existing `apply` path keeps its complete composition order and uses `makeup_prefix_count` for the makeup SourceAtop boundary.

### Failure rollback and verification

- If an appearance or makeup phase raises `OSError`, `ValueError`, `OutfitPackError`, or a bad ZIP error, `_AppearanceCompositionError` makes `apply_animated` discard the partial frame, call `_invalidate_view` to clear that view's caches, and replay `paint_motion` on the untouched `frame`. Programming errors from the core-motion callback still propagate.
- `tests/test_animated_makeup_depth.py` verifies rear-hair, body, makeup, and front-hair pixel order plus motion replay after makeup failure; `test_active_outfit_overlay_makeup.py`, `test_rear_hair_composition.py`, `test_installed_outfit_blink_roundtrip.py`, and `test_installed_outfit_cache.py` provide adjacent regression coverage. Pixel and contract tests provide technical evidence; visual approval remains a separate required gate.

### Settings and acceptance boundary

- `makeup.json` stores the complete validated intensity map; switching between four-slot and three-slot silhouettes or the `light` variant retains every slot value, while a legacy silhouette may omit `foundation` from display while preserving its stored value. Unknown keys or invalid values preserve the last valid settings and notify the caller.
- Technical verification compares `rest`, `half`, and `closed` with the bare counterpart, checks Alpha, zero intensity, individual slot controls, and reproducibility after returning to the initial state. Technical evidence and the owner's visual approval are recorded separately; the long-hair artwork still awaits the owner's decision.

### Garment makeup occlusion v2

- `occludes_makeup` is an optional boolean field for garment assets, with scope limited to `GARMENT_SLOTS`; omission means `false`. The updated reader accepts boolean values on `GARMENT_SLOTS` and known fields. This declaration requires a reader that supports it, preserving the depth contract in full.
- Static `apply` keeps makeup as the `makeup_prefix_count` `SourceAtop` prefix, and foreground layers still compose in declared `z-order`, so the established static order remains. Animated `apply_animated` uses `split_makeup_depth` to delay `front_hair_indices` and `makeup_occluder_indices` until after motion and makeup while preserving order inside each phase.
- A foreground garment asset with `occludes_makeup` set to `true` becomes a makeup occluder only in the animated path; omission or `false` keeps it in the `legacy` early phase. Rear hair remains in `behind_body` and retains its rear-hair role.
- Occlusion uses nonzero `RGBA` `Alpha`: only `Alpha` `0` is transparent, and partial `Alpha` also participates, with a threshold that includes both opaque and partially transparent pixels. Geometry, the `Alpha` channel, hashes, canvas and anchor limits, core identity regions, and safe makeup masks remain `fail-closed`. The field's scope is paint depth; protected identity and hand-safety boundaries remain fully enforced, and garments still pass the existing Alpha, mask, and geometry checks.
- The extension is covered by `tests/test_garment_makeup_occlusion.py` and adjacent depth tests. Passing parser, pixel, and regression tests provides technical evidence; artwork appearance, outfit-pack quality, and the owner's visual acceptance remain separately recorded gates.

## 日本語

### 文書と素材の所有権

- `tools/build_makeup_safe_regions.py` の生成範囲は legacy v1 の安全領域に限定し、v2 は作成者が記述した入力です。`--check` は v2 文書と参照されるすべてのマスクをその場で検証し、成功時に `VALIDATED_AUTHORED_V2` を報告します。通常の生成処理から作成済み v2 入力を完全に保護します。
- `mohan.makeup-safe-regions.v2` は各シルエットの `foundation_masks` と `eye_aperture_masks` を束縛します。インポート時と実行時の受入条件は、フィールドと状態が揃い、状態マップが一貫し、全キャンバス RGBA PNG の寸法とアンカーが一致することです。

### メイク状態と安全領域

- メイクは `eyes`、`cheeks`、`lips`、`foundation` を独立したスロットとして公開し、`foundation_silhouettes` で第4スロットを有効にします。ファンデーションを使うシルエットには `rest`、`half`、`closed` が必要で、半閉眼と閉眼ではファンデーションとアイメイクを同時に置き換えます。
- 実行時は現在の状態の安全領域でメイクをクリップし、見えている虹彩と口腔を保護します。`SourceAtop` は半透明の顔画素を含む元のキャラクター Alpha を保持します。バリアント濃度とユーザー設定の濃度を乗算し、濃度 0 では素体フレームを再現します。

### 動的な段階別奥行き順序

- `AppearanceLayerStack` は後ろ髪を `behind_body` に、その他の外観を `foreground` に保持し、`paint_behind_body` は `DestinationOver` で後ろ髪を先に描きます。`front_hair_indices` は前髪だけを示し、`split_front_hair` は前髪だけを遅延させ、衣装、頭飾り、その他のアクセサリーの既存順序を保ちます。
- `apply_animated` はキャンバスを準備し、後ろ髪とコアの身体・手のオーバーレイを合成し、衣装・頭飾り・アクセサリーを先に描き、`paint_motion` を実行してから `SourceAtop` でメイクを適用し、最後に各前髪レイヤーを `SourceOver` で1回だけ描きます。既存の `apply` は全体の合成順序を維持し、メイクの SourceAtop 境界には `makeup_prefix_count` を使います。

### 失敗時のロールバックと検証

- 外観またはメイクの段階で `OSError`、`ValueError`、`OutfitPackError`、または壊れた ZIP エラーが発生すると、`_AppearanceCompositionError` により `apply_animated` は途中のフレームを破棄し、`_invalidate_view` でその視点のキャッシュを消去したうえで、変更されていない `frame` に `paint_motion` を再生します。コア動作 callback 自体のプログラムエラーは伝播します。
- `tests/test_animated_makeup_depth.py` は後ろ髪、身体、メイク、前髪の画素順序と、メイク失敗後の動作再生を検証します。`test_active_outfit_overlay_makeup.py`、`test_rear_hair_composition.py`、`test_installed_outfit_blink_roundtrip.py`、`test_installed_outfit_cache.py` は隣接回帰を担います。画素テストと契約テストは技術証拠を提供し、外観承認は別の必須関門として残ります。

### 設定と受入れ境界

- `makeup.json` は検証済み強度マップ全体を保存します。4スロットと3スロットのシルエット、または `light` バリアントを切り替えても各スロット値を保持し、legacy シルエットは表示時に `foundation` を省略でき、保存値を完全に維持します。未知のキーや無効値では直前の有効設定を保ち、呼び出し元へ通知します。
- 技術検証では `rest`、`half`、`closed` と素体を比較し、Alpha、濃度 0、個別スロット操作、初期状態へ戻した再現性を確認します。技術証拠と所有者の外観承認は分けて記録し、長髪アートは所有者の判断を待ちます。

### 衣装メイク遮蔽 v2

- `occludes_makeup` は衣装アセットの任意ブール欄で、適用範囲を `GARMENT_SLOTS` に限定します。省略時は `false` と同じです。更新済みリーダーは `GARMENT_SLOTS` 上のブール値と既知欄を受け入れます。この宣言は対応リーダーで読み込み、奥行き契約を完全に保持します。
- 静的な `apply` は `makeup_prefix_count` によるメイクの `SourceAtop` プレフィックスを保ち、前景レイヤーを宣言された `z-order` で合成するため、既存の静的な順序は変わりません。動的な `apply_animated` は `split_makeup_depth` で `front_hair_indices` と `makeup_occluder_indices` を動きとメイクの後へ遅らせ、各段階内の順序を保ちます。
- `occludes_makeup` が `true` の前景衣装アセットは、動的な合成でだけメイク遮蔽レイヤーになります。省略または `false` の場合は `legacy` の前段に残ります。後ろ髪は `behind_body` にあり、後ろ髪の役割を維持します。
- 遮蔽は `RGBA` の非ゼロ `Alpha` で判定します。`Alpha` が `0` の場合だけ透明で、部分的な `Alpha` も遮蔽に参加し、閾値は不透明と部分透明の両方のピクセルを対象とします。ジオメトリ、`Alpha` チャンネル、ハッシュ、キャンバス／アンカー制限、コア身元領域、安全なメイクマスクは引き続き `fail-closed` です。この欄の作用範囲は paint depth に限定し、protected identity と手部安全境界を完全に維持します。衣装は従来の Alpha、マスク、ジオメトリ検査にも通過する必要があります。
- 拡張は `tests/test_garment_makeup_occlusion.py` と隣接する奥行きテストでカバーします。パーサー、ピクセル、回帰テストの成功は技術的証拠を示します。素材の外観、外観パック品質、所有者の美術受入れは、それぞれ別の関門として記録します。

