# PoseAtlas 24／600 正式閘門 QA 總結（2026-08-26）

執行環境：Windows 11、Git Bash、Python 3.13（qwen2509-standalone conda）＋ Pillow 12.3.0。
所有命令退出碼均為 0；證據檔案均在本目錄與 seam-repair/、final-recheck/ 子目錄。

## 正式 24 主視角（assets/pose-atlas/v4-working）

- 檔案閘門：24／24 PASS——RGBA、1024×1536、四角 Alpha=0、
  alpha bbox 不貼畫布邊界（poseatlas-gate-qa.json）。
- SHA-256：24 視角的 source 與 normalized 雜湊全部與
  v4-working/BUILD-METADATA.json 記錄一致（HASH_MISMATCH=NONE）。
- 綠幕殘留量測：嚴格綠殘（G>R+24 且 G>B+24、alpha≥128）全 24 視角
  合計 ≤1 像素（最高 yaw+090 為 1）。
- 人工目視 QA：24 視角全數逐張檢查——真墨寒身份一致、平底白鞋完整、
  髮飾方向連續、無娃娃臉／木偶手／裁切／棋盤格。
- 身份定錨：使用者 2026-08-26 分三批（18＋16＋11 張）展示並確認
  「真墨寒」，與 v4-source 家族逐張對應（見 true-mohan-source-index/）。
- 授權：v4-source/PROVENANCE.json，權利人 2026-08-16 確認。
- B00 拇指黑點：權威母圖已於 2026-08-26 完成 v5 修復（154 像素、
  Alpha 零變動、備份與前後 SHA-256 齊全）。
- 落盤：approved-staging-24views/（24 張＋APPROVED-RECORDS.json，
  每張含 SHA-256、閘門結果、目視結論、授權出處）。

## 正式 600 分層（assets/pose-atlas/v4-layered）

- 計數：PNG_COUNT=600、24 視角 × 25 層檔名精確覆蓋、MISSING=0、EXTRA=0。
- 檔案閘門：600／600 RGBA、1024×1536（FILE_GATE_FAILURES=0）。
- layer_manifest.json 存在：BODY_CENTER_CONSTANT=[512,1292]、
  offset 全 0、50Hz／20ms／15° 過渡契約、Z-order 記載完整。

### 接縫 Alpha 缺陷與修復（本輪主要修復工作）

- 發現：Z-order 重組後與 v4-working 母圖比較，RGB 於不透明區零差，
  但層邊界羽化疊合造成 Alpha 低於母圖（deficit max 64、每視角約
  5,000–7,500 像素），在 yaw+000 頸部與下唇下形成可見黑色虛線接縫
  （「頸頸拼貼環」類，不可放行）。
- 修法：seam_alpha_repair.py——不重繪、不位移任何像素；把每個
  deficit 像素的 Alpha 差額補回該像素 Alpha 最大的語意擁有層
  （原 Alpha<8 時 RGB 取母圖值）。每視角迭代 3 輪收斂。
- 備份：所有被修改的層先備份至 seam-repair/layer-backups/
  （*.before-seam-repair.png），修改前 SHA-256 記錄於
  seam-repair-applied.json。
- 修復後最終重驗（final-recheck/layered600-gate-qa.json）：
  - deficit（會露背景形成黑線／透環者）：全 24 視角歸零。
  - 重組 RGB 差（alpha≥128 區）：全 24 視角為 0。
  - 殘餘 Alpha 差全部為 surplus 型（邊緣稍實、不露背景、不閃爍）：
    max 19–47；僅 yaw-045／-030／-015 有額頭髮際小簇 max 107–127
    （各 19–63 像素），4 倍放大目視與母圖無法區分——依使用者
    2026-08-26 核定的驗收尺度（正常顯示看不出即可放行）放行。
  - yaw+000 頸部黑線與唇下細線目視確認消失
    （neck-roi-recompose-after-repair-4x.png）。

## 遺留事項（不阻塞 24／600 計數，待後續）

- 灰底／白底展示版與素體底模、側臉特寫的實體檔案位置待雜湊定位。
- layer_manifest.json 的 status 仍為 staged；正式晉升
  assets/pose-atlas/v4/ 需依 POSE-PACKS.md 走包裝與三平台載入驗證。
- 50Hz 執行期整合驗證屬程式端工作，非素材閘門。
- Git 工作樹（分支 fix/v4.4.2-render-audio-regression、HEAD 6408fa8）
  含大量既有修改；本輪僅新增 artifacts 與修復 v4-layered 接縫，
  未動 v4-source／v4-working／權威母圖。commit 待使用者指示。
