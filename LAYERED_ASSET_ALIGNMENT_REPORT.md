# 墨寒全身分層素材對齊分析報告（給 Codex）

> 本報告由 DeepSeek 端自動分析腳本產生，用於檢驗你（Codex）產出的 600 張全身分層素材
> （24 視角 × 25 圖層）的對齊品質。**請勿修改任何 .py 原始碼**，僅依本報告修正素材。

---

## 一、分析方法

1. 遍歷 `assets/pose-atlas/v4-layered/` 下全部 600 張 PNG。（2026-09-02 註：本報告分析的是一代 `v4-layered`；執行期自該日起改用 `assets/pose-atlas/v5-base-layered/`，`tools/analyze_layered_assets.py` 的預設路徑已同步指向現行世代。）
2. 計算每張圖的 **Alpha-trimmed bounding box**（透明像素邊界）。
3. 以 `body`（身體軀幹層）為基準，計算其餘 24 層的**相對座標中心**。
4. 對每個圖層，按 yaw 角度排序 24 視角，偵測**相鄰視角間的「突跳」**：
   若某視角的中心偏離「前後視角的線性內插預期值」超過 2 像素，即標記為 outlier。

> 說明：轉頭時頭髮/袖子/飾品是 3D 物體，其 bounding box 中心會**自然移動**，
> 因此本報告改用「相鄰視角連續性」而非「跨視角中心一致」來偵測，避免誤報。

---

## 二、總覽

| 項目 | 數值 |
|------|------|
| 總視角數 | 24 |
| 每視角圖層數 | 25 |
| 總圖層數 | 600 |
| 偵測到的突跳（outlier） | 256 |
| 其中突跳 ≥ 10px | 109 |

---

## 三、需要你重點檢查的圖層（突跳 ≥ 10px）

以下圖層在相鄰視角間有較大的中心突跳，**請逐一檢查是否為對齊錯誤**：

| 圖層 | 突跳 ≥10px 的視角數 | 說明 |
|------|---------------------|------|
| `hair_right` | 12 | 右側前髮，轉頭時可能翻轉 |
| `sleeve_right` | 12 | 右袖 |
| `ornament` | 10 | 髮飾 |
| `hair_back` | 9 | 後髮 |
| `hair_left` | 9 | 左側前髮 |
| `sleeve_left` | 9 | 左袖 |
| `blush_right` | 5 | 右頰紅暈 |
| `corner_right` | 4 | 右嘴角 |
| `iris_right` | 4 | 右虹膜 |
| `eyelid_right` | 4 | 右眼皮 |
| `eyeliner_right` | 4 | 右眼線 |
| `brow_right` | 4 | 右眉 |
| `oral_cavity` | 3 | 口腔 |
| `teeth_tongue` | 3 | 牙齒/舌頭 |
| `lip_lower` | 3 | 下唇 |
| `lip_upper` | 3 | 上唇 |

> **重要提醒**：頭髮/袖子/飾品的突跳，**大部分是轉頭時 3D 物體的自然非線性移動**，
> 不一定是對齊錯誤。請優先檢查**臉部五官**（base/jaw/lips/iris/eyelid/brow）的突跳，
> 這些才是真正可能影響「真人女孩感」的對齊問題。

---

## 四、完整 outlier 清單（JSON）

完整的 256 個 outlier 明細（含每個圖層的實際中心、預期中心、突跳像素數），
請見同目錄下的 JSON 檔案：

```
D:\FlamebladeStudio\CodexProjects\2026-08-13\mohan-multisensory-vision\layered_asset_analysis.json
```

該 JSON 的 `outliers` 陣列包含每個突跳的：
- `view_id`：視角
- `layer`：圖層
- `yaw_degrees`：yaw 角度
- `center`：實際中心（相對 body）
- `expected_center`：線性內插預期中心
- `jump_pixels`：突跳像素數

---

## 五、裁剪建議座標（Crop Coordinates）

JSON 的 `crop_coordinates` 欄位包含每張圖的 Alpha-trimmed 裁剪座標
（格式 `[left, top, right, bottom]`），供你對齊修正時參考。

範例（`yaw+000-pitch+00` 視角）：
```json
{
  "base": [440, 183, 588, 366],
  "body": [265, 1096, 759, 1488],
  "hair_back": [260, 85, 763, 1096],
  "hair_left": [232, 85, 513, 1096],
  "hair_right": [512, 84, 791, 1096],
  "sleeve_left": [232, 421, 429, 955],
  "sleeve_right": [596, 421, 791, 955],
  "ornament": [445, 86, 602, 310]
}
```

---

## 六、修正要求

1. **維持原尺寸**：1024 × 1536，不得縮放。
2. **維持共同錨點**：所有圖層共用同一座標系、同一錨點。
3. **維持規定疊加順序**：body → hair_back → base → … → ornament。
4. **背向視角的臉部圖層透明是刻意設計**，請維持，不要補上五官。
5. 修正後請回報：修正了哪些圖層、修正方式、以及任何你認為需要 DeepSeek 端注意的細節。
