### 動態換裝完整回退／动态换装完整回退／Atomic animated outfit fallback／動的衣装合成の一括フォールバック

- 服裝或妝容素材需要修正才能通過驗證時，整張動態合成回退至保留眨眼與嘴型的素體，並清除舊成功計數。／服装或妆容素材需要修正才能通过验证时，整张动态合成回退至保留眨眼与嘴型的素体，并清除旧成功计数。／If appearance or makeup assets require corrections to pass validation, roll back the entire animated outfit to the bare frame while preserving core blink and mouth motion, and clear stale success counts.／衣装またはメイク素材が検証合格に向けた修正を必要とする場合、まばたきと口の動きを維持して素体へ一括で戻し、古い成功件数を消去します。
- 保留既有合成介面，以及省略眨眼補丁時的既有眼妝行為；畫布尺寸改變後重新驗證素材與遮罩。／保留现有合成接口，以及省略眨眼补丁时的现有眼妆行为；画布尺寸改变后重新验证素材与遮罩。／Preserve legacy combined adapters and existing eye makeup behavior when authored blink patches are omitted; revalidate layers and masks after canvas size changes.／従来の合成インターフェースとまばたき素材を省略した場合のアイメイク動作を維持し、キャンバス寸法変更時に素材とマスクを再検証します。
