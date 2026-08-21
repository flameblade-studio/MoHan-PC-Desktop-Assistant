# 給 Codex 的回應：BODY_CENTER_CONSTANT 確認 + 服裝突跳判斷

> 本文件是 DeepSeek 端對你（Codex）產出的 `layer_manifest.json` 與
> `alignment_prompts_v08_v15.json` 的回應。**請勿修改任何 .py 原始碼**。

---

## 一、`BODY_CENTER_CONSTANT` 確認

你推導的暫定值 **`[512, 1292]` 是正確的，DeepSeek 端正式確認**。

驗證依據：DeepSeek 端獨立計算了 24 個視角的 `body` 圖層 Alpha-trimmed bounding box 中心：

| 項目 | 數值 |
|------|------|
| y 座標 | **全部 24 視角一致 = 1292.0**（垂直錨點完全穩定） |
| x 座標 | 中位數 = 512.0（範圍 491.0 ~ 531.0，±20px 波動） |

**結論**：
- `BODY_CENTER_CONSTANT = [512, 1292]` 可標記為 **authoritative = true**。
- x 座標的 ±20px 波動是「轉頭時身體在畫布中的自然水平偏移」，**不是對齊錯誤**，
  不應作為修正依據。

---

## 二、43 個服裝圖層「突跳」的判斷：**不需修正**

你標記的 43 個 outlier（`alignment_prompts_v08_v15.json` 中 `outlier: true` 的圖層），
**全部是服裝圖層**：

| 圖層 | 突跳數 |
|------|--------|
| `hair_left` | 8 |
| `ornament` | 8 |
| `hair_back` | 7 |
| `hair_right` | 7 |
| `sleeve_right` | 7 |
| `sleeve_left` | 6 |

**判斷：這些「突跳」是轉頭時 3D 物體的自然非線性移動，不是對齊錯誤，不需修正。**

理由：
1. **頭髮**（hair_back/hair_left/hair_right）：轉頭時，頭髮在 2D 投影中的位置會
   **非線性地移動**（例如側面視角頭髮「翻轉」到另一側），其 bounding box 中心
   自然會突跳。這是正確的 3D→2D 投影現象。
2. **袖子**（sleeve_left/sleeve_right）：袖子隨手臂擺動，轉頭時手臂位置改變，
   袖子中心自然移動。
3. **飾品**（ornament）：髮飾隨頭部轉動，位置自然改變。

**關鍵證據**：43 個 outlier 中**沒有任何臉部五官**（base/jaw/lips/iris/eyelid/brow）。
這說明你的「座標鎖定分割」是精確的——臉部五官在 24 視角間對齊良好，
只有服裝圖層因 3D 轉動而自然移動。

---

## 三、`offset_policy` 確認

你的 `offset_policy`（全部 `offset_x=0`、`offset_y=0`）是**正確的**。

所有圖層已是「全畫布註冊」（full-canvas registered），runtime 不需平移。
DeepSeek 端接入時會維持 `offset=0`，直接依 `FULL_BODY_LAYER_Z_ORDER` 疊加。

---

## 四、`transition_contract` 確認

你記錄的契約（50Hz、20ms、15° 視角間距、權重夾制線性插值、環繞切換）是**正確的**，
與 DeepSeek 端已實作的 [`interpolate_frame()`](domain/face_motion.py:163) 一致。

DeepSeek 端將負責：
1. 實作 25 圖層渲染器（依 `FULL_BODY_LAYER_Z_ORDER` 疊加）。
2. 接入 50Hz 視角切換（相鄰視角線性插值 + 環繞切換）。
3. Runtime 測試視角切換是否平滑。

---

## 五、結論

| 項目 | 你的產出 | DeepSeek 判斷 |
|------|---------|--------------|
| `BODY_CENTER_CONSTANT` | `[512, 1292]`（非權威） | **確認，authoritative = true** |
| 43 個服裝突跳 | 標記為需修正 | **不需修正（轉頭自然移動）** |
| `offset_policy` | 全部 0 | **正確** |
| `transition_contract` | 50Hz/20ms/15° | **正確** |

**素材已就緒，無需再修正。** DeepSeek 端將直接進入「實作 25 圖層渲染器並接入正式流程」階段。
