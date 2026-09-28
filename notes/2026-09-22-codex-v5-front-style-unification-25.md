# V5 正面漢服統一與原生造型結案工作，session 25

本輪 session：`codex-20260921-v5-native-closeout-25`。9/21 開輪、9/22 續作。

## 開輪與範圍

- 開輪 revision 153，checkpoint SHA `d35f1735e563cbcd211a43020bb3130a4fabc348591f23b344fbd4596b952506`；status 無鎖，verify 退出碼 0、inventory_complete=true、access_warning_count=0，claim 成功。
- branch `integration/worktree-consolidation-20260916`、HEAD `3fe2b7dd5a03bebf92b90ba6be1b0e5e6c79a009`，既有 168 項 porcelain 狀態保留。
- 使用者已取消「需要散髮」的推論；新散髮設計移出結案範圍。原生髮型／髮飾的可拆與選單語意問題仍列實際未完成項目。
- 使用者指出全身總覽有三種衣色與款式，並指定「我喜歡正面的那種」。以現行 +000 neutral-rest 的灰藍薄紗、白交領與白裙為統一基準，決定記於 `scratchpad/mohan-v5-hanfu-unified-front-163/owner-style-authority.json`。此決定不等於未展示的側背圖已批准。

## 唯讀現況核對

正式 PNG 尺寸與模式：V5 base 24 張 1024×1536 RGBA，layered 654 張 1024×1536 RGBA，V7 complete-expressions 84 張 1254×1254 RGBA，reviewed-garments 75 張（8 張 L、67 張 RGBA）1254×1254。

兩位 Sol Medium 唯讀審查回報：

- ±90° 五個官方圖層侵入臉保護區，renderer 正確拒絕並退回素體。既有 1,488 張矩陣中 100 筆衣裝失敗不能計作成功。
- 官方 24 全身視角只有 19 張 silhouette、13 張 replacement mask；+075、+135、+150 兩者均缺，與背心／肌膚殘留相符。衣裝 PNG 本身的款式差異另需來源比對，不能歸因於遮罩一項。
- 七半身原生髮型由 native alias 保留；舊 loose-hair 選項名稱與原生髮髻不符；六姿勢關閉頭飾畫面零差，尚未達真正獨立切換。

## 助理與命令

- 本機 Qwen health=ok；`python D:/LocalAI/ask-local.py --max-tokens 1600 --temp 0.2 <三語狀態翻譯規格>`：exit 0，380 tokens / 13.0 秒（29.2 tok/s）。主代理校對，日文「散髪」「款式」須改為自然的髪型／意匠用語。沒有外送專案資料到 DeepSeek。
- 兩個探查的猜測路徑不存在：`audit_fullbody_matrix.py`、舊 source-bound inventory 的 `receipt.json`／`manifest.json`。實際入口為 `audit_fullbody.py`、`formal-inventory.json` 及各 view manifest；保留失敗，不代表資料缺失。

## 後續

固定來源及樣式 → 查可重用採用原圖 → 缺少角度補繪候選 → 擁有者審閱 → 抽取同源可拆衣裝和遮罩 → staging 實際渲染 → 安裝收據與正式重載。尚未建立新款正式安裝。

## 本輪新證據

- `python scratchpad/mohan-v5-hanfu-unified-front-163/audit_current_costume.py`：exit 0，直接從正式 archive 讀出 24 衣層，逐張記錄 native／衣層／遮罩 SHA，輸出衣層原始像素總覽。主代理目視確認：鮮藍與灰藍兩組款式差異已在衣層 PNG 裡，+075 的黑色胸口也在衣層本身；缺遮罩不能單獨解釋或修掉這些外觀。
- 有效遮罩數再次實測：silhouette 19、replacement 13、body overlay 15。這些是盤點，不是 24 角度外觀通過。
- Sol 查指定衣裝工作樹與收據，未找到可確認已採用的同款側背原圖。舊 V4 權威明確 superseded，+075 原型候選僅 scratch extraction ready、formal_integrated=false、owner_visual_acceptance_claimed=false。
- 已使用 built-in image_gen 各生成一次 +090 側面與 −180 背面候選，實際提示詞記於 `candidate-prompts-01.json`。兩張已從 generated_images 逐位元組複製到 163，尺寸均 1024×1536 RGBA，alpha 0..254；有生成光暈，尚未完成有效去背，不能當乾淨圖層。
- 候選 SHA：+090 `8f10ad016ea88eb0b53ac058c45a12e227073c4408a43f70cc03b727d4cc080e`；−180 `8f724d2a8dd74150906dae0de0187c1d97c7a90e9b960d98da7043190d3c537e`。完整狀態見 `candidate-set-01.json`，三圖並排見 `review.html`。
- 主代理看圖：候選採灰藍寬袖、稀疏白紋，待 owner 確認新補的側背服裝結構；不沿用生成臉、髮、手作正式原生像素。未去背、未抽取、未安裝、未做這兩張的 runtime 測試。
- 複製命令首次因 PowerShell foreach 尾端空 pipe 語法錯誤 exit 1，未執行寫入；移除空 pipe 後重跑 exit 0。`tools/audit_language_sections.py` 猜測路徑不存在，實際使用既有 `tools/check_four_language_docs.py`。
- 中途 checkpoint revision 154，SHA `0e5e9688c5472740e2ab759f80abf19906513ea5405cdb26648ff59f3f734f7e`，inventory_complete=true、access_warning_count=0。

## 本輪檢查與收尾

- `.venv315/Scripts/python.exe -m ruff check .`：exit 0，All checks passed。
- 以 `tools.check_four_language_docs.audit_document` 直接稽核 `docs/v5-body-current-status.md` 與 `docs/hanfu-design-authority.md`：兩者錯誤清單均為空，exit 0。包含未追蹤現況頁。
- `git -c core.whitespace=blank-at-eol,blank-at-eof,space-before-tab,cr-at-eol diff --check`：exit 0；Git 印出三個 CRLF 正規化提示，未為此改寫任何素材。
- 候選複製雜湊：專案副本／generated_images 原檔／candidate-set 三方 2/2 相符；盤點 receipt 所列三個 artifact 的 SHA 全符；正式衣裝 archive SHA 與開輪一致。此命令 exit 0。
- 本輪沒有 runtime 或正式程式碼修改，未重新執行既有已通過 pytest；新圖須先由 owner 決定外觀。正式寫入 0、未 commit／PR／merge／release 軟體／tag。
- 兩位 Sol 唯讀子工作已完成；本機 Qwen 與 image_gen 均已結束。以相同 session checkpoint、協作 release，最後唯讀 verify；最終 revision／SHA 以 ledger 與回覆為準。
