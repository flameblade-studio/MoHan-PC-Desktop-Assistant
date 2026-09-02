# 墨寒 2.5D 參數化分層「全身 PoseAtlas」— 美術素材補產工作要點（給 ChatGPT Codex）

> 本文件是「墨寒（MoHan）2.5D 改善專案」第三階段美術素材補產的完整製作規格。
> 你（Codex）只負責產出美術素材（PNG 透明圖層），**不得更動任何軟體原始碼**。
> 素材產出後，由 DeepSeek 端負責程式碼接入。

---

## 一、背景與目標

墨寒目前有兩套身體渲染體系：

1. **半身**（`assets/expressions/*.png`）：3 姿態（front / lean / cheek），用於日常對話。
2. **全身**（`assets/pose-atlas/v5-base/*.png`）：24 個 yaw 視角，用於手勢、換裝、主人到來等全身鏡頭。

全身目前是「單一靜態全身照 + 程序化嘴巴（暗色橢圓）」。本次要將全身也升級為
「**參數化分層**」：把全身照拆成可獨立控制、可連續變形的透明圖層，讓全身的
嘴巴、眼皮、眉毛、虹膜、紅暈等五官也能平滑動起來，徹底取代靜態全身照。

**不改變角色五官、臉型、髮飾、服裝身分**。24 個 yaw 視角必須同時完成，缺一不可。

---

## 二、需要補產的素材（核心缺口）

### 24 個 yaw 視角（view）

全身 PoseAtlas 使用 24 個 yaw 角度（每 15 度一張），view_id 命名如下：

```
yaw-180-pitch+00, yaw-165-pitch+00, yaw-150-pitch+00, yaw-135-pitch+00,
yaw-120-pitch+00, yaw-105-pitch+00, yaw-090-pitch+00, yaw-075-pitch+00,
yaw-060-pitch+00, yaw-045-pitch+00, yaw-030-pitch+00, yaw-015-pitch+00,
yaw+000-pitch+00, yaw+015-pitch+00, yaw+030-pitch+00, yaw+045-pitch+00,
yaw+060-pitch+00, yaw+075-pitch+00, yaw+090-pitch+00, yaw+105-pitch+00,
yaw+120-pitch+00, yaw+135-pitch+00, yaw+150-pitch+00, yaw+165-pitch+00
```

> 共 **24 個視角**。

### 每個視角需要的分層圖層（layer）

與半身分層一致，共 **25 個圖層**（18 臉部五官 + 7 身體/頭髮/服裝）：

**臉部五官（18 圖層）**：
| 圖層 | 用途 | 控制項 |
|------|------|--------|
| `base` | 完整臉部底圖（含五官輪廓、髮際、下巴） | 固定 |
| `jaw` | 下顎位移影響區 | jaw |
| `oral_cavity` | 張嘴時的暗色口腔 | aperture |
| `teeth_tongue` | 張嘴時露出的牙齒與舌頭 | aperture |
| `lip_lower` | 下唇 | aperture / jaw |
| `lip_upper` | 上唇 | aperture / rounding |
| `corner_left` | 左嘴角 | corner_smile |
| `corner_right` | 右嘴角 | corner_smile |
| `blush_left` | 左頰紅暈 | blush |
| `blush_right` | 右頰紅暈 | blush |
| `iris_left` | 左虹膜 | gaze |
| `iris_right` | 右虹膜 | gaze |
| `eyelid_left` | 左眼皮 | blink |
| `eyelid_right` | 右眼皮 | blink |
| `eyeliner_left` | 左眼線 | blink |
| `eyeliner_right` | 右眼線 | blink |
| `brow_left` | 左眉 | brow_lift / brow_tension |
| `brow_right` | 右眉 | brow_lift / brow_tension |

**身體/頭髮/服裝（7 圖層）**：
| 圖層 | 用途 | 控制項 |
|------|------|--------|
| `body` | 全身+服裝底圖（臉部區域留空） | 固定 |
| `hair_back` | 後髮 | 固定 |
| `hair_left` | 左側前髮 | 物理擺動 |
| `hair_right` | 右側前髮 | 物理擺動 |
| `sleeve_left` | 左袖 | 物理擺動 |
| `sleeve_right` | 右袖 | 物理擺動 |
| `ornament` | 髮飾/飾品 | 物理擺動 |

