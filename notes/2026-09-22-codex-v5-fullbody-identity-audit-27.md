# V5 全身衣裝與原生身分核對（工作階段 27）

本階段依擁有者指出的三款衣裝不一致與 −090° 候選不像原生 V5，重新核對正式 runtime。鎖 session `codex-20260922-v5-closeout-all-27`；對既有未提交工作只做增量修改，未 reset、提交、合併或發佈。
最後核對 branch 為 `integration/worktree-consolidation-20260916`、HEAD `3fe2b7dd5a03bebf92b90ba6be1b0e5e6c79a009`，`git status --short` 180 項；開輪已有大量既有未提交／未追蹤變更，這個數字不能單獨歸因於本階段。

## 已確認的正式狀態

- 前一階段已採用並正式接入 +090°、−180° 兩個可拆衣裝角度；`scratchpad/mohan-v5-hanfu-unified-front-163/formal-installation-26/receipt.json` SHA-256 `f289791d763a9d4dea0801f0f75034e767c063643c79ad4ed561d5f6b45e6a21`，本階段未重做。
- 本階段執行 `scratchpad/mohan-v5-hanfu-unified-all-164/audit_formal_24.py formal-baseline-27`，退出碼 1，原因是 24 角度中 6 個衣裝選擇實際無作用（−090、−105、−120、−135、−150、−165）；這是本次診斷刻意的失敗回報。其餘 18 個有衣裝不代表款式統一；實際影格與逐角度資料見 `formal-baseline-27/frames/`、`formal-24-contact.jpg`、`validation.json`。
- 24 角度依像素色調與整體款式盤點：正面及相鄰 −060° 至 +060° 的 9 角度可沿用擁有者喜歡的灰藍薄紗款；+090°、−180° 是前一階段已採用角度；其餘 13 角度仍有不同款式／鮮藍或缺衣裝，需新的原生 V5 身分合成候選及擁有者外觀判斷。技術遮罩的有無不構成外觀採用。

## −090° 退回與隔離修正版

- `yaw-090-pitch+00.hanfu-front-style-candidate-01.png` 已被擁有者明確指出「這張特別不像」；`owner-rejection-yaw-090-candidate-01.json` 保留拒收與來源 SHA。此原始生成圖沒有抽取、安裝或作為正式人物。
- 後續改以正式已採用 +090° 衣料鏡像，疊回原生 −090° 頭部，並使用已採用 +090° 的原生 V5 手部支援。`yaw-090-mirrored-native-review-01` 肩／腿外露，`-02` 頸部空白，兩者只是失敗的隔離試作；`-03` 頭部 49,029 個非透明像素與原生 −090° RGB 零差；`-04` 改善半透明領緣下的頸部支援，為目前待檢視候選。它仍有手袖／頸口接縫，且尚未獲採用、抽取或安裝。各版 `receipt.json` 詳列來源 SHA 與限制。
- 其他 +075°、−075°、−120° 原始生成圖仍是未採用候選；不得當作原生 V5 人物或已安裝成果。
- 嘗試兩次 −165° 無人物衣料圖，第二次依原生體型明確指定領口、腰帶、袖手與衣襬座標，仍留下與素體不符的垂直配準與背景光暈。兩張只存於隔離資料夾當失敗證據，未進視覺審查或正式安裝；後續角度不可沿用這兩張作款式來源。

## 舊髮型選擇與原生分層

- 已保留正式官方髮型舊 ID，以 V5 全身原生髮髻呈現，不再疊加上一代散髮；+090° 官方舊髮飾附加圖侵入受保護臉區，該視角跳過附加圖。使用者匯入款與前視髮飾原有開／關路徑未改；選單及提示以四語明示舊代號與原生圖內飾品不會因關閉附加層而消失。程式修改集中於 `domain/outfit_pack_official.py`、`infrastructure/active_outfit_overlay.py`、衣櫃選單與兩份語系檔，並增補精確回歸測試；前輪 `active_outfit_overlay.py` 既有來源綁定髒改保留。
- 隔離分層候選在 `scratchpad/mohan-v5-native-partition-closeout-27/`：±090° 誤入 `ornament` 的 867／563 個像素其實是已採用原圖的黑髮，原 RGBA 移至候選髮層；+090° 三髮層 y≥400 的身體／手／腿像素移至候選 body。候選 manifest SHA-256 `fb865748e268c2debc9b5d77f6d5dde8fd4bc540d35de1a86d924c8e8b7473d0`，7 張候選 PNG SHA 全相符。嚴格 authority 的 ±090° 7 嘴型 × 3 眼態共 42 張 bare 正式／候選逐像素 RGBA 零差。
- 這份隔離分層尚未正式安裝：官方／內建衣裝與 ±090° 髮飾開／關 96 張實際合成，候選／正式雖零差，但「開」與「關」本身也全為零差；所以開關未通過。+090° 官方飾品仍有 20 個臉保護區碰撞，−090° 官方衣裝／輪廓另觸發 fail-closed；非中性 `body_energy=0.7` 也被正式與候選共同的既有 `neutral_body_only` 契約拒絕。+090° 上半髮層仍含臉／頸／肩皮膚，母圖既有半透明灰邊尚在。詳見 `REVIEW.md`，不能因 42 張 bare 零差便安裝或宣稱獨立髮飾完成。

## 檢查與剩餘決策

- `python -m ruff check .` 退出碼 0；顯式檢查兩個新 scratchpad 工作資料夾，退出碼 0。
- 首次直接以預設使用者 Temp 執行相關 pytest 退出碼 1，25 passed／35 setup errors；錯誤均為 `C:/Users/USERNAME/AppData/Local/Temp/pytest-of-USERNAME` 的既有 `WinError 5`，不是程式斷言失敗。改用工作區獨立 `--basetemp D:/FlamebladeStudio/CodexProjects/.qa/mohan-v5-session27-pytest-01` 後，衣裝／衣櫃／架構 60 passed、退出碼 0；四語完整性 2 passed、退出碼 0。新隔離分層腳本與候選比對的退出碼亦為 0，但其接受範圍以表述限制為準。
- 原有七半身 V7、七姿勢漢服、31 剪影妝容與 24 全身原圖血緣未變。這次正式衣裝 PNG、原生分層 PNG、官方 archive 安裝 0 件；沒有 commit、PR、merge、tag 或軟體發布。
- 工作包一仍缺真正可見且安全的髮飾開／關及原生髮際灰邊處理。工作包二的 13 個角度需要新衣裝外觀供擁有者目視判斷；−090° 修正版 04 尚有接縫，未申請採用。正式 24 角度衣裝一致性仍不通過，不得宣告二代素體全案結案。
