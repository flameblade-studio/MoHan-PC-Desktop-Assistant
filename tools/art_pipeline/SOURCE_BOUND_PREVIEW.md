# 來源固定執行期預覽／来源固定运行时预览／Source-bound runtime previews／ソース固定ランタイムプレビュー

## 繁體中文

`source_bound_manifest` 固定現有輸入，`source_bound_preview` 將候選建立在新的 `scratchpad` 目錄，再由產品使用的 `ActiveOutfitOverlay` 與 `LayeredFullBodyRenderer` 產生四種眼睛狀態。原生圖、身體與雙手維持 canonical 路徑及固定 bytes；來源漂移、身分違規或越界替換會明確失敗。全部驗證完成後才寫 `receipt.json`，產物仍須等待擁有者目視核可。

衣料、髮型與髮飾使用 `pack_updates`；每包指定 `target` 與 `members`，每個成員固定候選來源 `source`、包內既有成員路徑 `target`、候選 `sha256` 及事先製作的 `allowed_change_mask`。遮罩必須為同尺寸、非空且只含 `0` 與 `255`，路徑使用 `/`。`reference_preview` 固定基準的 `receipt_sha256` 與 `input_manifest_sha256`，`reference_frames` 固定四種同狀態影格。未選用、跨視角共用或遮罩外變更都會被拒絕。

可選的 `makeup_updates` 是平面的成員清單，只能更新 `mohan.makeup.builtin` 目前選定變體及視角中已存在的 `cheeks`、`eyes`、`lips`，包含同視角既有的半閉眼與閉眼成員。完整封包須以 canonical 路徑及 SHA 固定在 `files`。候選 alpha 必須與原成員完全相同，RGB 只能在原成員可見 alpha 與 `allowed_change_mask` 的交集內改變。`foundation`、新宣告、未選用或共用成員、原生圖路徑及未固定於 `scratchpad` 的候選都會失敗。

可選的 `makeup_slot_intensities` 沿用產品的 `eyes`、`cheeks`、`lips`、`foundation` 設定，各值須為 `0` 到 `1` 的有限數字，省略時為 1。基準與候選的正規化設定必須一致。妝容候選還須取得 `same-state-face-core-identical-outside-authored-makeup` 狀態：每幀臉部 alpha 與保護區零差異，且核准妝容區確有變更。這些設定不改寫素材或個人設定。

擁有者核可且受影響測試通過後，`integrate_source_bound_pack` 可接入一個選定套裝。呼叫端須提供候選 receipt SHA、擁有者原文核可、SHA 固定且 exit code 為 `0` 的回歸報告，以及寫入後 runtime 檢查。它先備份再原子替換，安全復原本次寫入並保留並行內容，最後寫成功 receipt；`release` 為 `false`。

同一候選若同時包含一個選定套裝與 canonical built-in 妝容，可由 `integrate_source_bound_packs` 視為一筆本機交易。全部來源、fresh rebuild、完整 stage、核可、回歸報告與兩個正式基準會在寫入前驗證；兩包先完成備份，再依序原子替換，且只有兩包皆更新後才呼叫一次 `postcheck`。任何失敗都會逐包嘗試安全復原並分類回報一般復原錯誤與並行修改。成功 receipt 最後寫入，`release` 為 `false`；`integrate_source_bound_pack` 仍拒絕妝容更新。兩個入口都不寫入原生圖，也不發布。

## 简体中文

`source_bound_manifest` 固定现有输入，`source_bound_preview` 将候选建立在新的 `scratchpad` 目录，再由产品使用的 `ActiveOutfitOverlay` 与 `LayeredFullBodyRenderer` 生成四种眼睛状态。原生图、身体与双手维持 canonical 路径及固定 bytes；来源漂移、身份违规或越界替换会明确失败。全部验证完成后才写 `receipt.json`，产物仍须等待拥有者目视批准。

衣料、发型与发饰使用 `pack_updates`；每包指定 `target` 与 `members`，每个成员固定候选来源 `source`、包内既有成员路径 `target`、候选 `sha256` 及预先制作的 `allowed_change_mask`。遮罩必须为同尺寸、非空且只含 `0` 与 `255`，路径使用 `/`。`reference_preview` 固定基准的 `receipt_sha256` 与 `input_manifest_sha256`，`reference_frames` 固定四种同状态帧。未选用、跨视角共用或遮罩外变更都会被拒绝。

