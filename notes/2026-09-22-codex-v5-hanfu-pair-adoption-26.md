# V5 已採用側背漢服：session 26

使用者回覆「可以」，採用 163 的 +090°／−180° 兩張衣裝候選。批准紀錄是 `scratchpad/mohan-v5-hanfu-unified-front-163/owner-approval-pair-26.json`；其餘新角度尚無自動批准。

開輪 status：revision 156、lock=null；verify exit 0，checkpoint SHA `c0df5c0871f0540fca12e4c8eea587c7cb65d1018c497a0b7931db439ae52017`、inventory_complete=true、access_warning_count=0。claim session `codex-20260922-v5-hanfu-pair-adoption-26` 成功。

正式盤點與前輪 aggregate SHA 完全一致：V5 base 24 張，layered 654 張，V7 84 張，reviewed-garments 75 張；畫布／模式仍分別為 1024×1536 RGBA、1254×1254 RGBA 或 L。branch 與 HEAD 保持 `integration/worktree-consolidation-20260916`／`3fe2b7dd5a03bebf92b90ba6be1b0e5e6c79a009`。

首次 worker 路徑沿用早期缺斜線記錄而不存在；實際已核对為工作區 `.tooling/birefnet-hr/birefnet_matting.py`。唯讀盤點 inline Python 初次因 shell quoting 失敗，改用 stdin here-string 後 exit 0；未影響正式檔案。

去背沿既有 offline BiRefNet HR worker 與固定模型 revision，保留真正子行程退出碼、stdout/stderr、原圖 SHA、輸出尺寸及遮罩。批准不是去背／抽取／安裝完成。

## 已完成範圍與安裝

- 本次原始採用只涵蓋 +090°／−180° 衣裝設計；兩張不是原生臉、髮或手來源。
- 離線去背真正退出碼 0，收據為 `163/adopted-pair-matting-26/process-receipt.json`。原生 alpha 輔助收據 `native-pair-matting-26/receipt.json` 也是 exit 0；原生 RGB 未變。
- 最終衣裝抽取為 `extracted-pair-26k`。領口／肩部／袖口只對衣料做局部位移；手部來自 native V5。+090 主手採官方 SAM ViT-B 的 mask-02，主代理檢視三個預測後補閉合內部洞、腕部及袖口裁切；不移動原生手 RGB。
- 衣裝專用 manifest 綁定 exact selection、native source SHA、archive garment member SHA、L visibility、左右手 SHA。手支援只在該衣裝通過來源驗證時生效，不改共用手部來源。
- 預檢 8 個目標 exit 0，原子安裝 8 個目標 exit 0；receipt SHA `f289791d763a9d4dea0801f0f75034e767c063643c79ad4ed561d5f6b45e6a21`。
- 僅正式 archive 內两個衣層及 manifest 兩個 SHA 改動；其餘 122 archive members 逐位元組不變。另新增 1 個衣裝綁定 manifest、2 個 L mask、4 個衣裝專用原生手 RGBA，共 8 個檔案目標。正式 pack SHA `2cc731341ccb81ddbabe50b4a515e2789824e275b6641ce89f39aa5df3ad569a`。
- 隔離 `isolated-pair-26k`：2 角度 × 4 嘴型 × 3 眼態 × 4 妝容 = 96 張，另關衣／還原 4 次檢查，共 100／0 failures。原生 pixel audit 96 張、24 張 bare 對照、4 手來源 RGB 全零差。
- 正式 `formal-reload-26`：重新載入真正正式 assets，100 次／0 failures，96/96 輸出 SHA 與 staging 相同；再次 native pixel audit exit 0、零差。檢視頁 `163/review.html` 顯示正式渲染及原始採用來源。
- V5 base 24 PNG、layered 654 PNG、V7 84 PNG、reviewed-garments 75 PNG 的開輪 aggregate 全數不變。安裝 8/8 目標 SHA 相符。完整摘要與釘選見 `163/closeout-evidence-26.json`。

## 實際命令與退出碼

以下 `PY` 是專案 `.venv315/Scripts/python.exe`，`W` 是 `scratchpad/mohan-v5-hanfu-unified-front-163`；所有執行 cwd 為本專案。

