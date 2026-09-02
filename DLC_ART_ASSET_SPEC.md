# 墨寒 2.5D 參數化分層臉部 — 美術素材製作工作要點（給 ChatGPT Codex）

> 本文件是「墨寒（MoHan）2.5D 改善專案」所需美術素材的完整製作規格。
> 你（Codex）只負責產出美術素材（PNG 透明圖層），**不得更動任何軟體原始碼**。
> 素材產出後，由 DeepSeek 端負責程式碼接入。

---

## 一、背景與目標

墨寒目前用「整張表情圖片切換」來呈現臉部（`assets/expressions/*.png`）。
本次要升級為「**參數化分層 2.5D 臉部**」：把臉拆成可獨立控制、可連續變形的透明圖層，
讓眼皮、眉毛、虹膜、紅暈、嘴唇、嘴角、口腔、下顎等五官能各自平滑動起來。

**不改變角色五官、臉型、髮飾、服裝身分**。三種姿態（正面 front、朝左 lean、托腮 cheek）
必須同時完成，缺一不可。

---

## 二、需要製作的素材（核心缺口）

目前 `assets/expressions/` 只有「整張表情圖」和「`v120_*` 物理切層（頭髮/袖子/飾品）」，
**缺少「臉部五官分層透明圖層」**。

> 來源註記（2026-09-02）：本文件描述的權威半身素材已由工作室自有產線自二代素體
> `assets/pose-atlas/v5-base/` 重新生成為素顏版（髮髻、灰色無袖上衣），不再含一代外部授權美術；
> 外袍、髮型、髮飾與妝容改為執行期圖層，因此 `v120_*` 的頭髮／袖子／髮飾切層依契約為全透明，
> 舊的 `physics_*` 圖層已移除。請為以下三種姿態，各製作一整套分層素材：

### 三種姿態（pose）
| 姿態代號 | 說明 |
|---------|------|
| `front` | 正面 |
| `lean`  | 朝左（未托腮） |
| `cheek` | 托腮（朝左、手托下巴） |

### 每個姿態需要的分層圖層（layer）
| 圖層 | 用途 | 控制項 |
|------|------|--------|
| 基底皮膚 `base` | 完整臉部底圖（含五官輪廓、髮際、下巴） | 固定 |
| 左眼皮 `eyelid_left` | 眨眼（左眼） | blink |
| 右眼皮 `eyelid_right` | 眨眼（右眼） | blink |
| 左眼線 `eyeliner_left` | 眼線（隨眼皮移動） | blink |
| 右眼線 `eyeliner_right` | 眼線 | blink |
| 左眉 `brow_left` | 挑眉/皺眉 | brow_lift / brow_tension |
| 右眉 `brow_right` | 挑眉/皺眉 | brow_lift / brow_tension |
| 左虹膜 `iris_left` | 視線移動 | gaze |
| 右虹膜 `iris_right` | 視線移動 | gaze |
| 左頰紅暈 `blush_left` | 害羞/開心紅暈 | blush |
| 右頰紅暈 `blush_right` | 紅暈 | blush |
| 上唇 `lip_upper` | 說話嘴型 | aperture / rounding |
| 下唇 `lip_lower` | 說話嘴型 | aperture / jaw |
| 左嘴角 `corner_left` | 微笑嘴角 | corner_smile |
| 右嘴角 `corner_right` | 微笑嘴角 | corner_smile |
| 口腔 `oral_cavity` | 張嘴時的暗色口腔 | aperture |
| 牙齒/舌頭 `teeth_tongue` | 張嘴時露出的牙齒與舌頭 | aperture |
| 下顎/下巴 `jaw` | 下顎位移影響區 | jaw |

> 共 **18 個圖層 × 3 姿態 = 54 張 PNG**。

---

## 三、素材規格（嚴格遵守）

1. **格式**：PNG，**RGBA 透明背景**（alpha 通道必須正確，非透明區域 alpha=255）。
2. **尺寸**：**1254 × 1254 像素**（與現有 `assets/expressions/*.png` 一致）。
3. **座標系**：所有圖層共用同一座標系、同一錨點（以現有 `idle.png` / `idle_lean.png` / `idle_front.png` 為對齊基準）。
4. **對齊**：每個圖層疊加後，必須能精確還原出「完整表情圖」的原始五官位置，不得偏移、縮放或變形。
5. **角色身分**：五官、臉型、髮飾、服裝必須與現有權威素材完全一致，不得自行改動角色外觀。
6. **邊緣**：圖層邊緣需有適度羽化（anti-aliasing），避免疊加時出現硬邊或殘影。

---

## 四、命名規則

檔名格式：`{pose}_{layer}.png`

範例：
- `front_base.png`、`front_eyelid_left.png`、`front_brow_right.png`、`front_lip_upper.png`
- `lean_base.png`、`lean_iris_left.png`、`lean_blush_right.png`
- `cheek_base.png`、`cheek_jaw.png`、`cheek_teeth_tongue.png`

---

## 五、存放路徑（完整本機路徑）

請將所有產出的 PNG 素材，放到以下目錄：

