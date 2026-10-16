# PoseAtlas v4 候選素材說明／PoseAtlas v4 候选素材说明／PoseAtlas v4 Candidate Assets／PoseAtlas v4 候補素材

## 繁體中文

這個目錄保存 v4.0.0 PoseAtlas 的內部候選圖，正式發布仍須完成下列門檻。候選圖涵蓋 `yaw-180`、`yaw-165`、`yaw-150`、`yaw-135`、`yaw-120`、`yaw-105`、`yaw-090`、`yaw-075`、`yaw-060`、`yaw-045`、`yaw-030`、`yaw-015`、`yaw+000`、`yaw+015`、`yaw+030`、`yaw+045`、`yaw+060`、`yaw+075`、`yaw+090`、`yaw+105`、`yaw+120`、`yaw+135`、`yaw+150`、`yaw+165`，全部使用 `pitch+00`。

這些 PNG 是依照使用者提供的參考圖產生的內部候選。產生來源、素材授權與再散布權仍須逐項確認，完成後才能列為正式發布資產。

目前已完成的離線檔案檢查只有：24 張 PNG 均為 1024×1536、RGBA、具有有效透明邊界，且主體與畫布邊緣保持間距。另已建立 `candidate-evidence/hand-detection-report.json`，記錄 19 組真實模型觀測、399 個 21 點座標；完整正式 hands sidecar 仍待補齊。來源與授權紀錄位於 `PROVENANCE.md` 與 `PROVENANCE.json`。來源權利、人物身分一致性、服裝與配件轉面一致性、身體 landmarks 及正式稽核仍各自需要完成證據。

候選圖在來源與再散布權、人物與服裝逐視角審查、landmarks、hands sidecar、雜湊、載入與正式 `release-audits.json` 全部完成後，才能複製到 `assets/pose-atlas/v4/` 並解除 v4.0.0 發布阻擋。

## 简体中文

此目录保存 v4.0.0 PoseAtlas 的内部候选图，正式发布仍须完成下列门槛。候选图覆盖 `yaw-180`、`yaw-165`、`yaw-150`、`yaw-135`、`yaw-120`、`yaw-105`、`yaw-090`、`yaw-075`、`yaw-060`、`yaw-045`、`yaw-030`、`yaw-015`、`yaw+000`、`yaw+015`、`yaw+030`、`yaw+045`、`yaw+060`、`yaw+075`、`yaw+090`、`yaw+105`、`yaw+120`、`yaw+135`、`yaw+150`、`yaw+165`，全部使用 `pitch+00`。

这些 PNG 是依据用户提供的参考图生成的内部候选。生成来源、素材许可与再分发权仍须逐项确认，完成后才能列为正式发布资产。

目前完成的离线文件检查只有：24 张 PNG 均为 1024×1536、RGBA、具有有效透明边界，并且主体与画布边缘保持间距。另已建立 `candidate-evidence/hand-detection-report.json`，记录 19 组真实模型观测、399 个 21 点坐标；完整正式 hands sidecar 仍待补齐。来源与授权记录位于 `PROVENANCE.md` 与 `PROVENANCE.json`。来源权利、人物身份一致性、服装与配件转面一致性、身体 landmarks 及正式审计仍各自需要完成证据。

在来源与再分发权、人物与服装逐视角审查、landmarks、hands sidecar、哈希、加载与正式 `release-audits.json` 全部完成后，才能把候选图复制到 `assets/pose-atlas/v4/` 并解除 v4.0.0 发布阻挡。

## English

This directory contains internal v4.0.0 PoseAtlas candidates. Release status requires the gates below. The candidates cover `yaw-180`, `yaw-165`, `yaw-150`, `yaw-135`, `yaw-120`, `yaw-105`, `yaw-090`, `yaw-075`, `yaw-060`, `yaw-045`, `yaw-030`, `yaw-015`, `yaw+000`, `yaw+015`, `yaw+030`, `yaw+045`, `yaw+060`, `yaw+075`, `yaw+090`, `yaw+105`, `yaw+120`, `yaw+135`, `yaw+150`, and `yaw+165`, all at `pitch+00`.

These PNG files are internal candidates generated from references supplied by the user. Generation provenance, asset licensing, and redistribution rights must be confirmed per asset before they can be treated as release assets.

The completed offline file check covers only these facts: all 24 PNG files are 1024×1536 RGBA images with valid non-empty alpha bounds, and the subject retains clearance from the canvas edge. `candidate-evidence/hand-detection-report.json` now records nineteen real model observations and 399 total 21-point coordinates, with the complete formal hands-sidecar set still pending. The source and authorization record is in `PROVENANCE.md` and `PROVENANCE.json`. Provenance rights, identity continuity, clothing and accessory turn consistency, body landmarks, and formal audit each require their own completion evidence.

Copying candidates into `assets/pose-atlas/v4/` and clearing the v4.0.0 release blocker require that provenance and redistribution rights, per-view character and clothing review, landmarks, hands sidecars, hashes, loading evidence, and genuine `release-audits.json` are complete.

## 日本語

このディレクトリには v4.0.0 PoseAtlas の内部候補画像だけを保存します。公開用素材への移行には以下のゲートの完了が必要です。候補は `yaw-180`、`yaw-165`、`yaw-150`、`yaw-135`、`yaw-120`、`yaw-105`、`yaw-090`、`yaw-075`、`yaw-060`、`yaw-045`、`yaw-030`、`yaw-015`、`yaw+000`、`yaw+015`、`yaw+030`、`yaw+045`、`yaw+060`、`yaw+075`、`yaw+090`、`yaw+105`、`yaw+120`、`yaw+135`、`yaw+150`、`yaw+165` を含み、すべて `pitch+00` です。

これらの PNG は、ユーザーが提供した参考画像を基に生成した内部候補です。生成出典、素材ライセンス、再配布権は各素材ごとに確認する必要があり、完了後に公開用素材として扱います。

完了したオフラインファイル検査は、24 枚すべてが 1024×1536、RGBA、有効な透明境界を持ち、主体と canvas の端に間隔があることだけを確認します。`candidate-evidence/hand-detection-report.json` には実モデルによる 19 組の観測と合計 399 個の 21 点座標を記録しましたが、正式な hands sidecar 一式は準備中です。出典と許諾の記録は `PROVENANCE.md` と `PROVENANCE.json` にあります。出典権利、人物同一性、衣装と装飾品の回転整合性、body landmarks、正式監査には、それぞれ完了証拠が必要です。

出典と再配布権、各視角の人物と衣装の審査、landmarks、hands sidecar、hash、load evidence、真正な `release-audits.json` がすべて揃った後に、候補を `assets/pose-atlas/v4/` にコピーし、v4.0.0 の公開ゲートを開くことができます。
