# V5 七姿勢嘴型批次：v6 退回，v7 原生嘴部座標修正待視覺裁定

日期：2026-09-21  
工作階段：`codex-20260921-v5-completion-18`

`front-crossed` v4 pilot 曾由擁有者回覆「可以採用」。第一批沿用該方法，從未改動的 V5 核准母版建立其餘六個姿勢的 `small`、`A`、`O`。擁有者其後在七姿勢總覽逐一框出嘴角線不自然或過長的項目，因此該批已整批標記為 `rejected_batch_v1`；其檔案以 `.v1` 名稱保留為退件證據，不得正式安裝。

v2 重新涵蓋七姿勢 × `small`／`A`／`O` 共 21 張。生成影像只提供中央口腔開合；每張成品仍以該姿勢未改動的 V5 核准 RGBA 為母版。混合遮罩取消 v1 的外圍唇線權重，只保留中央橢圓口腔區，並硬性鎖住嘴框左右各 18%：這些區域在 21/21 張中均為 0 像素變動。第一張 `left-neutral/O` 的粉色圓環來源與 v1 候選都沒有被 v2 引用。

批次建立時另發現 `assets/makeup-safe-regions.json` 的 `front-exasperated` 嘴唇框仍是正面姿勢座標 `[555, 524, 125, 72]`，實際位於傾斜臉的嘴上方。本批在隔離區以實際嘴位 `[540, 580, 145, 100]` 建立候選，並在 receipt 同時記錄登錄值與隔離修正原因；尚未修改正式 safe-region 設定。

驗證結果：

- 21/21 候選為 1254×1254 RGBA。
- 21/21 alpha 變動像素為 0。
- 21/21 候選嘴部框外 RGB 變動像素為 0。
- 21/21 左嘴角與右嘴角鎖定區的 RGB 變動像素均為 0。
- 被退回的粉色圓環來源未被引用。
- v1 候選未被當成 v2 來源。
- v2 建立器與驗證器的 Ruff 檢查通過。

v2 總覽：`scratchpad/mohan-v2-v5-mouth-rebuild-158/seven-pose-mouth-overview-v2.png`。每個姿勢另有 `*-mouth-review-v2.png` 臉部與嘴部放大表；擁有者框選項目的母版／v1／v2 對照為 `owner-marked-mouth-corners-v1-v2-comparison.png`。完整來源、輸出雜湊與像素計數在 `receipt-v2.json`；機械驗證在 `validation-v2.json`。v1 退回依據為 `owner-rejection-batch-v1-mouth-corners.json`。

狀態為 `owner_review_pending_not_formal`。正式素材寫入 0；尚未更新 complete-expression manifest、renderer 或 runtime 封包，也未以測試通過替代擁有者外觀裁定。擁有者批准整批後，下一步才是更新頭痛姿勢嘴唇框、建立七姿勢 84 態完整表情、隔離實載渲染、原子正式安裝與相關回歸。

## v2 退回與 v3 修正

擁有者在 v2 對照再框出五個仍有缺口或短線的項目：`front-crossed/O`、`left-neutral/small`、`left-neutral/A`、`cheek-rest/A`、`front-eureka/O`。根因是中央口腔遮罩雖鎖住外側嘴角，仍在內唇線上形成裁切端點；增加羽化與 seamless clone 的隔離實驗會讓開口消失或只把缺口模糊化，均未採用。

v3 針對這五項直接從未改動的 V5 母版重建完整且連續的嘴型來源，再於各姿勢嘴唇矩形內以柔邊完整唇形合成。其餘 16 項逐像素沿用未被框選的 v2。v3 共 21/21 張為 1254×1254 RGBA、alpha 零變動、嘴唇矩形外零變動；五項修正均引用新的 `generated-source-v3.png`，沒有引用被退回的 v2 作為修正來源。

其中一張 raw imagegen 中繼來源因輸入透明度被模型重畫成橢圓灰底，並改變雙手陰影。該檔只允許抽取嘴唇矩形；背景、雙手、身體及其餘臉部均由核准母版提供。正式 v3 驗證的嘴唇矩形外 0 像素變動即為此隔離契約的實測證據；raw 中繼圖不得直接成為候選或正式資產。

