# PoseAtlas v4 候選素材來源與授權紀錄／PoseAtlas v4 候选素材来源与授权记录／PoseAtlas v4 Candidate Provenance and Authorization Record／PoseAtlas v4 候補素材の出典と許諾記録

## 繁體中文

本紀錄已建立完成，對應 `PROVENANCE.json`。它描述候選素材的來源鏈，並記錄權利人已於 2026-08-16 確認的專案使用與公開再散布授權。

候選 PNG 是依照使用者在本次工作中提供的正面、側面、背面、服裝與配件參考圖產生的 24 張內部素材。候選素材並非從外部網站下載，也不是正式發布資產。權利人已確認炎劍文化工作室擁有參考圖的專案使用與公開再散布權，並授權以專案授權條款發布其衍生的 PoseAtlas v4 素材；此確認不解除任何技術或視覺稽核閘門。

手部證據位於 `candidate-evidence/hand-detection-report.json`。它記錄真實 OpenCV Zoo PalmDet 與 HandPose 模型輸出的 19 組觀測、共 399 個 21 點座標。這是候選證據，不是完整正式 sidecar；部分視角沒有兩隻可可靠偵測的手，因此正式 PoseAtlas 仍維持阻擋。

模型本身的 OpenCV Zoo 出處、固定版本、SHA-256、Apache-2.0 授權與實際檔案要求，唯一機器來源是 `docs/HAND-MODEL-PROVENANCE.json`。候選圖的來源與授權紀錄則以本檔及 `PROVENANCE.json` 為準。

正式發布前仍必須完成：逐視角人物與服裝配件審查、完整雙手 21 點證據、body sidecar、檔案雜湊與三平台乾淨載入證據。未完成前不得複製到 `assets/pose-atlas/v4/`。

## 简体中文

本记录已经建立完成，对应 `PROVENANCE.json`。它描述候选素材的来源链，并记录权利人已于 2026-08-16 确认的项目使用与公开再分发授权。

候选 PNG 是依据用户在本次工作中提供的正面、侧面、背面、服装与配件参考图生成的 24 张内部素材。候选素材不是从外部网站下载，也不是正式发布资产。权利人已确认炎剑文化工作室拥有参考图的项目使用与公开再分发权，并授权按照项目许可条款发布其衍生的 PoseAtlas v4 素材；此确认不解除任何技术或视觉审计闸门。

手部证据位于 `candidate-evidence/hand-detection-report.json`。它记录真实 OpenCV Zoo PalmDet 与 HandPose 模型输出的 19 组观测，共 399 个 21 点坐标。这是候选证据，不是完整正式 sidecar；部分视角没有两只可以可靠检测的手，因此正式 PoseAtlas 仍然阻挡。

模型本身的 OpenCV Zoo 来源、固定版本、SHA-256、Apache-2.0 许可与实际文件要求，唯一机器来源是 `docs/HAND-MODEL-PROVENANCE.json`。候选图的来源与授权记录则以本文件及 `PROVENANCE.json` 为准。

正式发布前仍须完成：逐视角人物与服装配件审查、完整双手 21 点证据、body sidecar、文件哈希与三个平台的干净加载证据。完成前不得复制到 `assets/pose-atlas/v4/`。

## English

This record is complete and corresponds to `PROVENANCE.json`. It records the candidate asset chain and the project-use and public-redistribution authorization confirmed by the rights holder on 2026-08-16.

The candidate PNG set contains twenty-four internal assets generated from the front, side, rear, clothing, and accessory reference images supplied by the user during this task. The candidates were not downloaded from an external website and are not release assets. The rights holder confirmed that Flameblade Studio has the right to use the references and publicly redistribute the derived PoseAtlas v4 assets under the project license. This authorization does not waive any technical or visual audit gate.

The hand evidence is stored in `candidate-evidence/hand-detection-report.json`. It records nineteen real OpenCV Zoo PalmDet and HandPose observations with 399 total 21-point landmark coordinates. This is candidate evidence, not a complete formal sidecar set; some views do not expose two hands reliably enough for formal evidence, so the PoseAtlas release gate remains blocked.

The sole machine-readable source for the hand model origins, immutable revisions, SHA-256 values, Apache-2.0 license, and actual-file requirements is `docs/HAND-MODEL-PROVENANCE.json`. The candidate image provenance and authorization record are governed by this document and `PROVENANCE.json`.

Before release, the project still needs per-view identity and clothing or accessory review, complete two-hand 21-point evidence, body sidecars, file hashes, and clean three-platform loading evidence. The candidates must not be copied into `assets/pose-atlas/v4/` before those gates pass.

## 日本語

この記録は作成済みで、`PROVENANCE.json` に対応します。候補素材の出典経路と、2026-08-16 に権利者が確認したプロジェクト利用および公開再配布の許諾を記録します。

候補 PNG は、本タスクでユーザーが提供した正面、側面、背面、衣装、装飾品の参考画像を基に生成した内部素材 24 枚です。外部サイトからダウンロードした素材ではなく、公開用素材でもありません。権利者は、炎剣文化工作室が参考画像をプロジェクトで利用し、その派生 PoseAtlas v4 素材をプロジェクトライセンスで公開再配布する権利を持つことを確認しました。この許諾は技術的または視覚的な監査ゲートを免除しません。

手の証拠は `candidate-evidence/hand-detection-report.json` に保存します。実際の OpenCV Zoo PalmDet と HandPose の出力として、19 組の観測と合計 399 個の 21 点ランドマーク座標を記録しています。これは候補証拠であり、正式な sidecar 一式ではありません。二つの手を信頼できる形で確認できない視角があるため、正式 PoseAtlas の公開ゲートは阻害されたままです。

手モデルの出典、固定リビジョン、SHA-256、Apache-2.0 ライセンス、実ファイル要件の機械可読な唯一の情報源は `docs/HAND-MODEL-PROVENANCE.json` です。候補画像の出典と許諾記録は本書と `PROVENANCE.json` を正本とします。

公開前に、各視角の人物と衣装・装飾品の確認、完全な両手 21 点証拠、body sidecar、ファイルハッシュ、三プラットフォームのクリーンな読み込み証拠を完了する必要があります。完了前に `assets/pose-atlas/v4/` へコピーしてはいけません。
