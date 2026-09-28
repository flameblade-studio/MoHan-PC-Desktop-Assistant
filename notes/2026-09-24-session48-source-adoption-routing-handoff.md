# Session 48：已採用來源、隔離接合與派工更新

2026-09-24。專案分支 `integration/worktree-consolidation-20260916`，HEAD `3fe2b7dd5a03bebf92b90ba6be1b0e5e6c79a009`。既有未提交變更保留。沒有 commit、PR、merge、tag 或發布。

## 最新派工

擁有者指定主控 `gpt-6-astra / max`、子代理 `gpt-6-luna / max`，依獨立工作需要使用 0–3 名，不得遞迴派工。工作區與專案 AGENTS、ASSISTANT_ROUTING、CODEX_PROJECT_HANDOFF、docs/ai-workflow、協作 START_HERE 與 TASKS 已同步。本機 config.toml 和個人 AGENTS 已更新，原檔在同目錄保存 `routing-20260924-212333.bak`。TOML 已解析核對。既有 GPT-5.6 子代理停止，保留輸出；預設更新不代表本任務主模型已熱切換。Astra／Flash 技能仍暫停。

## 三項來源批准

證據根目錄為 `scratchpad/mohan-v5-visible-geometry-scale-166/session48/`。

- 四角臉型已採用：`owner-face-approval.json`；±60、±75。
- 13 角眼唇來源已採用：`owner-glamour-source-approval.json`，SHA `0a0af0449a2d6c513f1dffb6fb36c3bc0907806bc795ffbdf7badf7fa75ed629`。
- 四角半閉／閉眼 8 張已採用：`root-new-eye-sources-01/owner-approval.json`，SHA `6f13d9f333617ace81cff04a2f81dc8cd4f954e0fe222977527123e870ecc5cb`。來源 manifest SHA `ce8a503463efe3fb98af416d489370aa0947c4094849a1ec719c70df72abe55c` 保留生成當時未批准欄位；後續 owner-approval 為目前批准權威。

批准範圍是來源及後續抽取，尚未完成全身動態接合、正式安裝或擁有者對最終 runtime 的驗收。Session 47 已退件，不能再安裝。

## 已完成的隔離工作

`root-four-face-03/` 為新四角頭部與原生身體接合；每頭採單一等比，y=340 以下與原生身體相同。`root-six-makeup-01/mapped-01/` 與 `seven-makeup-extraction-luna/revision03/` 共 13 角已抽取眼唇；使用採用來源色彩，沒有重設計華麗妝。

`root-rest-runtime-01/all13-run-04/` 的建包與實際 renderer 命令均退出 0，13 角 × 素顏／華麗妝 × 裸身／漢服共 52 張 rest。妝層在 y=400 以下改動 0、alpha 改動 0。這組仍有領口／腳部問題，並非外觀驗收通過。

`stage_hanfu_binding.py` 將新頭分為臉、髮與頸部語義層，使用獨立 copy2，避免把整個脖頸當成禁止衣裝覆蓋的臉部。`four-repair-05/` 4 角 16 張重渲退出 0，root07 頭頸不透明像素損失 0。相對先前裸身輸出仍有 140／101／138／5 個像素差異，需確認分層邊界原因後才能正式接入。

`repair_plus075_binding.py` 退出 0，root08 僅清理 +75 衣裝獨立白色元件 103 像素，元件範圍外改動 0；另限制領口 visibility，排除原內衣肩帶。pack SHA `654b8e505b62945f86a4a4ca8de711020620d57c20c2671a85319a003bcb5ff3`。`plus075-repair-06/` 實際重渲 4 張退出 0，主控看到白條及露出的舊肩帶已消除；最終接合尚待整組外觀確認。

主要命令（在專案根目錄使用 `.venv315/Scripts/python.exe`）：`root-rest-runtime-01/build_rest_pack.py`、`stage_hanfu_binding.py`、`render_rest.py`（--pack-dir all13-run-04 --atlas-parent four-face-runtime-binding-luna/runtime-binding-root03-v2 --overlay-asset-root 對應 staging/asset-root；+75 使用 --hanfu-pack root08/*.staging --views yaw+075-pitch+00）。完整參數及根目錄記於各 runtime-receipt.json。

## 已恢復的硬連結事故

舊子代理在硬連結 staging 直接寫入，意外改到正式 ±75 visibility。主控發現後停止該代理，使用歷史逐位元相符來源原子替換並斷開正式硬連結；兩檔已恢復，沒有採用事故候選。

- −75 原 SHA：`0d221b65b22b4d5c3faec3f9b3544a47107fcb0995978ad58513e720d01f1789`。
- +75 原 SHA：`b14905cc0906815a558bcf0db04b0640a79bdc5b95a8a979333da50b7a71fdb8`。
- `root-hardlink-recovery-01/restore_exact_masks.ps1` 退出 0，事故 bytes 保留 `.incident-copy`。恢復後正式 visibility manifest 60 項 SHA 核對失敗 0。
- `four-face-runtime-binding-luna` 的 visibility v1–v4 輸出均不得接入；新的 root06–08 使用 copy2。

正式妝包仍為 `bdc28c8c33ccf93d126cfe140cf8b28a24a7865ae8bacdcbcb7a813cd6a605b3`，正式漢服仍為 `a826955cfdb183c47feac1819f64feb1f75c74c7afbf018bbe419fb9909a6d92`；本批沒有已採用新資產正式安裝。

## 精確接續點

1. 主控目視 `four-eye-extraction-luna/revision03/yaw-060-pitch+00.revision03.same-scale-raw-rest-final.png`。前兩版仍有舊睫毛黑弧，已退回；revision03 只完成 −60，尚未主控驗收。通過後才擴其餘三角。8 張來源已採用，不須重生。
2. `four-blink-runtime-binding-luna` 工作在程式落地前因派工規則更新中止。建立 source-bound 8 blink overlays 的隔離 runtime binding，保持 face/alpha/body不變；不要以 rest-only manifest 禁用舊角度動態後直接安裝。
3. −45、−30 的鞋口腳踝仍透明。`feet-binding-luna/diagnostic/` 只有定位圖，修復未完成；沿已採用原生來源與既有腳部修復追查，不塗補虛構皮膚。
4. 完成新四角三眼態與 13 角華麗妝動態對齊，確認眼唇及嘴角乾淨、頸部自然、鞋口完整，再進行整組實際渲染及擁有者外觀審查。light/classic 對新四角與說話表情也仍須 source-bound 接續，不能直接宣告二代素體結案。

協作 checkpoint／release／readonly verify 以共享帳本最新實測為準。
