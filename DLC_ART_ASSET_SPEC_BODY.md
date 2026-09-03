# 墨寒 2.5D 參數化分層「身體/頭髮/服裝」— 美術素材補產工作要點（給 ChatGPT Codex）

> 本文件是「墨寒（MoHan）2.5D 改善專案」第二階段美術素材補產的完整製作規格。
> 你（Codex）只負責產出美術素材（PNG 透明圖層），**不得更動任何軟體原始碼**。
> 素材產出後，由 DeepSeek 端負責程式碼接入。

---

## 一、背景與目標

第一階段你已產出「臉部五官」分層素材（`assets/expressions/layered/` 下 54 張 PNG，
三姿態 × 18 圖層）。這些圖層只涵蓋**臉部五官**（眼皮、眉毛、虹膜、紅暈、嘴唇、
嘴角、口腔、牙齒/舌頭、下顎、臉部底圖）。

但墨寒的「整張表情圖」（`assets/expressions/idle.png`、`happy.png` 等）是**半身肖像**，
除了臉部，還包含**身體、頭髮、服裝、袖子、髮飾**。

> 來源註記（2026-09-02）：上述半身肖像已由工作室自有產線自二代素體 `assets/pose-atlas/v5-base/`
> 重新生成為素顏版（髮髻、灰色無袖上衣），不再含一代外部授權美術；外袍、髮型、髮飾與妝容改為
> 執行期圖層，`hair_left`／`hair_right`／`sleeve_left`／`sleeve_right`／`ornament` 在素體本身為空圖層。

為了讓「參數化分層渲染器」能合成**完整半身肖像**（而非只有一張漂浮的臉），
需要你補產「身體/頭髮/服裝」的分層素材，與第一階段的臉部五官分層**共用同一座標系**，
疊加後能精確還原出完整的半身肖像。

**不改變角色五官、臉型、髮飾、服裝身分**。三種姿態（正面 front、朝左 lean、托腮 cheek）
必須同時完成，缺一不可。

---

## 二、需要補產的素材（核心缺口）

### 三種姿態（pose）
| 姿態代號 | 說明 |
|---------|------|
| `front` | 正面 |
| `lean`  | 朝左（未托腮） |
| `cheek` | 托腮（朝左、手托下巴） |

### 每個姿態需要補產的圖層（layer）

| 圖層 | 用途 | 控制項 | 說明 |
|------|------|--------|------|
| `body` | 身體+服裝底圖 | 固定 | 半身肖像的「身體+服裝」底圖，**不含臉部**（臉部由第一階段 18 圖層負責）。含肩膀、胸部、服裝、領口、手臂（不含袖子，袖子另拆） |
| `hair_back` | 後髮（頭部後方頭髮） | 固定 | 位於臉部底圖之後、身體之前的後方頭髮 |
| `hair_left` | 左側前髮 | 物理擺動 | 可獨立動態的前方頭髮（左側） |
| `hair_right` | 右側前髮 | 物理擺動 | 可獨立動態的前方頭髮（右側） |
| `sleeve_left` | 左袖 | 物理擺動 | 可獨立動態的左袖 |
| `sleeve_right` | 右袖 | 物理擺動 | 可獨立動態的右袖 |
| `ornament` | 髮飾/飾品 | 物理擺動 | 髮飾、頭飾等可獨立動態的飾品 |

> 共 **7 個圖層 × 3 姿態 = 21 張 PNG**。

---

## 三、素材規格（嚴格遵守）

1. **格式**：PNG，**RGBA 透明背景**（alpha 通道必須正確，非透明區域 alpha=255）。
2. **尺寸**：**1254 × 1254 像素**（與第一階段臉部五官分層、以及現有 `assets/expressions/*.png` 完全一致）。
3. **座標系**：所有圖層共用**同一座標系、同一錨點**，以現有 `idle.png` / `idle_lean.png` / `idle_front.png` 為對齊基準。
4. **對齊**：每個圖層疊加後，必須能精確還原出「完整半身肖像」的原始位置，不得偏移、縮放或變形。
5. **與第一階段臉部五官分層的關係**：
   - `body` 圖層是「身體+服裝」底圖，**臉部區域必須留空（透明）**，因為臉部由第一階段的 `base` 圖層負責。
   - `hair_back` 圖層位於 `base`（臉部底圖）**之後**，即後方頭髮。
   - `hair_left` / `hair_right` 圖層位於臉部**之前**，即前方頭髮（可遮住部分臉部邊緣）。
   - 疊加順序（由下到上）：`body` → `hair_back` → 臉部五官 18 圖層 → `hair_left`/`hair_right` → `sleeve_left`/`sleeve_right` → `ornament`。
6. **角色身分**：身體、服裝、髮型、髮飾必須與現有權威素材完全一致，不得自行改動角色外觀。
7. **邊緣**：圖層邊緣需有適度羽化（anti-aliasing），避免疊加時出現硬邊或殘影。

---

## 四、命名規則

檔名格式：`{pose}_{layer}.png`

範例：
- `front_body.png`、`front_hair_back.png`、`front_hair_left.png`、`front_hair_right.png`
- `front_sleeve_left.png`、`front_sleeve_right.png`、`front_ornament.png`
- `lean_body.png`、`lean_hair_left.png`、`lean_sleeve_right.png`
- `cheek_body.png`、`cheek_hair_right.png`、`cheek_ornament.png`

