# PoseAtlas 24/600 正式閘門 QA 總結／PoseAtlas 24/600 正式闸门 QA 总结／PoseAtlas 24/600 Formal Gate QA Summary／PoseAtlas 24/600 正式ゲート QA 総括

## 繁體中文

驗收日期：2026-08-26。所有命令退出碼均為 0；完整原始證據位於
`artifacts/pose-atlas-rebuild/2026-08-26/formal-gate-qa/`（不入庫），
本目錄保存入庫版摘要與關鍵對照圖。

### 正式 24 主視角（assets/pose-atlas/v4-working）

- 檔案閘門 24／24 PASS：RGBA、1024×1536、四角 Alpha=0、alpha bbox 不貼畫布邊界（poseatlas-gate-qa.json）。
- SHA-256：24 視角的 source 與 normalized 雜湊全部與 BUILD-METADATA.json 一致。
- 嚴格綠幕殘留（G>R+24 且 G>B+24、alpha≥128）：全 24 視角合計 ≤1 像素。
- 人工目視 24／24：真墨寒身份一致、平底白鞋完整、髮飾方向連續，無娃娃臉／木偶手／裁切／棋盤格。
- 身份定錨：使用者 2026-08-26 三批展示確認；授權：v4-source/PROVENANCE.json（權利人 2026-08-16 確認）。

### 正式 600 分層（assets/pose-atlas/v4-layered）

- 計數：600 張、24 視角 × 25 層精確覆蓋、零缺零多；600／600 RGBA 1024×1536。
- 發現缺陷：Z-order 重組後層邊界羽化疊合使 Alpha 低於母圖（deficit max 64），於 yaw+000 頸部與唇下形成可見黑色虛線接縫（不可放行）。
- 修復：以 Alpha 差額回補法修復全 24 視角（不重繪、不位移；差額補回該像素 Alpha 最大的語意擁有層；每視角 3 輪迭代；被改動層先備份並記錄修改前 SHA-256）。
- 修復後重驗（layered600-gate-qa-final.json）：deficit 全 24 視角歸零；重組 RGB 與母圖零差；殘餘僅邊緣稍實型微差（最大簇 63 像素，4 倍放大目視不可辨），依 2026-08-26 核定驗收尺度放行；頸部黑線目視消失（neck-roi-before/after-repair-4x.png）。

## 简体中文

验收日期：2026-08-26。所有命令退出码均为 0；完整原始证据位于
`artifacts/pose-atlas-rebuild/2026-08-26/formal-gate-qa/`（不入库），
本目录保存入库版摘要与关键对照图。

### 正式 24 主视角（assets/pose-atlas/v4-working）

- 文件闸门 24／24 PASS：RGBA、1024×1536、四角 Alpha=0、alpha bbox 不贴画布边界（poseatlas-gate-qa.json）。
- SHA-256：24 视角的 source 与 normalized 哈希全部与 BUILD-METADATA.json 一致。
- 严格绿幕残留（G>R+24 且 G>B+24、alpha≥128）：全 24 视角合计 ≤1 像素。
- 人工目视 24／24：真墨寒身份一致、平底白鞋完整、发饰方向连续，无娃娃脸／木偶手／裁切／棋盘格。
- 身份定锚：用户 2026-08-26 三批展示确认；授权：v4-source/PROVENANCE.json（权利人 2026-08-16 确认）。

### 正式 600 分层（assets/pose-atlas/v4-layered）

- 计数：600 张、24 视角 × 25 层精确覆盖、零缺零多；600／600 RGBA 1024×1536。
- 发现缺陷：Z-order 重组后层边界羽化叠合使 Alpha 低于母图（deficit max 64），于 yaw+000 颈部与唇下形成可见黑色虚线接缝（不可放行）。
- 修复：以 Alpha 差额回补法修复全 24 视角（不重绘、不位移；差额补回该像素 Alpha 最大的语义拥有层；每视角 3 轮迭代；被改动层先备份并记录修改前 SHA-256）。
- 修复后重验（layered600-gate-qa-final.json）：deficit 全 24 视角归零；重组 RGB 与母图零差；残余仅边缘稍实型微差（最大簇 63 像素，4 倍放大目视不可辨），依 2026-08-26 核定验收尺度放行；颈部黑线目视消失（neck-roi-before/after-repair-4x.png）。