擁有者框選項目的母版／v2／v3 對照為 `owner-marked-mouth-gaps-v2-v3-comparison.png`；七姿勢總覽為 `seven-pose-mouth-overview-v3.png`，完整紀錄與驗證為 `receipt-v3.json`、`validation-v3.json`。正式素材寫入仍為 0，等待 v3 視覺裁定。

## v3 開口不均退回與 v6 候選

擁有者在 v3 再框出 `left-neutral/small`、`left-neutral/A`、`cheek-rest/A`，判定嘴部開口不自然、不平均。該決定已寫入 `owner-rejection-v3-uneven-openings.json`。v4、v5 為內部重建嘗試，因遠側開口仍過早收合或近似單側裂縫，未提交視覺裁定，也未進入正式素材。

v6 以三張各自未改動的 V5 核准母版為身份與姿勢基準，另以已穩定的 `front-crossed` small／A 嘴型限制開口曲線；完整生成圖仍只作嘴唇矩形來源。三張修正版與其餘 18 張未被本次框選的 v3 候選共同構成 21 張 v6 隔離候選。

驗證結果：21/21 張為 1254×1254 RGBA、21/21 alpha 零變動、21/21 嘴唇矩形外零變動；三張修正版均引用 `generated-source-v6.png`，raw 來源的背景、雙手、身體與嘴唇矩形外像素均不得進入候選。母版／退回 v3／修正 v6 放大對照為 `owner-marked-uneven-openings-v3-v6-comparison.png`，完整總覽為 `seven-pose-mouth-overview-v6.png`；來源雜湊、輸出雜湊與像素計數在 `receipt-v6.json`，機械驗證在 `validation-v6.json`。

狀態仍為 `owner_review_pending_not_formal`。正式素材寫入 0；未更新 complete-expression manifest、renderer、runtime 封包或正式安全區設定。

## v6 退回與 v7 裁切座標根因修正

擁有者再次明確退回右欄三張：`left-neutral/small`、`left-neutral/A`、`cheek-rest/A`，原話「不行，右欄3張的嘴型開口還是不自然流暢」。截圖與 SHA 已保存於 `owner-rejection-v6-unnatural-openings.json`。前文把 v4／v5／v6 單側開口主要歸因於生成來源，判斷不充分；本次逐張並排核對 raw 完整來源與實際候選，確認主因是沿用錯置嘴唇框和合成遮罩，造成完整新嘴的右半邊被原本閉唇覆蓋。

- `left-neutral` 舊框 `[445,544,121,73]` 在 x=566 結束，V5 嘴唇實際延伸至約 x=607。
- `cheek-rest` 舊框 `[452,547,118,76]` 在 x=570 結束，V5 嘴唇實際延伸至約 x=623。
- 因此舊的「嘴框外零變動」只驗出遵守錯框，沒有證明嘴框位於正確位置。診斷圖為 `v7-coordinate-root-cause.png`。

v7 使用 `v7-mouth-geometry.json` 釘選的原生 1254×1254 嘴部多邊形：完整上下唇、開口及兩側嘴角使用既有 source 原始像素，10 px 羽化位於外側皮膚；不縮放、不拉伸或補畫嘴型。這兩個姿勢的 small／A／O 共六張都受舊框影響，因此一併重新抽取；本次新圖生成次數為 0。其餘十五張逐像素沿用 v6 候選，不因此取得新外觀批准。

三張框選比較圖：`owner-marked-mouth-v6-v7-comparison.png`，左為核准 V5 原圖、中為 v6 合成、右為 v7 完整抽取。另有六張比較圖 `two-pose-six-mouths-v7-comparison.png` 與七姿勢總覽 `seven-pose-mouth-overview-v7.png`。主代理已逐張檢視三張比較、六張來源、托腮 A 完整候選，確認 v6 裁切造成的單側閉合已消除；這是主代理檢視，不替代擁有者裁定。

實際驗證：

- `python scratchpad/mohan-v2-v5-mouth-rebuild-158/validate_corrected_v7.py`：exit 0；21 張尺寸／RGBA／alpha／正確嘴框外像素核對通過，六張完整嘴型 core 與對應 raw source RGB 完全相同，合成遮罩之外 RGBA 零變動。
- 六張舊錯框輸入均被新增的「完整嘴型覆蓋」檢查拒絕；單像素框外污染的負向案例亦全部被偵測。詳見 `validation-v7.json`。
- 正式素材盤點的 704 個檔案全部維持原 SHA；正式寫入 0。
- 三支新增 v7 程式的 Ruff：exit 0。全庫 `python -m ruff check .`：exit 1，六項 unused-import 均來自既存未追蹤 `.pytest-v5-formal-seven-regression-01`、`.pytest-v5-line-gate-01` 的測試暫存 probe/product.py；沒有更改或豁免這些檔案，不能宣稱全庫 Ruff 通過。
- 本輪修正尚在隔離素材，沒有執行正式安裝、84 態整合或 runtime 發布。