> 共 **25 個圖層 × 24 視角 = 600 張 PNG**。

---

## 三、素材規格（嚴格遵守）

1. **格式**：PNG，**RGBA 透明背景**（alpha 通道必須正確，非透明區域 alpha=255）。
2. **尺寸**：**1024 × 1536 像素**（與現有 `assets/pose-atlas/v5-base/*.png` 完全一致）。
3. **座標系**：所有圖層共用**同一座標系、同一錨點**，以現有 `assets/pose-atlas/v5-base/{view_id}.png` 為對齊基準。
4. **對齊**：每個圖層疊加後，必須能精確還原出「完整全身照」的原始位置，不得偏移、縮放或變形。
5. **臉部區域**：`body` 圖層的**臉部區域必須留空（透明）**，因為臉部由 `base` 圖層負責。
6. **角色身分**：五官、臉型、髮飾、服裝、身體比例必須與現有權威素材完全一致，不得自行改動角色外觀。
7. **邊緣**：圖層邊緣需有適度羽化（anti-aliasing），避免疊加時出現硬邊或殘影。

---

## 四、命名規則

檔名格式：`{view_id}_{layer}.png`

範例：
- `yaw+000-pitch+00_base.png`、`yaw+000-pitch+00_body.png`
- `yaw+000-pitch+00_lip_upper.png`、`yaw+000-pitch+00_eyelid_left.png`
- `yaw-090-pitch+00_hair_left.png`、`yaw+045-pitch+00_sleeve_right.png`

> 注意：view_id 中的 `+` 號必須保留（例如 `yaw+000-pitch+00`），不得省略或改寫。

---

## 五、存放路徑（完整本機路徑）

請將所有產出的 PNG 素材，放到以下目錄：

```
D:\FlamebladeStudio\CodexProjects\2026-08-13\mohan-multisensory-vision\assets\pose-atlas\v5-base-layered\
```

即完整路徑範例：
```
D:\FlamebladeStudio\CodexProjects\2026-08-13\mohan-multisensory-vision\assets\pose-atlas\v5-base-layered\yaw+000-pitch+00_base.png
D:\FlamebladeStudio\CodexProjects\2026-08-13\mohan-multisensory-vision\assets\pose-atlas\v5-base-layered\yaw+000-pitch+00_body.png
D:\FlamebladeStudio\CodexProjects\2026-08-13\mohan-multisensory-vision\assets\pose-atlas\v5-base-layered\yaw+000-pitch+00_lip_upper.png
...（以此類推，共 600 張）
```

> 若 `v5-base-layered` 子目錄不存在，請自行建立。

---

## 六、參考素材（對齊基準）

製作時請以現有權威素材為對齊與身分基準：

```
D:\FlamebladeStudio\CodexProjects\2026-08-13\mohan-multisensory-vision\assets\pose-atlas\v5-base\yaw+000-pitch+00.png
D:\FlamebladeStudio\CodexProjects\2026-08-13\mohan-multisensory-vision\assets\pose-atlas\v5-base\yaw-090-pitch+00.png
...（24 個視角的靜態全身照）
```

以及半身分層素材（作為臉部五官的對齊基準）：
```
D:\FlamebladeStudio\CodexProjects\2026-08-13\mohan-multisensory-vision\assets\expressions\layered\front_base.png
D:\FlamebladeStudio\CodexProjects\2026-08-13\mohan-multisensory-vision\assets\expressions\layered\lean_base.png
D:\FlamebladeStudio\CodexProjects\2026-08-13\mohan-multisensory-vision\assets\expressions\layered\cheek_base.png
```

---

## 七、交付檢查清單

