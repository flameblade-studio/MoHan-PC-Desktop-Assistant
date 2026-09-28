# 2026-09-21 V5 完整表情擁有者退回與全身角度稽核

## 七姿勢完整表情：正式安裝已完整回滾

七姿勢 × 12 態候選先前已通過 alpha、嘴部安全區、loader 與 renderer 的機械驗證，並依擁有者先前的整組採納授權正式安裝 84 張畫格與一份 manifest。擁有者查看放大後的七組嘴型比較，明確指出「看起來好怪，不像原來的墨寒，有偏差」。這項最新外觀判定優先於先前整組採納，也證明機械邊界通過不足以代表人物身份正確。

正式安裝已用原安裝計畫與逐位元組備份完整回滾：25 個既有目標恢復安裝前 SHA-256，60 個本次新建目標移除，正式 `assets/expressions/complete-expressions/` 回到安裝前 25 個檔案。回滾收據為 `scratchpad/mohan-v2-v5-complete-seven-151/formal-installation/owner-rejection-rollback.json`，SHA-256 `dae5225c38c7ee56f49599b876867709efb15b75fb92d49ffe641138355576c7`。

候選 manifest SHA-256 `143f25b6c77cf2df6338a75e4ae4ad211c123da16d5d8816d96235fd537cf239` 已列為擁有者退回，不得再安裝或當作身份參考。回滾後 `tests/test_expression_pipeline.py` exit 0／`EXPRESSION_PIPELINE_OK`，相關回歸 `87 passed`。

後續若要補齊七姿勢嘴型，必須以擁有者最新確認的二代素顏畫格為身份基底，只在嘴部安全區建立可逆變化，並重新提供足以看清臉部輪廓與五官比例的視覺檢視；先前候選不沿用。

## 全身 24 yaw 來源稽核

`scratchpad/mohan-v2-fullbody-source-audit-152/` 重新比對正式 `v5-base`、擁有者指定的 V5 來源庫及既有 generated_images。24 個 yaw 中 20 個可直接精確對回來源；原先列為待補的七個角度中，`yaw+075`、`yaw-030`、`yaw-105` 可精確對回既有生成來源，`yaw+045`、`yaw-045`、`yaw-060` 為同代 V5 外觀，只有 `yaw-090` 明確仍是白／灰舊衣裝與舊代外觀。

既有 24 視角 600 個分層檔案的 package 與 semantic audit 目前通過，但該檢查只能證明檔案契約與重建關係，不能辨識世代錯置。

## `yaw-090` 隔離修復候選

`scratchpad/mohan-v2-yaw-minus090-repair-153/` 釘選既有 V5 來源 `exec-df0a397e-a393-4340-94dd-1ed1c9166ac9.png`，來源 SHA-256 `94b329c684d1d51ccac5697f2f57669176a6111b4d5ee674041471e79bbbbd68`。離線 BiRefNet 去背輸出 RGBA SHA-256 `9bef85b6b0e20da4cc4662e1f0cb814e0622adaad945eb3576c889fac6cb3cc8`；RGB 與來源逐像素相同，alpha sidecar 相同，前景未碰觸畫布邊界。

此候選尚未寫入正式素材。正式 runtime 同時使用 authority image 與 25 個可拆層，只換 `v5-base/yaw-090-pitch+00.png` 會造成跨世代混用。下一工作單元是從候選建立完整 25 層、驗證精確重建與 runtime 切換，再以單一原子計畫更新該視角。

## 仍未結案

- 七姿勢嘴型 84 態：候選已退回、正式安裝已回滾，需重新建立身份一致的嘴型來源。
- `yaw-090`：需完成 25 層 V5 重建、隔離渲染與正式原子安裝。
- 其餘 yaw 的來源鏈與分層重建關係仍需最後收斂。
- 在上述項目與總體 completion matrix 完成前，不宣告二代素體所有姿勢、角度與動作完成。