本機 Qwen3.8-27B 提供驗證條件建議，主代理已審查；223 tokens／8.2 s／27.1 tok/s。已採納 core 完整覆蓋、來源像素相等、mask 外不變、alpha 不變及 hash 釘選五條；排除模型對舊程式 alpha 問題的未證實歸因，並更正其「core 外全不變」說法為「mask 零值區全不變，外側皮膚羽化環可合成」。原始答覆及審查記錄見 `local-qwen-validation-review-v7.json`。第一次 helper 因過期模型別名 HTTP 400，讀取本機實際載入 ID 後使用同一 Qwen 模型成功，未切換模型或修改 helper 設定。

狀態：`owner_review_pending_not_formal`。更正後待擁有者查看，保留同一 actor/session 編輯鎖並 checkpoint。後續若採用，須同時遷移 left-neutral、cheek-rest 與原已發現的 front-exasperated 正式嘴部座標，再進行 84 態與實載驗證；不能把本輪合成修正宣告為二代素體全部完成。

## v7 擁有者批准、84 態正式安裝與實載驗證

擁有者於同一輪檢視後回覆「我已確認完畢，這次沒問題了。」此批准已寫入 `scratchpad/mohan-v2-v5-mouth-rebuild-158/owner-approval-v7.json`，涵蓋七姿勢的 rest／small／A／O 外觀及後續 84 態整合與原子正式安裝；不包含發行、合併或發布授權。

正式候選以 v7 核准嘴型為四個嘴型家族，再只套用先前已驗收的七姿勢 half／closed 眼部貼片。第一版隔離驗證正確攔下 48 張眼部貼片 alpha 被帶入的問題，該版 `candidate-validation.json` 為 fail，從未安裝。第二版在眼部 RGB 合成後強制沿用各姿勢母版 alpha，結果如下：

- 84/84 張 alpha 與姿勢母版完全一致。
- 84/84 張嘴型變動均限制於 v7 核准嘴框。
- 56 個 half／closed 眼態變動均限制於既有眼部貼片支援範圍。
- 52 個 expression 綁定由 `CompleteHalfbodyRenderer` 實際載入；84/84 張 renderer 輸出在 alpha、實色像素及可見合成像素檢查全部通過。

原子安裝共處理 86 個目標：84 張完整表情影格、`assets/expressions/complete-expressions/manifest.json` 與 `assets/makeup-safe-regions.json`。正式嘴部安全框同步修正為 `left-neutral [509,560,117,91]`、`cheek-rest [525,570,113,91]`、`front-exasperated [540,580,145,100]`。安裝收據為 `scratchpad/mohan-v2-v5-complete-seven-v7-formal-159/formal-installation-v7/receipt.json`。

安裝後從正式路徑重新載入驗證：86/86 安裝目標 SHA-256 與核准計畫一致，84/84 來源與 84/84 runtime 輸出通過，52 個綁定有效，無 alpha、嘴框、眼部範圍或可見像素失敗。正式驗證為 `formal-verification-v7.json`，實載接觸表為 `formal-verification-v7-artifacts/v7-84-state-runtime-review-v2.png`。

回歸結果：七個相關 pytest 模組共 `47 passed`；`tests/test_expression_pipeline.py` 輸出 `EXPRESSION_PIPELINE_OK`、exit 0；stage 159 的六支程式 Ruff 通過。全庫 Ruff 仍為 exit 1，僅有六項既存未追蹤 `.pytest-v5-formal-seven-regression-01`／`.pytest-v5-line-gate-01` 暫存 fixture 的 unused `json` import；本輪未刪除、修改或豁免這些既存檔案。

本項狀態為 `owner_approved_formally_installed_runtime_verified`。沒有執行 release、merge 或 publish；也不以本項結案宣稱所有二代素體其他待辦均已完成。
