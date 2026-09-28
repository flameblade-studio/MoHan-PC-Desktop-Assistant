# 二代素體 31 姿勢渲染及來源封存（2026-09-21）

## 範圍與來源

正式來源封存與渲染沿用 V5 素體、已核准的七動作嘴型和現有妝容封包；這兩項驗證沒有重生人物圖片。`scratchpad/mohan-v2-final-runtime-matrix-160/` 保存比對、安裝計畫、回復副本與收據。二十四個正式全身角度中，十九個找到外部原圖且正式不透明像素逐點相同；左右 90° 兩張有擁有者採用與正式安裝收據；`yaw+045-pitch+00`、`yaw-045-pitch+00`、`yaw-060-pitch+00` 的正式圖可對上 Git blob，但外部原始圖尚未精確找回。三者不可宣稱外部原圖來源完整。

`assets/pose-atlas/v5-base/SOURCE-PROVENANCE.json` 明列各來源、SHA-256 和三個缺口。來源狀態由過度概括的 `sealed` 更正為 `verified_artifacts_with_three_external_raw_source_gaps`，`BUILD-METADATA.json` 釘選新雜湊。更正收據：`scratchpad/mohan-v2-final-runtime-matrix-160/source-provenance-status-formal-installation/receipt.json`，2 個檔案原子替換，計畫 SHA-256 `950e8f242fc417b83f4283a309ac8b8ea7af83df0c15b8d0dc99f27c2f24b87d`。沒有變更圖像像素。

## 實際渲染與驗證

已核准的七動作新版嘴型安全範圍與原有妝容安全框有三處衝突；保留兩者的聯集，正式替換 `assets/makeup-safe-regions.json`，安裝收據在 `formal-installation/receipt.json`。正式封包的安全檢查恢復通過，沒有擴大到頭髮或衣裝，也沒有重畫妝容。

`isolated-runtime-validation-v4/validation.json` 為本輪最後驗證：31 個剪影 × 3 款妝容 × 3 眼態，共 279 張實際合成；另渲染 31 張素顏來源，0 項失敗。它檢查封包解析、圖層宣告與實際合成、alpha、眼態差異和安全範圍。這是技術驗證，不取代擁有者對每一張的美術目視採納。

本輪相關 pytest 分組 28、34、39 項通過；來源狀態更正後再跑來源相關 22 項通過，退出碼均 0。維護中的程式目錄和本輪修改腳本／測試的 Ruff 均通過。全樹 `ruff check .` 仍掃到既有 `.pytest-*` 與 `artifacts` 歷史證據中的 98 個錯誤；沒有改動歷史證據或放寬規則。

## 尚未結案

七個半身動作的可拆藍白漢服目前正式來源只含 `cheek-rest`、`front-eureka`。本輪另以每個動作的 V5 素體為編輯目標、已核准的 V5 藍白漢服來源僅作衣裝參考，透過內建 image_gen 各產生一張 `front-crossed`、`left-neutral`、`front-mock-scold`、`front-mock-hit`、`front-exasperated` 衣裝候選。五張完整 PNG、原圖對照、局部預覽、SHA-256 和像素差異在 `scratchpad/mohan-v5-hanfu-five-candidates-161/` 的 `candidate-set.json`、`review.html`。臉區平均 RGB 差 4.93～6.57，代表生成器有輕微重算，不能直接把候選人像當正式臉；未進行衣裝圖層抽取、正式安裝或替擁有者核准外觀。舊版穿衣人物不能代替 V5 素體。

另須逐一找回上述三個全身角度的外部原圖，或明確保留 Git 歷史來源級別。31 剪影渲染通過不表示所有身體、衣裝、表情與來源血緣已全面結案，也不授權發布。
