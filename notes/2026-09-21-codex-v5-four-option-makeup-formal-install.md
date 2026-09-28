# 2026-09-21 V5 七姿勢四款妝容正式安裝

## 結果

擁有者已授權整組美術採納，並要求所有候選轉為正式。本輪只使用既有 V5 原圖與既有生成影像，沒有重製圖片。Bare、Classic、Light、Glamorous 已完整涵蓋七個 V5 特殊姿勢；Classic、Light、Glamorous 各有 rest、half、closed 三種眼態。

擁有者退回的兩張歪髮 `front-exasperated` 來源已永久排除：

- `exec-f12fa538-55bd-4822-9de1-fc1cc7772374.png`，SHA-256 `5afdbee8feefc5421bfbb6fe2b4f382c89c7d8546dc7647872b91ae1f6201391`
- `exec-ced1e061-6432-4282-b75f-e405a4e2d0c9.png`，SHA-256 `6138a6f3c00072926ca572f5096281a8344b77d790802c97fe0072867c6ed3eb`

兩者記錄於 `scratchpad/mohan-v2-v5-eye-state-source-discovery-148/owner-rejected-sources.json`，沒有進入來源選擇、封包或正式安裝。

## 正式寫入

既有正式安裝器 `tools/art_pipeline/approved_asset_install.py` 完成兩筆原子替換，並保存可逐位元組回復的舊檔：

| 目標 | 安裝前 SHA-256 | 安裝後 SHA-256 |
| --- | --- | --- |
| `assets/official-packs/mohan.makeup.builtin.mohan-outfit` | `d3623485e533c049ffdc1134ecb5f1d67c504feed13552206f8376dfa6fd8a81` | `e37f5c7da3c047fff3087eb1033f9bb3e54b8e369c663b101afa595c032979a3` |
| `assets/makeup-safe-regions.json` | `4ca78a577d93ba65d5d6af0d9aaee6d999d59b9fa6f6222d953d91afa19b7552` | `eb56bd48dead6fd01479db1378dbe03db7e8e7625a1a9a51834e7b53b4b898d1` |

安裝計畫 SHA-256 為 `2454d6894324a95a4705195de894388990e9992822ab123771fb2a084491d778`。正式收據與備份位於 `scratchpad/mohan-v2-v5-eye-state-source-discovery-148/formal-installation-revision-18/`。

## 驗收

- 正式解析與安全區：`inspect_outfit_pack`、`parse_makeup_safe_regions`、`verify_makeup_layers` 全部通過；31 個 silhouette 可解析。
- 隔離渲染：63 張，0 失敗。
- 正式安裝後渲染：63 張，0 失敗；63/63 與隔離結果逐位元組相同。
- Bare：七姿勢均為 0 層，與 V5 素體逐像素相同。
- Classic、Light、Glamorous：七姿勢 × 三眼態皆載入三個宣告圖層；cheeks 保持透明。
- Light／Glamorous 的 42 張畫格與擁有者已檢視的 revision 21 逐位元組相同。
- Classic 只更新七個 V5 姿勢；其餘 123 個既有封包成員保持逐位元組相同。
- 相關回歸：42 passed。
- 全庫 Ruff：`All checks passed!`。

舊測試 `test_safe_region_document_matches_the_rigs` 原本強制所有正面姿勢共用同一組眼部矩形，與正式 V5 的逐姿勢眼位資料衝突。測試已改為保留兩個 legacy 眼框，並要求每個 V5 姿勢具備兩個獨立量測眼框；修正後該測試通過。

## 獨立既有缺口

額外執行 `python tests/test_expression_pipeline.py` 時，`eureka_front` 在完整表情畫格 blink 切換中有 29,668 個像素改變，範圍 `[128, 12]..[304, 461]`，超出 blink mask `[180, 153, 96, 34]`，因此 `blink_outside == 0` 失敗。切換到 Bare 後仍有 29,698 個像素以同範圍改變，證明它不依賴本輪正式妝容封包；來源是既有 complete-expression 全畫格切換。此項沒有改測試或放寬斷言，留作獨立產品修復。

診斷證據位於 `scratchpad/mohan-v2-v5-eye-state-source-discovery-148/expression-pipeline-eureka-diagnostic/`。