可选的 `makeup_updates` 是扁平成员列表，只能更新 `mohan.makeup.builtin` 当前选中变体及视角中已存在的 `cheeks`、`eyes`、`lips`，包括同视角既有的半闭眼与闭眼成员。完整封包须以 canonical 路径及 SHA 固定在 `files`。候选 alpha 必须与原成员完全相同，RGB 只能在原成员可见 alpha 与 `allowed_change_mask` 的交集内改变。`foundation`、新声明、未选用或共用成员、原生图路径及未固定于 `scratchpad` 的候选都会失败。

可选的 `makeup_slot_intensities` 沿用产品的 `eyes`、`cheeks`、`lips`、`foundation` 设置，各值须为 `0` 到 `1` 的有限数字，省略时为 1。基准与候选的规范化设置必须一致。妆容候选还须取得 `same-state-face-core-identical-outside-authored-makeup` 状态：每帧脸部 alpha 与保护区零差异，且批准妆容区确有变更。这些设置不改写素材或个人设置。

拥有者批准且受影响测试通过后，`integrate_source_bound_pack` 可接入一个选定套装。调用端须提供候选 receipt SHA、拥有者原文批准、以 SHA 固定且 exit code 为 `0` 的回归报告，以及写入后 runtime 检查。它先备份再原子替换，安全恢复本次写入并保留并发内容，最后写成功 receipt；`release` 为 `false`。

同一候选若同时包含一个选定套装与 canonical built-in 妆容，可由 `integrate_source_bound_packs` 视为一笔本机事务。全部来源、fresh rebuild、完整 stage、批准、回归报告与两个正式基准会在写入前验证；两包先完成备份，再依次原子替换，且只有两包都更新后才调用一次 `postcheck`。任何失败都会逐包尝试安全恢复并分类报告一般恢复错误与并发修改。成功 receipt 最后写入，`release` 为 `false`；`integrate_source_bound_pack` 仍拒绝妆容更新。两个入口都不写入原生图，也不发布。

## English

`source_bound_manifest` pins the current inputs, and `source_bound_preview` builds a candidate in a new `scratchpad` directory before the product's `ActiveOutfitOverlay` and `LayeredFullBodyRenderer` produce four eye states. Native, body, and hand inputs retain canonical paths and pinned bytes; source drift, identity violations, and out-of-scope replacements fail explicitly. `receipt.json` is written only after all validation completes, and the result still awaits owner visual approval.

Garment, hairstyle, and headwear edits use `pack_updates`; each pack declares its `target` and `members`, while each member pins the candidate `source`, existing archive member `target`, candidate `sha256`, and a pre-authored `allowed_change_mask`. The mask must have the same canvas, contain content, and use only `0` and `255`; paths use `/`. `reference_preview` pins the baseline `receipt_sha256` and `input_manifest_sha256`, while `reference_frames` pins four matching-state frames. Inactive, cross-view shared, and out-of-mask changes are rejected.

Optional `makeup_updates` is a flat member list limited to existing `cheeks`, `eyes`, and `lips` members in the current view and selected variant of `mohan.makeup.builtin`, including existing half-closed and closed-eye members for that view. The complete pack must be pinned in `files` at its canonical path and SHA. Candidate alpha must exactly match the original member; RGB may change only in the intersection of original visible alpha and `allowed_change_mask`. `foundation`, new declarations, inactive or shared members, native-image paths, and candidates not pinned under `scratchpad` fail.

Optional `makeup_slot_intensities` uses the product's `eyes`, `cheeks`, `lips`, and `foundation` settings, each a finite number from `0` to `1`; omitted values default to 1. Baseline and candidate normalized settings must match. A makeup candidate must also report `same-state-face-core-identical-outside-authored-makeup`: every frame has zero face-alpha and protected-region change, with a positive change in the approved cosmetic region. These settings do not alter assets or personal settings.

