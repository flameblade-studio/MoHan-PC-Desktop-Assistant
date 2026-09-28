# V5 七姿勢完整表情候選（84 態）

日期：2026-09-21

## 結果

- 以七張使用者確認的 V5 素顏姿勢為唯一身體／臉型基底。
- 從既有核對過的 V5 眼態來源建立 rest／half／closed。
- 既有生成圖庫不足以提供七姿勢一致的 small／A／O 嘴型，因此用內建 ImageGen 為每個姿勢各產生一張三聯圖；每張只改嘴部及緊鄰唇周，保留身份、姿勢、相機、髮型、背景與表情語意。
- 三聯圖依序為 small、A、O。原圖保留於 Codex generated_images，另複製至 `scratchpad/mohan-v2-v5-complete-seven-151/generated-mouth-strips/`。
- 第一版沿用上一代嘴型差分，出現白邊與齒列殘影，已明確標為 rejected，未正式安裝。
- 第二版只在各姿勢的 lips 安全區貼合新嘴型，生成 7 姿勢 × 4 嘴型 × 3 眼態＝84 張 RGBA 候選。

## ImageGen 提示共同約束

Identity-preserving horizontal triptych of the exact same approved V5 MoHan woman and the exact same pose, camera, background, hairstyle and facial identity. Edit only the mouth and immediately adjacent lip pixels. Panel 1 is a small speech mouth, panel 2 is a natural A mouth, panel 3 is a rounded O mouth. Preserve all other pixels and the pose-specific expression. No makeup changes, seams, text or watermark.

七次呼叫分別加入 front-crossed、left-neutral、cheek-rest、front-eureka、front-mock-scold、front-mock-hit、front-exasperated 的姿勢描述。使用內建 ImageGen，未使用外部 CLI。

## 隔離驗證

- `candidate-root-v2/manifest.json`：schema `mohan.complete-halfbody-expressions.v1`，7 poses、52 expression bindings、84 frames。
- 正式 loader 實載：7 poses、52 bindings、84 frames，0 缺漏。
- `boundary-verification-v2.json`：56 組合；alpha 全相同、嘴部變化全在 lips 安全區、眼態變化全在 eyes 安全區。
- `runtime-v2/runtime-verification.json`：正式 `CompleteHalfbodyRenderer` 載入並渲染 84 張；alpha 全等、實色像素全等、灰底合成誤差均不超過 1 階（Qt 半透明預乘捨入）。
- 四支建置／驗證腳本 Ruff：All checks passed。
- 重建 84 張後逐檔 SHA-256 與先前候選完全相同，證明流程可重現。

## 邊界

- 正式 `assets/expressions/complete-expressions/` 尚未覆寫。
- 第二版已完成隔離封裝與實際渲染驗收；整組審閱圖為 `v5-seven-pose-12-state-review-v2.png`。
- 正式接入須使用第二版，不得使用已拒絕的第一版。
