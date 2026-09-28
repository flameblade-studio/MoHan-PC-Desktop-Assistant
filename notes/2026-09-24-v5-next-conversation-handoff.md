# 可直接貼到新對話：墨寒 V5 二代素體接續指令

請接手墨寒 V5 二代素體專案，從現有已採用來源與隔離成果繼續，完成眼態、已定裝華麗妝、全身接合及正式接入。以下是接續工作的授權；上一對話因我要求暫停而停止素材工作，後來只為交接保存狀態。請使用臺灣繁體中文，直接推進已授權的可逆步驟，只有新外觀偏差或需要我判斷的重大阻礙才詢問。

## 1. 路徑、派工與開輪

- 工作區：`D:\FlamebladeStudio\CodexProjects`
- 專案 P：`D:\FlamebladeStudio\CodexProjects\2026-09-02\mohan-front-layer-repair`
- 協作 H：`D:\FlamebladeStudio\CodexProjects\shared\agent-handoff\mohan`
- 當輪來源 S：`P\scratchpad\mohan-v5-visible-geometry-scale-166\session48`
- 主控 `gpt-6-sol / max`，子代理 `gpt-6-luna / max`，依獨立工作需要派 0–3 名，最多同時 3 名，不含主控，禁止遞迴派工。主控負責規劃、原生繪圖、審查與整合。每包指定唯一寫入者及完成條件。
- `astra-flash-orchestrator`、Flash 角色及 Router 保留但暫停，不因主控模型變更而恢復 Flash；不可靜默回退。
- 本機 `C:\Users\USERNAME\.codex\config.toml` 已設上述預設；已開啟任務的主模型不能只憑預設宣稱已切換。變更前備份為同目錄 `config.toml.routing-20260924-sol-max-before.bak` 與 `AGENTS.md.routing-20260924-sol-max-before.bak`。不讀出或散布金鑰。
- 原 GPT-5.6 子代理均已停止。新對話請建立符合新規則的子代理，不直接續用舊模型代理。

開工依序讀取：

1. 工作區 `CODEX_PROJECT_HANDOFF.md`、`AGENTS.md`、`_tools\ASSISTANT_ROUTING.md`。
2. `shared\agent-handoff\START_HERE.md` 與 `PROTOCOL.md`。
3. 專案 `AGENTS.md`、`ARCHITECTURE.md`、相關模組與測試。
4. H 的 `CURRENT_STATUS.md`、`TASKS.json`、`OWNER_DECISIONS.md`、最新 ledger。
5. 專案 `notes\2026-09-24-session48-source-adoption-routing-handoff.md`。
6. S 的三份 owner approval；按本輪工作再選讀下列收據，避免重做已完成項目。

上一 session 為 `codex-20260924-v5-approved-glamour-native-retarget-45`。第一次暫停時 checkpoint 中止，exit 1，當時 revision 196；後來因交接請求重新封存。請讀最新 `H\ledger\CURRENT.json` 及執行 status，不能直接沿用 revision 196 或最早 revision 142。

使用 `C:\Program Files\nodejs\node.exe` 與 `D:\FlamebladeStudio\CodexProjects\shared\agent-handoff\tools\handoff.mjs`。`--project-dir` 必須指向 H。若 lock=null，依 `status → verify → claim`，每步 exit 0 後再繼續，claim 使用自己的新 session ID。若舊鎖仍在，不可刪鎖、冒用舊 session 或強制 claim；先唯讀依協定處理殘留交接。verify 只證明校驗範圍完整性，不是美術驗收或全盤備份。

已重新核對：branch `integration/worktree-consolidation-20260916`；HEAD `3fe2b7dd5a03bebf92b90ba6be1b0e5e6c79a009`；`git status --porcelain=v1` 為 225 項。保持全部既有變更，不 reset、不 checkout 還原、不清暫存或刪成果。沒有 commit、PR、merge、tag 或發布授權。

## 2. 素材與外觀權威

V5 原生權威是 `C:\Users\USERNAME\Desktop\墨寒桌面語音互動虛擬女友2026.07.28開始開發\墨寒V5素顏` 的來源，不得用上一代臉或藍白漢服整圖充當 V5 素體。衣裝、妝、髮飾保持可拆且於 runtime 合成；生成候選只抽取被批准的部位。

七個半身姿勢與 V7 嘴型已採用及正式接入，保留既有成果：front-crossed、left-neutral、cheek-rest、front-eureka、front-mock-scold、front-mock-hit、front-exasperated。原生來源及 RGBA 在 `P\scratchpad\mohan-v2-v5-seven-pose-matting-146`。最早五姿勢漢服採用／未去背描述已過期，不要照舊清單重做。

