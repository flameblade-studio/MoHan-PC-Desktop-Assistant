# 選項 C：徹底重構渲染流程 — 架構規劃

> 目標：廢除「整張表情圖切換」+「嘴巴補丁」兩套舊機制，讓
> `LayeredParametricFaceRenderer` 成為唯一的半身渲染路徑，並實作全身 24 視角
> 分層渲染器取代 PoseAtlas 靜態照 + 程序化嘴巴。

---

## 一、現況盤點

### 舊機制 1：整張表情圖切換（`expression_pixmaps`）
- 載入：`companion_visual_dynamics.py` 的 `_build_character_widget` / `_load_expression_assets`
- 使用：5 個檔案 58 處（表情切換、眨眼、嘴巴補丁、視差、物理）
- 承載功能：表情切換、眨眼合成、嘴巴補丁、視線視差、物理圖層

### 舊機制 2：嘴巴補丁（`face_renderer` = `ParametricFaceRenderer`）
- 注入：`service_container.py` 的 `face_renderer_factory`
- 使用：`companion_face_animation.py` 的 `_mouth_aperture_pixmap`、`_blink_composite`
- 契約：只改嘴巴 clip 區域，其餘像素與 base 一致（`test_expression_pipeline.py` 驗證）

### 新機制：分層渲染器（`LayeredParametricFaceRenderer`）
- 已實作：25 圖層合成（18 五官 + 7 身體/頭髮/服裝）
- 已具備動態：眨眼（eyelid/eyeliner opacity）、嘴巴（oral_cavity/teeth_tongue/lips）、
  表情（brow/blush/corner）、視線（iris）
- 尚未接入：正式渲染流程

---

## 二、重構策略

### 核心原則
分層渲染器**已經具備**大部分動態能力（眨眼、嘴巴、表情、視線），重構的關鍵是：
**把「表情切換」從「切換預載圖」改成「切換 FaceMotionFrame 的 expression 參數，然後重新合成」**。

### 分階段執行

#### 階段 1：全身 24 視角分層渲染器（獨立、低風險）
- 新增 `infrastructure/layered_full_body_assets.py`（載入 24 視角 × 25 圖層）
- 新增 `infrastructure/layered_full_body_renderer.py`（24 視角合成 + 相鄰視角插值）
- 取代 `pose_atlas_assets.py` 的程序化嘴巴
- 這部分獨立於半身，風險低，可先完成

#### 階段 2：半身分層渲染器接入（核心重構）
- 讓 `companion_visual_dynamics` 用分層渲染器取代 `expression_pixmaps`
- 表情切換改為「切換 FaceMotionFrame.expression + 重新合成」
- 廢除 `face_renderer`（嘴巴補丁），嘴巴開合由分層渲染器的 oral_cavity/lips 處理

#### 階段 3：同步修改測試
- `test_expression_pipeline.py`：嘴巴補丁契約 → 分層合成契約
- `test_face_renderer.py`：ParametricFaceRenderer → LayeredParametricFaceRenderer
- 其他依賴舊契約的測試

---

## 三、風險與緩解

| 風險 | 緩解 |
|------|------|
| 破壞大量既有功能 | 分階段執行，每階段跑完整測試 |
| 分層渲染器動態能力不足 | 先補齊眨眼/嘴巴/視線/表情的完整動態 |
| 測試契約大改 | 明確記錄新契約，逐一更新測試 |

---

## 四、待確認事項

1. 分層渲染器合成的半身圖（1254×1254）需縮放到 465×465 才能與現有畫布一致
2. 表情切換的「過渡動畫」（crossfade）如何用分層渲染器實現
3. 視線（iris 位移）如何從 `shy_gaze` 傳遞到分層渲染器
