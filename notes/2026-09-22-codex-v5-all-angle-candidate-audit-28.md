# V5 全身灰藍漢服 13 角度候選與正式接入門檻（session 28）

工作階段：`codex-20260922-v5-all-angles-candidates-28`。本次從交接 revision 161 取得鎖；沿用既有髒工作樹，沒有 reset、清理、提交、PR、合併、發行或 tag。正式素材安裝數為 0。

## 正式基線與採用範圍

- 正式 24 角度 neutral/rest 稽核：`scratchpad/mohan-v5-hanfu-unified-all-164/formal-baseline-27/validation.json`。−090、−105、−120、−135、−150、−165 六角選官方衣裝仍退回裸素體。九個正面相鄰角度維持已選灰藍款；+090、−180 兩角有擁有者採用及正式安裝收據。其餘 13 角尚未完成統一外觀。
- 使用者已指出先前生成的 −090 整張人物「特別不像」。該圖保持退回狀態，未作正式來源。本次 −090 僅沿用鏡像已採用 +090 衣料、原生 V5 頭部的隔離草稿 `yaw-090-mirrored-native-review-04`，仍有頸袖縫，沒有採用或安裝。
- 24 角的來源血緣缺口已於先前 session 22 補到 22 個外部原圖 RGB 精確吻合與 2 個 ±90° 擁有者採用／安裝收據；本次未修改 `SOURCE-PROVENANCE.json`，沒有重新宣稱來源封存以外的美術完成。

## 本輪新增的候選證據

- 由正式套件抽出 13 角舊衣層至 `archive-originals-28/`，只作幾何與舊款對照，未覆蓋套件。套件原 SHA-256：`2cc731341ccb81ddbabe50b4a515e2789824e275b6641ce89f39aa5df3ad569a`。
- 對 −165、−150、−135、−105 產生灰藍款完整人物衣裝來源，沿用既有 −120、−075、+075 衣裝來源；新圖的人臉、頭髮及手不是 V5 正式身分。其餘 +105、+120、+135、+150、+165 的隔離預覽只鏡像相應負角度衣料。沒有把完整生成圖裝成素體。
- 離線 BiRefNet HR 模型 `ZhengPeng7/BiRefNet_HR-matting` revision `5d6b6f8adcb5b417c871b1d84ceaae9871355b7f`。−165 兩次單張與六圖批次的實際程序退出碼均為 0。命令使用 `D:/FlamebladeStudio/CodexProjects/.tooling/birefnet-hr/Scripts/python.exe`、`D:/FlamebladeStudio/CodexProjects/.tooling/birefnet-hr/birefnet_matting.py`、`--output-dir` 指向各自新資料夾，環境為 `HF_HUB_OFFLINE=1`、`TRANSFORMERS_OFFLINE=1`、`HF_HOME=D:/FlamebladeStudio/CodexProjects/.tooling/birefnet-hr/hf-home`。`audit_matted_sources_28.py` 最新實際稽核 8/8 通過：各 1024×1536 RGBA、來源 RGB 精確保留、alpha 0..255 且 256 個值、四邊非零 alpha 0。收據 `dressed-matting-batch-28/audit-receipt-v2.json` SHA-256 `fcb0b5a107d80885b61fce284f36ecf7ea86a93a891088108e112cf62fbb2d94`；先前 7/7 收據保留不覆蓋。這是技術去背，非美術採用。
- `build_native_identity_candidates_28.py` 隔離輸出 `native-identity-candidates-28-v7/` 共 11 角，實際退出碼 0。候選逐張記載來源、原生 V5 圖與輸出 SHA；原生頭部保留的 RGB 變化 0。手部從原生 V5 圖以最近鄰縮放與位移補接，已在 receipt 誠實標示轉換，不能稱作原位 source-exact 正式手支援。`receipt.json` SHA-256 `4ebcd09215d10baa719603464170163d5b560fb3a75e2b0b6a1cb38c95d8de8f`；檢視頁 `review-28.html` SHA-256 `0d11c7ce67e281e6a233afeb9adf34cb7333cea727fd2ceaa07d16865261ccf5`；兩者只是草稿。另有 −165 原生頭手草稿 `yaw-165-native-composite-review-02`，總計 13 角皆有隔離檢視稿。
- 全專案 Ruff `& .venv315/Scripts/python.exe -m ruff check .` 退出碼 0；七張 matte 稽核退出碼 0。正式 renderer 的 24 角基線是上輪實測，不可挪作本輪候選的 runtime 驗收。

## 明確未通過與正式安裝前置

新角度的頸側仍有殘片／斷線；手與袖口尚有比例、細白邊及姿勢對位問題；±165 的衣料方向過於接近正背。−090 鏡像衣料草稿仍有頸袖接縫。這些是實際視覺不合格，不應請擁有者把有瑕疵草稿直接當作正式採用，也不應以程式通過代替外觀判斷。

為修 −165 姿態另以原生 −165 與已採用 −180 做兩次完整衣裝來源生成。source04 SHA `79cecd747cb14c1fc92e3e39cbb7748dd09d3fa123e261a41fc7f35b82041c65` 仍近乎正背；source05 SHA `cb5f8d624a7ba5022c55116447f757398da2bb297e6adab55b1a9b69344e0bbb` 雖較能看見偏轉耳側，離線去背／原生頭手合成 review03（receipt SHA `6665ea921a31a25bf568e1499805f78b6e7611d71f4d10b0e19581b6e2978ff0`）卻露出頸肩大塊斷口，故技術退回，未取代 review02、未列入正式候選。兩次同路線未改善，不再盲目重試。

正式 `infrastructure/source_bound_garment_visibility.py` 要求每角全畫布 RGBA 衣層、8-bit 二值可見遮罩、與原生 face/hair/ornament/hand 不相交的保護區、原生手支援（若使用）、官方套件 member SHA、來源 SHA 與選擇 manifest 綁定。若 13 角均需左右手支援，預期至少 41 個安裝目標：套件 ZIP、binding manifest、13 張 L 遮罩及 26 張 RGBA 手；還須擁有者新角度外觀核准、隔離正式 renderer 實際切換、安裝計畫與 receipt、正式重載驗證。本輪 13 角無一達到這些門檻，所以正式安裝 0。

髮飾切換未通過的原因已定位：+090 舊銀飾與保護區相交 20 像素而被刻意略過；−090 銀飾自身可載入，但舊漢服先與保護區相交 85 像素，使整幀 fail-closed 退回原生。`scratchpad/mohan-v5-native-partition-closeout-27/official-headwear-comparison.json` 中 96 張 on/off 無差異。該比較程式只把「候選等於正式」納入退出條件，退出 0 不是髮飾開關通過。本輪沒有把隔離 native partition 候選裝入正式素材。

後續順序：先修 13 角頸、手、袖接縫與 ±165 方向並取得新角度外觀判斷；再抽可拆衣層與可見遮罩，讓 −090 衣領及 +090 銀飾過保護區；隔離 staging 實測衣裝／髮飾開關及 24 角聯合矩陣；全過才走正式安裝器。正式基線、已採用兩角及七姿勢結果保持不變。
