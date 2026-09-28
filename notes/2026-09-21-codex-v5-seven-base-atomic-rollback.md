# 2026-09-21 V5 七姿勢靜態底圖替換回滾

## 結論

七張已確認的 V5 姿勢去背來源本身有效，但不能直接覆寫既有
`assets/expressions/` 靜態底圖。既有嘴型、眼態及其他完整表情仍以舊代
底圖的臉部錨點為座標基準；只替換七張底圖會造成跨代混接。

正式安裝曾以既有安裝器原子替換七個目標，隨後立即執行
`python tests/test_expression_pipeline.py`。測試在表情錨點輪廓檢查失敗，
因此同一工作階段依安裝收據的備份逐檔回滾。回滾後七個目標皆與安裝前
SHA-256 相同，重跑 `python tests/test_expression_pipeline.py` 為 exit 0 並輸出
`EXPRESSION_PIPELINE_OK`。正式樹未保留退化狀態。

## 失敗方案

- 計畫：`scratchpad/mohan-v2-v5-seven-pose-expression-base-150/formal-installation-plan.json`
- 計畫 SHA-256：`c0f2e43f77044fa8ff4ad5f2d9895722069ea2de24133b23f9f8c5798c692b39`
- 安裝收據：`scratchpad/mohan-v2-v5-seven-pose-expression-base-150/formal-installation-01/receipt.json`
- 回滾證據：`scratchpad/mohan-v2-v5-seven-pose-expression-base-150/formal-installation-rollback.json`
- 隔離錨點診斷：`scratchpad/mohan-v2-v5-seven-pose-expression-base-150/isolated-anchor-regression.json`

隔離診斷記錄 13 個超出容許範圍的既有表情。`cheek` 家族多個表情的錨點
偏移約 5 至 6 像素；`front` 家族亦有多個表情偏移 3 至 5 像素。這些是
既有舊代表情與新 V5 底圖之間的幾何差異，不能靠放寬測試或只改靜態底圖
解決。

## 後續正式路徑

七姿勢 V5 應以獨立 complete-expression 接線交付：沿用已確認的 V5 rest
來源、既有生成庫中已選定的 half/closed 來源，以及既有嘴型資產建立同一代
的完整狀態組。這條路徑不得改動供舊表情使用的全域基準底圖；候選須先在
隔離 root 經 loader、renderer、嘴型、眼態、妝容及衣裝往返驗證，並經視覺
檢視後才可正式安裝。
