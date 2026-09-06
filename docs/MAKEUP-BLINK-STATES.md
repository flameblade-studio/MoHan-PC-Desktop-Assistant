# 眨眼妝容切換／眨眼妆容切换／Blink makeup switching／まばたき時のメイク切替

## 繁體中文

妝容變體可選填 `eye_states`，同時提供 `half` 與 `closed`。每個狀態沿用 `poses` 的完整 31 姿勢規則，只接受全畫布、原點定位的 `eyes` 圖層。封裝、匯入與執行期保留雜湊、安全區、虹膜及口腔保護。

半身與全身依眨眼狀態切換眼妝，腮紅及唇妝保持原層；三項濃度繼續相乘。快取包含眼睛狀態，滑桿變動會清除所有狀態。未提供狀態素材的舊套件保留原有閉眼隱藏眼妝行為。此功能不代表所有新素體素材已完成接入。

## 简体中文

妆容变体可选填 `eye_states`，同时提供 `half` 与 `closed`。每个状态沿用 `poses` 的完整 31 姿势规则，只接受全画布、原点定位的 `eyes` 图层。封装、导入与运行时保留哈希、安全区、虹膜及口腔保护。

半身与全身依眨眼状态切换眼妆，腮红及唇妆保持原层；三项浓度继续相乘。缓存包含眼睛状态，滑块变动会清除所有状态。未提供状态素材的旧套件保留原有闭眼隐藏眼妆行为。此功能不代表所有新素体素材已完成接入。

## English

Makeup variants may include `eye_states`, providing both `half` and `closed`. Each state follows the complete 31-view `poses` contract and accepts only full-canvas `eyes` layers anchored at the origin. Packaging, import and runtime retain hashes, safe regions, iris and oral protection.

Half-body and full-body rendering select eye makeup by blink state while retaining cheek and lip layers. The three intensity factors still multiply. Caches include eye state and slider changes invalidate every state. Legacy packs without state assets retain existing closed-eye suppression. This feature does not establish completion of every rebuilt body asset.

## 日本語

メイクのバリエーションには任意の `eye_states` を指定し、`half` と `closed` を両方用意できます。各状態は `poses` の全31ポーズ契約に従い、原点に配置した全キャンバスの `eyes` レイヤーのみを受け付けます。パッケージ化、インポート、実行時のハッシュ、安全領域、虹彩と口腔の保護を維持します。

半身と全身の描画では、まばたき状態に応じてアイメイクを切り替え、チークとリップのレイヤーを維持します。3つの濃度係数は引き続き乗算されます。キャッシュに目の状態を含め、スライダー変更時に全状態を無効化します。状態素材がない従来のパックは閉眼時の非表示動作を維持します。この機能は全素体素材の接続完了を意味しません。