---

## 五、存放路徑（完整本機路徑）

請將所有產出的 PNG 素材，放到以下目錄（與第一階段臉部五官分層**同一目錄**）：

```
D:\FlamebladeStudio\CodexProjects\2026-08-13\mohan-multisensory-vision\assets\expressions\layered\
```

即完整路徑範例：
```
D:\FlamebladeStudio\CodexProjects\2026-08-13\mohan-multisensory-vision\assets\expressions\layered\front_body.png
D:\FlamebladeStudio\CodexProjects\2026-08-13\mohan-multisensory-vision\assets\expressions\layered\front_hair_back.png
D:\FlamebladeStudio\CodexProjects\2026-08-13\mohan-multisensory-vision\assets\expressions\layered\front_hair_left.png
D:\FlamebladeStudio\CodexProjects\2026-08-13\mohan-multisensory-vision\assets\expressions\layered\front_hair_right.png
D:\FlamebladeStudio\CodexProjects\2026-08-13\mohan-multisensory-vision\assets\expressions\layered\front_sleeve_left.png
D:\FlamebladeStudio\CodexProjects\2026-08-13\mohan-multisensory-vision\assets\expressions\layered\front_sleeve_right.png
D:\FlamebladeStudio\CodexProjects\2026-08-13\mohan-multisensory-vision\assets\expressions\layered\front_ornament.png
...（以此類推，共 21 張）
```

> 若 `layered` 子目錄不存在，請自行建立。

---

## 六、參考素材（對齊基準）

製作時請以現有權威素材為對齊與身分基準：

```
D:\FlamebladeStudio\CodexProjects\2026-08-13\mohan-multisensory-vision\assets\expressions\idle.png          （cheek 托腮基準）
D:\FlamebladeStudio\CodexProjects\2026-08-13\mohan-multisensory-vision\assets\expressions\idle_lean.png    （lean 朝左基準）
D:\FlamebladeStudio\CodexProjects\2026-08-13\mohan-multisensory-vision\assets\expressions\idle_front.png   （front 正面基準）
```

以及第一階段已產出的臉部五官分層（作為臉部區域的對齊基準）：
```
D:\FlamebladeStudio\CodexProjects\2026-08-13\mohan-multisensory-vision\assets\expressions\layered\front_base.png
D:\FlamebladeStudio\CodexProjects\2026-08-13\mohan-multisensory-vision\assets\expressions\layered\lean_base.png
D:\FlamebladeStudio\CodexProjects\2026-08-13\mohan-multisensory-vision\assets\expressions\layered\cheek_base.png
```

---

## 七、交付檢查清單

- [ ] 三種姿態（front / lean / cheek）各 7 個圖層，共 21 張 PNG
- [ ] 全部 1254 × 1254、RGBA 透明背景
- [ ] `body` 圖層的**臉部區域留空（透明）**，不與第一階段 `base` 圖層重疊
- [ ] 疊加後能精確還原完整半身肖像（身體+頭髮+服裝+臉部五官）
- [ ] 邊緣羽化、無硬邊、無殘影
- [ ] 檔案命名符合 `{pose}_{layer}.png`
- [ ] 全部放入 `assets\expressions\layered\` 目錄（與第一階段臉部五官分層同目錄）

---

## 八、注意事項

1. **不得更動任何 `.py` 原始碼**、`.json` 設定、或現有 `assets/expressions/*.png` 素材。
2. **不得更動第一階段已產出的 54 張臉部五官分層**（`assets/expressions/layered/` 下既有的 `{pose}_{五官}.png`）。
3. 只新增 `assets\expressions\layered\` 目錄下的 21 張新素材。
4. 若對某個圖層的「拆分方式」有疑問（例如頭髮要拆成幾片、袖子是否要與手臂分開），請先詢問，不要自行決定。
5. 完成後回報：產出了哪些檔案、總張數、以及任何你認為需要 DeepSeek 端注意的對齊細節。

---

## 九、疊加順序總覽（供 DeepSeek 端接入參考，Codex 不需實作）

由下到上的完整疊加順序（共 25 圖層）：

1. `body`（身體+服裝底圖）
2. `hair_back`（後髮）
3. `base`（臉部底圖，第一階段）
4. `jaw`（下顎，第一階段）
5. `oral_cavity`（口腔，第一階段）
6. `teeth_tongue`（牙齒/舌頭，第一階段）
7. `lip_lower`（下唇，第一階段）
8. `lip_upper`（上唇，第一階段）
9. `corner_left` / `corner_right`（嘴角，第一階段）
10. `blush_left` / `blush_right`（紅暈，第一階段）
11. `iris_left` / `iris_right`（虹膜，第一階段）
12. `eyelid_left` / `eyelid_right`（眼皮，第一階段）
13. `eyeliner_left` / `eyeliner_right`（眼線，第一階段）
14. `brow_left` / `brow_right`（眉毛，第一階段）
15. `hair_left` / `hair_right`（前髮，本階段）
16. `sleeve_left` / `sleeve_right`（袖子，本階段）
17. `ornament`（髮飾，本階段）