- [ ] 24 個視角（yaw-180 到 yaw+165）各 25 個圖層，共 600 張 PNG
- [ ] 全部 1024 × 1536、RGBA 透明背景
- [ ] `body` 圖層的**臉部區域留空（透明）**，不與 `base` 圖層重疊
- [ ] 疊加後能精確還原完整全身照（身體+頭髮+服裝+臉部五官）
- [ ] 邊緣羽化、無硬邊、無殘影
- [ ] 檔案命名符合 `{view_id}_{layer}.png`（`+` 號保留）
- [ ] 全部放入 `assets\pose-atlas\v5-base-layered\` 目錄

---

## 八、注意事項

1. **不得更動任何 `.py` 原始碼**、`.json` 設定、或現有 `assets/pose-atlas/v5-base/*.png` 素材。
2. **不得更動半身分層素材**（`assets/expressions/layered/` 下的既有素材）。
3. 只新增 `assets\pose-atlas\v5-base-layered\` 目錄下的 600 張新素材。
4. 若對某個圖層的「拆分方式」有疑問（例如全身的頭髮要拆成幾片、袖子是否要與手臂分開），請先詢問，不要自行決定。
5. 完成後回報：產出了哪些檔案、總張數、以及任何你認為需要 DeepSeek 端注意的對齊細節。

---

## 九、疊加順序總覽（供 DeepSeek 端接入參考，Codex 不需實作）

由下到上的完整疊加順序（共 25 圖層，與半身一致）：

1. `body`（全身+服裝底圖）
2. `hair_back`（後髮）
3. `base`（臉部底圖）
4. `jaw`（下顎）
5. `oral_cavity`（口腔）
6. `teeth_tongue`（牙齒/舌頭）
7. `lip_lower`（下唇）
8. `lip_upper`（上唇）
9. `corner_left` / `corner_right`（嘴角）
10. `blush_left` / `blush_right`（紅暈）
11. `iris_left` / `iris_right`（虹膜）
12. `eyelid_left` / `eyelid_right`（眼皮）
13. `eyeliner_left` / `eyeliner_right`（眼線）
14. `brow_left` / `brow_right`（眉毛）
15. `hair_left` / `hair_right`（前髮）
16. `sleeve_left` / `sleeve_right`（袖子）
17. `ornament`（髮飾）

---

## 十、妝容圖層（makeup slot，2026-09-02 新增）

擁有者裁決：全身素體 `assets/pose-atlas/v5-base` 保持**素顏**、髮髻收攏；外袍、散髮、銀髮飾與**妝容**全部是可開關、可替換的獨立圖層，與半身同一標準。妝容以「妝容套件」提供，格式與衣裝套件相同（權威文件：`docs/OUTFIT-PACKS.md` 的 `makeup` 一節）。

### 全身要製作的圖層

24 個 yaw 視角 × 每個 variant 各三張透明 RGBA PNG，畫布 **1024 × 1536**、與 `{view_id}_base.png` 同座標系、anchor 固定 0,0：

| slot | 內容 | 禁畫 |
|------|------|------|
| `eyes` | 眼線、眼影、睫毛、眉（合成一張） | 可見虹膜 |
| `cheeks` | 腮紅 | — |
| `lips` | 唇色／唇彩 | 牙齒、口腔 |

### 安全區與背面視角

所有不透明像素都必須落在 `assets/makeup-safe-regions.json` 為該 view_id／slot 定義的矩形內（由 `assets/pose-atlas/v5-base-layered/{view_id}_eyelid_*`／`_eyeliner_*`／`_brow_*`、`_blush_*`、`_lip_*`／`_corner_*` 的 alpha 外框各自外擴 24／48／20 px 而得）。看不到臉的視角（`yaw-180` 至 `yaw-105` 與 `yaw+105` 至 `yaw+165`）安全區為空，對應圖層必須是**完全透明**的 1024 × 1536 PNG，但檔案仍要交付（格式要求 31 個 silhouette 齊全）。側面視角只看得到一隻眼、一邊腮紅時，只畫看得到的那一側。

### 交付物與封裝

item `mohan-signature`，variant `classic`（原妝，對齊 `assets/pose-atlas/v4` 的臉部外觀）與 `light`（淡雅）。檔名由範本寫死：

```
assets/makeup/builtin/assets/mohan-signature-{variant}-{view_id}-{slot}.png
```

24 視角 × 3 slot × 2 variant = 144 張；連同半身 42 張（`DLC_ART_ASSET_SPEC.md` 第九節）共 186 張，全部放齊後執行：

```
py -3.15 tools/build_outfit_pack.py assets/makeup/builtin/manifest.json assets/makeup/builtin assets/makeup/mohan.makeup.builtin.mohan-outfit
```

封裝即驗證 sha256、尺寸與安全區；任何一張越界或缺漏都整包拒絕。