After owner approval and affected tests pass, `integrate_source_bound_pack` can install one selected outfit. Its caller supplies the candidate receipt SHA, the owner's approval text, a SHA-pinned regression report with exit code `0`, and a post-write runtime check. It backs up before atomic replacement, safely restores bytes written by this run while preserving concurrent content, and writes the success receipt last; `release` is `false`.

When the same candidate contains one selected outfit and the canonical built-in makeup pack, `integrate_source_bound_packs` treats them as one local transaction. It validates all sources, fresh rebuilds, complete staged files, approval, regression evidence, and both formal baselines before writing; it backs up both packs before sequential atomic replacement and calls `postcheck` once only after both updates complete. Every failure attempts safe recovery for each pack and reports ordinary recovery errors separately from concurrent changes. The success receipt is written last with `release` set to `false`; `integrate_source_bound_pack` continues to reject makeup updates. Neither entry point writes native images or publishes.

## 日本語

`source_bound_manifest` は現在の入力を固定し、`source_bound_preview` は新しい `scratchpad` ディレクトリに候補を作成してから、製品の `ActiveOutfitOverlay` と `LayeredFullBodyRenderer` で四つの目状態を生成します。原生画像・身体・両手は canonical パスと固定 bytes を保ち、ソースの変化、識別違反、範囲外置換は明示的に失敗します。全検証の完了後だけ `receipt.json` を書き込み、成果物は所有者の目視承認待ちです。

衣装・髪型・髪飾りの変更には `pack_updates` を使い、各パックは `target` と `members`、各メンバーは候補ソース `source`、パック内の既存メンバーパス `target`、候補の `sha256`、事前作成した `allowed_change_mask` を固定します。マスクは同じキャンバスで空ではなく、`0` と `255` だけを含み、パスには `/` を使います。`reference_preview` は基準の `receipt_sha256` と `input_manifest_sha256`、`reference_frames` は同じ状態の四フレームを固定します。未選択、別視点と共有、マスク外の変更は拒否されます。

任意の `makeup_updates` は平坦なメンバー一覧で、`mohan.makeup.builtin` の現在選択中の変体・視点に既存する `cheeks`、`eyes`、`lips` だけを更新でき、同じ視点に既存する半閉じ・閉じ目メンバーも含みます。完全なパックを canonical パスと SHA で `files` に固定する必要があります。候補 alpha は元メンバーと完全に一致し、RGB は元の可視 alpha と `allowed_change_mask` の交差内だけ変更できます。`foundation`、新規宣言、未選択・共有メンバー、原生画像パス、`scratchpad` 配下で固定されていない候補は失敗します。

任意の `makeup_slot_intensities` は製品の `eyes`、`cheeks`、`lips`、`foundation` 設定を使い、各値は `0` から `1` の有限数で、省略値は 1 です。基準と候補の正規化設定は一致する必要があります。メイク候補には `same-state-face-core-identical-outside-authored-makeup` 状態も必要です。各フレームの顔 alpha と保護領域の変化はゼロで、承認済みメイク領域には正の変化が必要です。これらの設定は素材や個人設定を書き換えません。

所有者の承認と影響範囲のテスト完了後、`integrate_source_bound_pack` は選択済み衣装一つを接入できます。呼び出し側は候補 receipt SHA、所有者の承認文、SHA 固定かつ exit code `0` の回帰レポート、書き込み後 runtime 検査を提供します。先にバックアップしてから原子的に置換し、今回書いた bytes を安全に復元しつつ並行内容を保持し、成功 receipt を最後に書きます。`release` は `false` です。

同じ候補に選択済み衣装一つと canonical built-in メイクパックがある場合、`integrate_source_bound_packs` は一つのローカルトランザクションとして扱います。全ソース、fresh rebuild、完全な stage、承認、回帰証拠、二つの正式基準を事前検証し、両パックを先にバックアップしてから順番に原子的に置換し、両方の更新後だけ一度 `postcheck` を呼びます。すべての失敗で各パックの安全な復元を試み、通常の復元エラーと並行変更を分けて報告します。成功 receipt は最後に書き、`release` は `false` です。`integrate_source_bound_pack` は引き続きメイク更新を拒否します。どちらの入口も原生画像を書き込まず、公開しません。