全身 24 角衣裝、共用等比 DISPLAY-PLACEMENT 與若干局部修復已有正式安裝歷史。尺寸已採用，不再重做整套尺寸。新四角頭部與眼唇是本輪未完成接合。現行 `assets\pose-atlas\v5-base\SOURCE-PROVENANCE.json` 已記錄 22 個 external_exact 與 2 個 approved_alpha_cleanup_derivation，`external_raw_source_gaps=[]`；最早三個外部原圖缺口不再是待辦。新的四角來源接入時仍須另建立衍生血緣，不能冒稱外部原圖精確相同。

淡妝、經典妝、華麗妝之前已定裝。不要重新設計、改成另一套粉底或只做淡淡的眼唇就稱華麗妝。原華麗妝權威是 `P\scratchpad\mohan-v2-makeup-global-142\candidates\yaw+000-pitch+00-glamorous-neutral-rest.png`，SHA `e647c1d8a1e01fd43dcdf1e66e04c54985356deebeb7d778dab0709a8282f7ae`。本輪 13 角批准的來源是目前抽取依據。

Session47 的 13 角一致性候選已被退回：±60／±75 身分不符及眼唇不自然。其 pack SHA `e5ae95aa3316fa30a63af65117d0cce72ab426bd36034e02e1bdc38aed9ca05f` 不可安裝。技術測試歷史不能推翻擁有者退件。

## 3. 最新三批批准

### 四角身分：已採用

批准 `S\owner-face-approval.json`，原話「四角臉型可採用」。來源均為 1254×1254 RGB：

- −75：`yaw-075-bare-candidate-01.png`；SHA `d06116f72ba20724801586bf68ef6139fe40f0fd9085c2356c534e1933250a4c`。
- −60：`yaw-060-bare-candidate-01.png`；SHA `88d7bc5edf52fac173fe5cc01f965b5a81b01d1975add56b1fc792f044456ab2`。
- +60：`yaw+060-bare-candidate-02.png`；SHA `2f90543dea0f8e11ea9c711d8ee0a42b18cdcfac768da80056a168a93053c262`。
- +75：`yaw+075-bare-candidate-02.png`；SHA `1abafaf88f999de924eb9da021fa7c3e97a48adfad6c4713f34c93a4293d55e1`。

正角的 candidate01 過於正面，已排除；不要選錯版本。

### 13 角華麗妝眼唇來源：已採用

批准 `S\owner-glamour-source-approval.json`，SHA `0a0af0449a2d6c513f1dffb6fb36c3bc0907806bc795ffbdf7badf7fa75ed629`，原話「13 角眼唇來源可採用」。涵蓋 −90 到 +90 每 15° 共 13 角。

- 正面及 ±90 使用 `yaw<角度>-glamorous-candidate-02.png` 的灰背景版本。
- 其他十角使用 `yaw<角度>-glamorous-candidate-01.png`。
- 全部精確來源路徑、SHA、尺寸在批准 JSON。不要用正面／±90 被排除的透明背景 candidate01。
- 批准僅限可拆眼唇抽取，不批准把生成器整張臉替換原生臉，也不代表全身接合或正式安裝完成。

### 四角半閉／閉眼 8 張：已採用

`S\root-new-eye-sources-01\owner-approval.json`，SHA `6f13d9f333617ace81cff04a2f81dc8cd4f954e0fe222977527123e870ecc5cb`，原話「8 張眼態來源整組採用」。

檔名 `yaw-075.half.source-01.png`、`yaw-075.closed.source-01.png`，以及 −060、+060、+075 的同名兩態，均 1254×1254 RGB。

來源 manifest `candidate-set.json` SHA `ce8a503463efe3fb98af416d489370aa0947c4094849a1ec719c70df72abe55c` 保留生成時未批准欄位；目前批准以後寫入的 owner-approval 為準。只抽眼部，保留已採用臉型、身體與手。不要重生這 8 張。

## 4. 已有可重用的隔離成果

### 新四角全身接合

