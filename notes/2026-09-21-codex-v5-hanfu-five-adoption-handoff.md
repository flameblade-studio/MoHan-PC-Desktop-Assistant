# V5 五張藍白漢服整組採用後交接（2026-09-21）

## 使用者決定與邊界

使用者對 stage 161 檢視組明確說「整組採用」。這批准五張圖片的外觀方向及以其為可拆衣裝抽取來源；正式衣裝圖層尚須符合原生 V5 臉、髮、手的身分與 runtime 合成契約。核准檔：`scratchpad/mohan-v5-hanfu-five-candidates-161/owner-approval.json`，SHA-256 `697c4266ecdacfa5edba1c0c54b07ba7aa018073fa9bb11e25a715ec421ef0eb`；候選集合 `candidate-set.json` SHA-256 `19b7c719974bafacf932ec8b4286a15cbae3e5f50031103fc0fb9b318066888c`。

## 目前真實狀態

- 五張 1254×1254 原圖：`front-crossed`、`left-neutral`、`front-mock-scold`、`front-mock-hit`、`front-exasperated`，位於 `scratchpad/mohan-v5-hanfu-five-candidates-161/<pose>.hanfu-candidate-01.png`；檢視頁 `review.html`。
- 原生素體來源：`scratchpad/mohan-v2-v5-seven-pose-matting-146/originals/<pose>.source.png`；核准原生 RGBA：同 stage 的 `local-alpha-01/<pose>.source.birefnet-rgba.png`。生成後五張臉部 ROI 平均 RGB 差 4.93–6.57，不能以生成臉取代 V5 原生臉。
- 既有正式可拆漢服 manifest `assets/expressions/reviewed-garments/manifest.json` 只有 `cheek-rest` 與 `front-eureka`。新五張未去背、未抽取、未安裝、未實際渲染。
- BiRefNet 原預定輸出 `scratchpad/mohan-v5-hanfu-five-candidates-161/dressed-matting-01`。呼叫中斷，cell 已不存在，沒有退出碼；檢查時輸出目錄不存在，也沒有可見 Python 行程。切勿宣稱其已完成或以未知退出碼當通過。
- 工作樹在 `integration/worktree-consolidation-20260916`，HEAD `3fe2b7dd5a03bebf92b90ba6be1b0e5e6c79a009`；檢查時 git porcelain 152 項，含既有變動。不可重設、刪除或覆蓋。此輪未提交、開 PR、合併或發佈。

## 下一輪執行順序

1. 先讀工作區 `CODEX_PROJECT_HANDOFF.md`、`shared/agent-handoff/START_HERE.md`、專案狀態與精確 git status；交接鎖預期本輪釋放。依協定 `status → verify → claim` 取得新 session。
2. 檢查五張核准圖 SHA 與原生 V5 RGBA，離線重跑 BiRefNet 去背並取得真正退出碼、輸出完整性與遮罩檢查。Worker：`.tooling/birefnet-hr/birefnet_matting.py`；使用既有離線模型快取，勿再次生成同一姿勢。
3. 只由五張核准圖抽出可拆藍白漢服及相容手臂／手部覆蓋；原生 V5 臉、髮與手保持來源一致。檢視 `infrastructure/reviewed_garment_assets.py` 的每姿勢 native source SHA、灰階可見遮罩、全畫布 RGBA 圖層、outfit selection 和 SHA 契約。若生成衣袖必須遮蓋原生手臂，要以獨立層與可見遮罩處理，並檢查手指、衣袖與頸部邊界。
4. 在隔離 staging 重建五姿勢 × 表情／嘴型／眼態的實際 runtime 渲染，檢查臉髮身分、alpha、衣裝和手部邊緣、背景污染及任何妝容重複。既有二姿勢須做回歸；不得把整張生成圖直接設為素體。
5. 依 `tools/art_pipeline/approved_asset_install.py` 生成驗證計畫、原子安裝與 receipt；正式 manifest 加入五姿勢後再重新載入 renderer，驗證七姿勢實際衣裝切換。保存結果、SHA、退出碼與專案紀錄。擁有者已批准整組外觀及先前候選正式化方向，例行可逆抽取與驗證無需逐步詢問；只有新外觀偏差或不可替代的重大阻礙再請其裁定。
6. 尚有全身三個外部原圖血緣缺口：`yaw+045-pitch+00`、`yaw-045-pitch+00`、`yaw-060-pitch+00`。目前各有相符 Git blob，但未找到精確外部原圖；維持較低證據級別或找回原圖，不能偽稱全部來源封存。31 剪影妝容／眼態實際渲染矩陣已通過，不必重做素材。

## 已完成的相鄰項目

七姿勢 × 四嘴型 × 三眼態共 84 張 V7 表情已正式安裝，86/86 目標 SHA 相符，renderer 84/84 實測通過，相關 pytest 47 passed。31 剪影 × 三妝容 × 三眼態 279 張及 31 素顏實際合成零失敗。來源比例為 19 外部精確、2 擁有者核准側面、3 Git blob 無外部原圖。細節與當時測試結果見 `notes/2026-09-21-codex-v5-runtime-provenance-closeout.md`；勿把測試結果當成五張漢服接入驗收。