```
D:\FlamebladeStudio\CodexProjects\2026-08-13\mohan-multisensory-vision\assets\expressions\layered\
```

即完整路徑範例：

```
D:\FlamebladeStudio\CodexProjects\2026-08-13\mohan-multisensory-vision\assets\expressions\layered\front_base.png
D:\FlamebladeStudio\CodexProjects\2026-08-13\mohan-multisensory-vision\assets\expressions\layered\front_eyelid_left.png
D:\FlamebladeStudio\CodexProjects\2026-08-13\mohan-multisensory-vision\assets\expressions\layered\lean_base.png
D:\FlamebladeStudio\CodexProjects\2026-08-13\mohan-multisensory-vision\assets\expressions\layered\cheek_base.png
...（以此類推，共 54 張）
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

---

## 七、交付檢查清單

- [ ] 三種姿態（front / lean / cheek）各 18 個圖層，共 54 張 PNG
- [ ] 全部 1254 × 1254、RGBA 透明背景
- [ ] 疊加後能精確還原原始五官位置與角色身分
- [ ] 邊緣羽化、無硬邊、無殘影
- [ ] 檔案命名符合 `{pose}_{layer}.png`
- [ ] 全部放入 `assets\expressions\layered\` 目錄

---

## 八、注意事項

1. **不得更動任何 `.py` 原始碼**、`.json` 設定、或現有 `assets/expressions/*.png` 素材。
2. 只新增 `assets\expressions\layered\` 目錄下的新素材。
3. 若對某個圖層的「拆分方式」有疑問（例如眼皮與眼線是否要分開），請先詢問，不要自行決定。
4. 完成後回報：產出了哪些檔案、總張數、以及任何你認為需要 DeepSeek 端注意的對齊細節。

---

## 九、妝容圖層（makeup slot，2026-09-02 新增）

擁有者裁決：素體（`*_base.png`）保持**素顏**、頭髮收成髮髻；外袍、散髮（含鬢髮）、銀髮飾與**妝容**全部是可開關、可替換的獨立圖層，半身與全身同一標準。妝容**不再畫進 base**，而是以「妝容套件」的形式提供，格式與衣裝套件完全相同（`docs/OUTFIT-PACKS.md` 的 `makeup` 一節是權威）。

### 半身要製作的圖層

每個半身輪廓（silhouette）× 每個 variant 各三張透明 RGBA PNG，畫布 **1254 × 1254**、與 `{pose}_base.png` 同座標系、anchor 固定 0,0：

| slot | 內容 | 禁畫 |
|------|------|------|
| `eyes` | 眼線、眼影、睫毛、眉（合成一張） | 可見虹膜（眼皮遮住的部分可畫） |
| `cheeks` | 腮紅 | — |
| `lips` | 唇色／唇彩 | 牙齒、口腔 |

半身輪廓與 rig 的對應：`cheek-rest`→`cheek`、`left-neutral`→`lean`、`front-crossed`／`front-mock-scold`／`front-mock-hit`／`front-eureka`／`front-exasperated`→`front`（四個手勢輪廓沿用 front 的頭部 rig，圖層可直接複製 front 的成品）。

### 安全區（不可越界）

每張圖層的**所有不透明像素**都必須落在 `assets/makeup-safe-regions.json` 為該 silhouette／slot 定義的矩形內（由 `{pose}_eyelid_*`／`_eyeliner_*`／`_brow_*`、`_blush_*`、`_lip_*`／`_corner_*` 的 alpha 外框各自外擴 24／48／20 px 而得；`py -3.15 tools/build_makeup_safe_regions.py --check` 可驗證檔案未過期）。越界一個像素，`tools/build_outfit_pack.py` 封裝與雲裳閣匯入都會整包拒絕。除安全區外，其餘像素 alpha 必須為 0；不得畫皮膚、不得重繪五官。

### 內建妝容（工作室交付物）

item `mohan-signature` 兩個 variant：`classic`（原妝，對齊四代 `assets/pose-atlas/v4` 的臉部外觀）與 `light`（淡雅，較淡的同套妝）。檔名已由範本寫死：

```
assets/makeup/builtin/assets/mohan-signature-{variant}-{silhouette}-{slot}.png
```

半身 7 輪廓 × 3 slot × 2 variant = 42 張（全身另 144 張，見 `DLC_ART_ASSET_SPEC_FULLBODY.md` 第十節）。素材放齊後執行：

```
py -3.15 tools/build_outfit_pack.py assets/makeup/builtin/manifest.json assets/makeup/builtin assets/makeup/mohan.makeup.builtin.mohan-outfit
```

封裝成功即代表 sha256／尺寸／安全區全部通過；產出的 `.mohan-outfit` 由 `assets/makeup/` 直接供應執行期，使用者不可移除。第三方純妝容 DLC 同樣以 `tools/scaffold_makeup_pack_manifest.py` 產生範本、補齊 PNG、以 `tools/build_outfit_pack.py` 封裝，然後從雲裳閣「匯入服裝套件」按鈕安裝。