- `PY W/run_adopted_pair_matting.py`：0，wrapper 記錄真正 worker 子行程退出碼。
- `PY W/prepare_native_masks_26.py`：0，離線 native alpha 輔助。
- SAM 使用離線 worker 的 Python：`D:/FlamebladeStudio/CodexProjects/.tooling/birefnet-hr/Scripts/python.exe D:/FlamebladeStudio/CodexProjects/.tooling/sam-native/run_point_prompt.py --prompt W/profile-main-hand-prompt-26.json --output-dir W/profile-main-hand-sam-26`：0。checkpoint SHA `ec2df62732614e57411cdcf32a23ffdf28910380d03139ee0f4fcbe91eb8c912`。
- `PY W/review_native_hand_masks_26.py`：0。
- `PY W/extract_adopted_pair_26.py extracted-pair-26k`：0。
- `PY W/stage_adopted_pair_26.py isolated-pair-26k --extracted extracted-pair-26k`：0。
- `PY W/audit_pair_stage_26.py isolated-pair-26k`：0。
- `PY W/install_adopted_pair_26.py prepare`：0；`... install`：0。使用既有 `tools/art_pipeline/approved_asset_install.py` 預檢、回復備份、逐檔原子置換及最後 receipt。
- `PY W/reload_pair_26.py isolated-pair-26k formal-reload-26`：0。
- `PY W/audit_pair_stage_26.py formal-reload-26`：0。
- Sol 最終回歸：`PY -m pytest tests/test_source_bound_garment_visibility.py tests/test_active_outfit_overlay.py tests/test_outfit_hand_occlusion.py tests/test_full_body_complete_expression.py tests/test_layered_full_body.py -q --basetemp D:/FlamebladeStudio/CodexProjects/.qa/source-hands-full-26`：0，95 passed in 68.87s。
- `PY -m pytest tests/test_layered_facade_cycles.py -q --basetemp D:/FlamebladeStudio/CodexProjects/.qa/v5-pair-architecture-26`：0，24 passed in 11.71s。
- `PY -m ruff check .`、`PY -m ruff check W`：皆 0。顯式 W 稽核有涵蓋被全庫 Ruff 預設忽略的 scratch 腳本。
- 兩份修改的四語文件逐一 `tools.check_four_language_docs.audit_document`：錯誤清單皆空、0。
- 較早版本曾有 102 pytest passed，之後因新增衣裝限定手支援，以上最終 95 才對應最終 runtime 程式；不以舊結果冒充新版本驗收。

## 失敗與修正保留

- stage 26a 的官方 ID 由公開 user pack importer 載入遭拒，改為隔離 process 的 bundled official root，沒有放寬 importer。
- stage 26b 的 public clear API 不允許 hairstyle／garment 清空。隔離 profile 明寫 resolver 已支援的 builtin/none/none；未改使用者衣櫃，未宣稱公開 UI 可選。
- stage 26c 真實渲染有 60 failures：+090 領口碰到 82 個原生保護像素；背面重複 body overlay 使頭部 alpha 改變。保留原失敗 JSON；以衣料對齊及先還原原生 body 再套 visibility 的程式修正。
- 26d／26g／26h／26i／26j 雖技術可過，手部／袖口仍經目視逐步修正；26j 遠側手邊白圈來自外緣 seam fill。26k 只補封閉衣層缺口，排除連通背景的區域，已看圖確認白圈消失。
- Ruff 曾指出長函式、magic values 等，拆分小函式並明名常數，未加 ignore。最終抽取腳本相較 26k 執行時只將 flood label 2 命名為常數；影像演算法不變。
- 結尾 aggregate probe 首次用「相對各素材資料夾」路徑造成 digest 不同、exit 1；改回開輪的「相對專案根目錄」算法，四組 SHA 均吻合、exit 0；另逐檔對 staging 副本也零差，沒有素材漂移。
- 部分猜測 receipt 路徑或檔名不存在；採用去背的實際檔名是 `process-receipt.json`。CIM 行程盤點曾權限不足，不影響已完成子行程及實際輸出驗證。

## 尚未完成與下一步

1. 其餘 22 個全身角度尚未完成本輪正面款式統一驗收；不是全部需要重製。先保留相符正面角度，再逐角度補既有缺口，新外觀才交 owner 決定。
2. 全身原生髮型選單與舊 ensemble 相容尚未處理；本次正式 renderer 驗證用隔離原生設定，不是預設 App 全面通過。±90° 舊散髮／髮飾碰撞與 −090° 衣裝仍屬開放範圍。
3. 原生去背髮際灰邊仍存在。+090 原生 hair_back／hair_left／hair_right 包含身體皮膚像素（可到 y1076），屬既有分区語意缺陷。衣服覆蓋之後不代表分區已修好；後續若重分層，須保持 bare 全狀態重建一致並檢查動態。
4. 七半身原生髮飾真正獨立切換及選單標籤仍開放；自創新散髮不在結案範圍。
5. 未更動原生 source、共用手／body overlay、使用者衣櫃；未 commit、PR、merge、軟體 release 或 tag。

## 助理分工與交接

複雜 runtime 綁定由既有 Sol 子工作處理，主代理審查四個程式／測試檔與實際渲染後整合；子工作已完成、停止寫入。非繪圖翻譯草稿先用本機 Qwen3.8-27B，248 tokens／13.5 秒（18.4 tok/s），主代理修正英日文不自然的「rendering isolation」語句後採用；沒有將專案資料送往 DeepSeek。本轮沒有重生已採用衣裝。

更新 CURRENT_STATUS、TASKS 與 extra 清單後，以原 session checkpoint、協作 release，最後唯讀 verify；revision／checkpoint SHA 以 CLI 帳本及最後回覆為準。verify 只校验已列出的檔案，不是美術驗收或全磁碟備份。