`S\root-four-face-03\`：來源頭部同一等比 426/1254，top=47；四角 left 分別 −75=287、−60=298、+60=295、+75=274。純頸部短帶接合，y=340 以下與原生身體相同。`receipt.json` 及 4 個 `.four-face-candidate.rgba.png` 可用作隔離權威。較早 worker 大小失真的臉部接合不要回用。

### 13 角可拆眼唇

- 六角：`S\root-six-makeup-01\mapped-01\`，±60、±75、±90。
- 中央七角：`S\seven-makeup-extraction-luna\revision03\<view>\`。
- 全畫布 1024×1536 RGBA，eyes/lips 分離。原始眼孔保護以 rest-aperture 釘選。
- 正確 468 點來自 `root-six-makeup-01\provider-geometry.json`，模型輸入 `/255`；同目錄舊 `geometry.json` 使用錯誤正規化，不可回用。
- 分別有來源到母版的 SIFT 註冊及 canvas 等比映射收據；主控已檢視 rest 結果，未完成三眼態／說話驗收。

### 真正的 renderer 輸出

`S\root-rest-runtime-01\all13-run-04\`：13 角 × none/glamorous × bare/hanfu 共 52 張 rest，由 LayeredFullBodyRenderer 和 ActiveOutfitOverlay 在隔離環境實際輸出。妝包 SHA `9a021131b2778f9d14e6c2cf0cef8143faa797ffc939aa784bbd351aba749ea9`。建包契約與 render 命令 exit 0；眼唇對 y=400 以下及 alpha 改動 0。

這是 rest-only 預覽，`formal_installation_allowed=false`，foundation／cheeks 透明僅為隔離眼唇比對，尚有領口／鞋口缺陷。不能直接安裝該 pack 或稱所有妝容完成。

`four-repair-05\`：4 角 16 張，root07 分層及 visibility 後頭頸不透明像素損失 0；其中 +75 過寬保留區露出舊內衣肩帶，已繼續局部修正。

`hanfu-binding-root08\` 與 `plus075-repair-06\`：+75 衣裝中與主布料分離的白條位於原 canvas [565,300,23,6]，只有 103 像素，已隔離移除；元件外像素改動 0。配合領口 visibility 限制，主控已看到白條和舊肩帶消失。staging 漢服 pack SHA `654b8e505b62945f86a4a4ca8de711020620d57c20c2671a85319a003bcb5ff3`；該角 4 張實際 render exit 0。尚未安裝、未獲最終全身接合採用。

分層重組後，4 角 bare rest 相對 `four-run-03` 仍分別有 −75=140、−60=101、+60=138、+75=5 個像素差異。尚未定位是否僅邊界，不能寫成零差；正式接入前要確認。

## 5. 優先未完成事項

### A. 接續眼態抽取

先由主控目視：
`S\four-eye-extraction-luna\revision03\yaw-060-pitch+00.revision03.same-scale-raw-rest-final.png`

此版只完成 −60° half/closed，worker 已交付，但主控尚未目視接受。receipt SHA `41ffc11c1c820e6684cdd32e48cb3a69ca3696bd74c44fbc45032c54db555424`；handoff SHA `55d46e78675c3b74c3f9bb3d67528e419016596123819b456642122327194651`。

前兩版被主控退回，因閉眼上方還有舊張眼睫毛黑弧。修法是幾何核心完整覆蓋眼孔與原睫毛，alpha 255，僅外緣羽化，眉毛保持原生；不能用 RGB 差值決定 opacity，否則會半透明混入舊眼線。RGBA 縮放只能做一次正確預乘／反預乘，避免雙重處理產生亮邊。

revision03 目視通過後才擴其他三角。worker 的 outside-eye=0、alpha=0、body-below-y341=0 只是技術指標，不等於外觀已被採用。

### B. 新四角動態接入與妝容

8 張眼部 overlays 綁定到新 authority，沿 `infrastructure\full_body_blink_binding.py` 的 source SHA／兩態 SHA 契約與 `LayeredFullBodyView.blink_frames`。保留其他角度既有動態。

`S\four-face-runtime-binding-luna\runtime-binding-root03-v2` 的 loader 可供參考，但它把 24 角動態欄位清空供 rest 診斷，不能正式安裝。新的 four-blink-runtime-binding-luna 工作在程式落地前停止，不能稱已完成。

華麗妝 half/closed 與說話嘴型仍需對新原生眼唇接合。light/classic 也須重綁新四角，不能留下舊臉座標。維持既有已定裝風格，禁止重設計或以素顏充當華麗妝。

### C. 腳部缺口與領口

−45、−30 漢服鞋口上方腳踝仍透明，看起來像空鞋。`S\feet-binding-luna\diagnostic\` 只有 13 角腳踝總覽及兩張 base/garment/render 定位圖，沒有完成修復。`feet_binding_diagnostics.py` 可重用，應比對既有原生、衣裝／body overlay、replacement/visibility，以及正式與隔離 asset_root 的依賴。沿用已採用來源，不憑空塗膚色。

確認 +75 新頸部輪廓、領口、配件及腳部全身效果；不要把 root07 的零缺像素機械結果當成整體自然外觀。

### D. 最終整合

完成 13 角實際妝容與衣裝切換、相關三眼態和說話狀態，以及 7 半身姿勢相關回歸。先修明顯破圖再提供整組原生／上妝、裸身／漢服及眼口頸手腳 close-up。

新的整體外觀由擁有者審查；不重問已採用來源。符合外觀後，使用 `tools\art_pipeline\approved_asset_install.py` 的驗證計畫、原子安裝與 receipt，更新必要 source SHA、安全區、manifest 與血緣，再新行程載入正式 renderer 核對。直到真正完成以前，維持「已採用來源／已抽取／已隔離實際渲染／未正式安裝」的精確狀態。

## 6. 必須知道的硬連結事故

舊子代理用硬連結建立 staging，接著 Image.save 原地寫入，意外改到正式 ±75 visibility。主控發現後停止代理，從逐位元相符歷史備份原子恢復兩檔並斷開正式硬連結。恢復腳本 `S\root-hardlink-recovery-01\restore_exact_masks.ps1` exit 0，事故 bytes 有保留。

恢復後應為：
- `assets\pose-atlas\v5-garment-visibility\yaw-075-pitch+00.png`：`0d221b65b22b4d5c3faec3f9b3544a47107fcb0995978ad58513e720d01f1789`。
- `assets\pose-atlas\v5-garment-visibility\yaw+075-pitch+00.png`：`b14905cc0906815a558bcf0db04b0640a79bdc5b95a8a979333da50b7a71fdb8`。

60 個正式 visibility manifest 來源／遮罩／hand-support SHA 核對失敗 0，之後再次查兩檔仍與原值相符。不能宣稱整輪「從未寫過正式檔」，應記為事故已精確恢復、沒有新採用素材正式安裝。

`four-face-runtime-binding-luna\hanfu-visibility-binding-root03-v1` 到 v4 均失效，不可接入。後續所有可寫 staging 使用獨立 copy2，禁止硬連結；不得繞過 face、hair、hand、alpha、安全區驗證器。

## 7. 技術入口與已知環境

Python 使用 `P\.venv315\Scripts\python.exe`；系統 python 缺 PIL，專案含 Python 3.15 語法。

主要支援腳本：
- `S\root-rest-runtime-01\build_rest_pack.py`
- `S\root-rest-runtime-01\preview_regions.py`
- `S\root-rest-runtime-01\stage_hanfu_binding.py`
- `S\root-rest-runtime-01\repair_plus075_binding.py`
- `S\root-rest-runtime-01\render_rest.py`

`stage_hanfu_binding.py` 的舊 DEST=root07 已存在，再跑須選新輸出；不要覆寫歷史。`render_rest.py` 支援 --pack-dir、--atlas-parent、--overlay-asset-root、--hanfu-pack、--output-dir、--views；使用新的 output-dir。

正式 `LayeredFullBodyRenderer` 必須帶已採用 DISPLAY-PLACEMENT；省略就不是已採用整體尺寸。ActiveOutfitOverlay 的 asset_root 中新 rig 相對路徑必須實際存在；garment visibility 要同步 native SHA、pack member SHA 和 mask SHA。衣裝失敗會 fail-closed 退回素體，故 PNG 寫出／exit 0 不代表已著衣，要比對身體衣裝像素。

實際檢查：13 角 rest 52 張、後續四角 16 張及 +75 4 張的命令 exit 0；最後全庫 `python -m ruff check .` exit 0；`python tools/check_four_language_docs.py` exit 0。本輪不宣稱整套 pytest 或全動態驗收已完成。新變更只跑相符必要檢查，不為綠燈反覆跑無關測試。

正式守衛 SHA：
- makeup pack：`bdc28c8c33ccf93d126cfe140cf8b28a24a7865ae8bacdcbcb7a813cd6a605b3`。
- Hanfu pack：`a826955cfdb183c47feac1819f64feb1f75c74c7afbf018bbe419fb9909a6d92`。
- DISPLAY-PLACEMENT：`b4b5b5785ec8507f5c50dc415558b14922fe7a5f0904f8ef73f16bf73fc1026f`。

Windows rg 啟動曾遭拒，必要時用 Get-ChildItem／Select-String。不要反覆查 denied 的 CIM。上一輪內嵌瀏覽器開本機檔案被安全限制阻擋，未繞路；可用 view_image 檢查本機圖，將 HTML 絕對路徑交給擁有者自行開啟。美術圖不可只看縮小總覽。

新對話完成一段工作後，收齊／停止寫入者，更新狀態與 extra 清單，checkpoint、release，再唯讀 verify；報告實際退出碼、SHA、限制及尚未核准的外觀。不要動軟體發行或聲稱二代素體已結案。