## English

Acceptance date: 2026-08-26. Every command exited with code 0. The complete
raw evidence lives in `artifacts/pose-atlas-rebuild/2026-08-26/formal-gate-qa/`
(not committed); this directory keeps the committed summary and key comparison images.

### Formal 24 master views (assets/pose-atlas/v4-working)

- File gate 24/24 PASS: RGBA, 1024×1536, all four corner alphas 0, alpha bbox clear of the canvas edge (poseatlas-gate-qa.json).
- SHA-256: source and normalized hashes for all 24 views match BUILD-METADATA.json.
- Strict green-screen residue (G>R+24 and G>B+24, alpha≥128): at most 1 pixel across all 24 views combined.
- Human visual QA 24/24: consistent true-MoHan identity, intact flat white shoes, continuous hair-ornament orientation; no doll face, puppet hands, cropping, or checkerboard artifacts.
- Identity anchor: confirmed by the owner's three batches on 2026-08-26; licensing: v4-source/PROVENANCE.json (rights holder confirmed 2026-08-16).

### Formal 600 layers (assets/pose-atlas/v4-layered)

- Count: exactly 600 files covering 24 views × 25 layers, none missing, none extra; 600/600 RGBA 1024×1536.
- Defect found: after Z-order recomposition, feathered layer boundaries stacked to an alpha below the master view (deficit max 64), producing a visible dashed dark seam at the neck and below the lower lip on yaw+000 (not acceptable).
- Repair: alpha-deficit backfill across all 24 views (no repainting, no displacement; each deficit pixel credited to the layer owning the highest alpha there; 3 iterations per view; every touched layer backed up with its pre-repair SHA-256 recorded).
- Post-repair recheck (layered600-gate-qa-final.json): deficit zero across all 24 views; recomposed RGB identical to the master views; only slightly-firmer-edge surplus remains (largest cluster 63 pixels, indistinguishable at 4× zoom), released under the acceptance standard ratified on 2026-08-26; the neck seam is visually gone (neck-roi-before/after-repair-4x.png).

## 日本語

検収日：2026-08-26。すべてのコマンドの終了コードは 0。完全な生証拠は
`artifacts/pose-atlas-rebuild/2026-08-26/formal-gate-qa/`（コミット対象外）にあり、
本ディレクトリにはコミット版の要約と主要比較画像を保存する。

### 正式 24 主視点（assets/pose-atlas/v4-working）

- ファイルゲート 24／24 合格：RGBA、1024×1536、四隅アルファ 0、alpha bbox はキャンバス端に接しない（poseatlas-gate-qa.json）。
- SHA-256：24 視点の source と normalized のハッシュはすべて BUILD-METADATA.json と一致。
- 厳格グリーンバック残留（G>R+24 かつ G>B+24、alpha≥128）：全 24 視点合計で最大 1 ピクセル。
- 目視 QA 24／24：真の墨寒の同一性、白い平底靴の完全性、髪飾りの向きの連続性を確認。人形顔・操り人形の手・切り欠け・市松模様なし。
- 身元アンカー：オーナーが 2026-08-26 に三批提示で確認。ライセンス：v4-source/PROVENANCE.json（権利者 2026-08-16 確認）。

### 正式 600 レイヤー（assets/pose-atlas/v4-layered）

- 数量：600 枚、24 視点 × 25 層を過不足なく網羅。600／600 RGBA 1024×1536。
- 発見欠陥：Z-order 再合成後、レイヤー境界の羽化重合によりアルファが母画像を下回り（deficit 最大 64）、yaw+000 の首と下唇下に可視の黒破線継ぎ目が発生（不合格）。
- 修復：全 24 視点にアルファ差分補填法を適用（再描画・移動なし。各差分ピクセルをアルファ最大の意味的所有レイヤーへ補填。各視点 3 回反復。変更レイヤーは事前バックアップと変更前 SHA-256 を記録）。
- 修復後再検証（layered600-gate-qa-final.json）：deficit は全 24 視点でゼロ。再合成 RGB は母画像と完全一致。残余はエッジがわずかに固くなる surplus 型のみ（最大クラスタ 63 ピクセル、4 倍拡大でも判別不能）で、2026-08-26 承認の検収基準により合格。首の黒線は目視で消失（neck-roi-before/after-repair-4x.png）。
