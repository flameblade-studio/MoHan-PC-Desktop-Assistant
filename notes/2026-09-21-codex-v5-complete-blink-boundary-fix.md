# 2026-09-21 V5 完整半身眼態邊界修復

## 問題

`tests/test_expression_pipeline.py` 的 `eureka_front` 眨眼會把整張 complete-expression 畫格換掉，造成嘴型、手勢、身體與眼罩外像素一起改變。切換到 Bare 後仍能重現，確認根因在完整半身眼態合成，不是正式妝容封包。

## 修復

- `CompleteHalfbodyRenderer.blink()` 仍從已登錄的 complete-expression 端點取得 half／closed 眼瞼，但只讓呼叫端提供的眼部貼片 alpha 決定可替換範圍。
- 結果以目前正在顯示的畫格為底，因此嘴型、手勢、髮型、身體與眼罩外像素保持不變。
- 非 rest 眼態會依目前妝容上下文重新套用合法的眼態妝容；不具妝容能力的測試替身維持相容。
- 完整半身渲染器記住合成後畫格的 pose／mouth-family 綁定，使連續眨眼仍指向正確端點。
- 妝容責任留在 `complete_halfbody_renderer.py`，避免把 `layered_face_renderer.py` 推過既有 800 行門檻。

## 驗證

- 五個相關測試模組：`29 passed`。
- `tests/test_expression_pipeline.py`：exit 0，`EXPRESSION_PIPELINE_OK`。
- `tests/test_layered_facade_cycles.py`：`24 passed`。
- 四個修改檔 Ruff：`All checks passed!`。
- 診斷實跑：default 2,487 個、Bare 2,507 個變動像素；變動範圍 `[180,153]..[275,186]`，完整落在 blink rect `[180,153,96,34]`。

## 範圍

本工作單元只修正 complete-expression 的眼態替換邊界。沒有新增、重製或正式安裝美術素材；其餘二代素體的姿勢、角度與可拆分層仍依後續盤點逐項完成。
