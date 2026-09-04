"""產線契約常數。

數值集中於此，避免 scratchpad 腳本各自漂移。每組數值都記錄原始來源與
量測依據；改動時應同步更新該註解與回歸測試。
"""

from __future__ import annotations

lazy from dataclasses import dataclass
lazy from typing import Final


# 來源：既有 half-body 執行期資產與 companion face contract；量測：輸入與
# 執行期畫布均以這兩個尺寸驗收，465/1254 也是既有矩形換算比例。
CANVAS_SIZE: Final = 1254
RUNTIME_SIZE: Final = 465
CANVAS_TO_RUNTIME: Final = CANVAS_SIZE / RUNTIME_SIZE
IMAGE_DIMENSIONS: Final = 3
BGR_CHANNELS: Final = 3
RGBA_CHANNELS: Final = 4
RECTANGLE_FIELDS: Final = 4

# 來源：tools/extract_chroma_alpha.py；量測：既有鍵色工具的硬透明與漸變
# 門檻，保留相同 alpha 行為以避免產線與執行期分叉。
CHROMA_SPILL_THRESHOLD: Final = 92
CHROMA_HARD_THRESHOLD: Final = 34
MAGENTA_BGR: Final = (255, 0, 255)
ALPHA_EPSILON: Final = 1e-3
MAGENTA_DETECTION_RED_BLUE_MIN: Final = 200
MAGENTA_DETECTION_GREEN_MAX: Final = 80

# 來源：scratchpad/halfbody/align_to_template.py 的 YuNet 建構參數；量測：
# 沿用已驗證的模型信心、NMS 與最多候選臉數設定。
YUNET_SCORE_THRESHOLD: Final = 0.6
YUNET_NMS_THRESHOLD: Final = 0.3
YUNET_TOP_K: Final = 100
DETECTION_BACKGROUND_GRAY: Final = 128.0

# 來源：scratchpad/halfbody/derive_variants.py；量測：465 空間矩形先換算
# 到 1254，再向內縮 2 px，10 px 內羽化只落在矩形內。
RECT_INSET_PIXELS: Final = 2
RECT_FEATHER_PIXELS: Final = 10

# scratchpad/halfbody/align_ref_to_base.py 的 head-top fallback。12 列/行與
# 1 px 最小跨度沿用來源的防除零保護；依輸入頭部最上方 alpha 量測。
HEAD_ANCHOR_SCAN_ROWS: Final = 12
ANCHOR_SPAN_MIN_PIXELS: Final = 1.0

# 來源：domain.companion_animation_contract 與 scratchpad assemble_set；
# 量測：這些是執行期固定嘴框/眼框，單位為 465 空間像素。
MOUTH_CLIPS: Final = {
    "cheek": (168, 195, 64, 40),
    "lean": (158, 194, 62, 42),
    "front": (206, 199, 54, 35),
}
BLINK_RECTS: Final = {
    "cheek": ((160, 153, 55, 34), (198, 153, 61, 34)),
    "lean": ((153, 153, 55, 34), (191, 153, 61, 34)),
    "front": ((180, 153, 53, 34), (220, 153, 56, 34)),
}


@dataclass(frozen=True, slots=True)
class DiffParameters:
    """一個抽層步驟的差分、形態學與 alpha 參數。"""

    rgb_threshold: int
    open_kernel: int
    close_kernel: int
    soft_alpha_span: int


# 來源：scratchpad/layers/extract_layers.py；量測：L1 妝容保留低對比細線，
# 其餘步驟沿用原始 RGB/形態學設定，避免改變既有抽層結果。
DIFF_ALPHA_THRESHOLD: Final = 40
DIFF_FEATHER_PIXELS: Final = 3
STEP_PARAMETERS: Final = {
    "L1_makeup": DiffParameters(8, 0, 5, 40),
    "L2_garment": DiffParameters(22, 5, 9, 0),
    # On halfprod_front_A, open=5 left 2,807 measured forehead holes; open=3
    # left 1,463, while open=0 with the unchanged close=9 left 630 (79.1%
    # below the 3,013 packaged baseline).  Zero preserves one-pixel strands.
    "L3_hair": DiffParameters(22, 0, 9, 0),
    # The old 3-pixel opening erased the measured 4--39 px chain segments.
    # No opening preserves all four vertical chains; close=7 already bridges
    # anti-aliased gaps without merging neighbouring beads in the source scan.
    "L4_headwear": DiffParameters(16, 0, 7, 0),
}
STEPS: Final = tuple(STEP_PARAMETERS)

# 來源：scratchpad/layers/extract_layers.py；量測：邊緣 13 px 橢圓腐蝕帶、
# 既有去溢色判斷與 0.85 壓回比例，保留藍袍/紅唇不誤傷的原始分類。
DESPILL_INNER_EROSION_KERNEL: Final = 13
DESPILL_EDGE_SPILL_THRESHOLD: Final = 8
DESPILL_DARK_SPILL_THRESHOLD: Final = 14
DESPILL_DARK_GREEN_MAX: Final = 130
DESPILL_REDUCTION_FACTOR: Final = 0.85

# 來源：scratchpad/layers/extract_layers.py；量測：YuNet 五點推導出的臉部
# 安全區，數值是原腳本以雙眼距 d 為尺的橢圓半徑/偏移。
MAKEUP_EYE_CENTER_Y_FACTOR: Final = -0.12
MAKEUP_EYE_RADIUS_X_FACTOR: Final = 0.45
MAKEUP_EYE_RADIUS_Y_FACTOR: Final = 0.42
MAKEUP_CHEEK_CENTER_X_FACTOR: Final = 0.15
MAKEUP_CHEEK_CENTER_Y_FACTOR: Final = 0.75
MAKEUP_CHEEK_RADIUS_X_FACTOR: Final = 0.45
MAKEUP_CHEEK_RADIUS_Y_FACTOR: Final = 0.38
MAKEUP_LIP_RADIUS_X_FACTOR: Final = 0.55
MAKEUP_LIP_RADIUS_Y_FACTOR: Final = 0.32
DIFF_SOFT_BLUR_SIGMA: Final = 1.2

# 來源：scratchpad/layers/extract_layers.py；量測：相位相關只在未變動的
# silhouette ROI 估平移，保留原始的像素量與 fail-safe 位移上限。
REGISTER_HEAD_ROI_BOTTOM_RATIO: Final = 0.28
REGISTER_LOWER_ROI_TOP_RATIO: Final = 0.60
REGISTER_MIN_ALPHA_PIXELS: Final = 500
REGISTER_IGNORE_SHIFT_PIXELS: Final = 0.3
REGISTER_MAX_SHIFT_PIXELS: Final = 40.0

# 來源：scratchpad/layers/extract_layers.py；量測：鞋層只允許畫布下方，
# 0.90 以下為完整腳區，0.87--0.90 為裙襬邊界帶；60 px 為逐列補鞋的
# 最近鄰安全距離。
SHOE_UPPER_EXCLUSION_RATIO: Final = 0.78
SHOE_FOOT_ZONE_TOP_RATIO: Final = 0.90
SHOE_FOOT_BAND_TOP_RATIO: Final = 0.87
SHOE_NEAREST_MAX_DISTANCE: Final = 60
SHOE_BARE_ALPHA_MIN: Final = 128
SHOE_COVERED_ALPHA_MIN: Final = 200
SHOE_BLUE_RED_MARGIN: Final = 25
SHOE_BLUE_GREEN_MARGIN: Final = 10
BARE_SKIN_RED_MIN: Final = 150
BARE_SKIN_RED_GREEN_MARGIN: Final = 15
BARE_SKIN_GREEN_BLUE_MARGIN: Final = 5

# 來源：scratchpad/layers/extract_layers.py；量測：髮飾安全區、膚色/暗色
# 排除與連通塊門檻均沿用原始人工檢視通過的範圍。
HEAD_FALLBACK_TOP_RATIO: Final = 0.30
HEAD_REGION_BOTTOM_FACE_FACTOR: Final = 1.05
HEAD_REGION_LEFT_FACE_FACTOR: Final = 1.60
HEAD_REGION_RIGHT_FACE_FACTOR: Final = 2.60
HEAD_REGION_FACE_CUT_TOP_FACTOR: Final = 0.15
HEAD_REGION_FACE_CUT_LEFT_FACTOR: Final = 0.12
HEAD_REGION_FACE_CUT_BOTTOM_FACTOR: Final = 0.88
HEADWEAR_SKIN_RED_MIN: Final = 140
HEADWEAR_SKIN_RED_GREEN_MARGIN: Final = 10
HEADWEAR_SKIN_GREEN_BLUE_MARGIN: Final = 5
HEADWEAR_DARK_PIXEL_MAX: Final = 80
# The smallest visible silver-chain segment in halfprod_front_A is 4 px; the
# 1--3 px components in the same scan are isolated keying noise.  The old 40
# px threshold removed the chain while retaining its 76--341 px beads.
HEADWEAR_MIN_COMPONENT_AREA: Final = 4
# In the re-extracted front-crossed mask, a 20 px radius links the visible
# anti-aliased chain segments (maximum measured inter-segment gap <= 40 px),
# while the remaining cluster >100 px away is the measured y=632 extraction
# speck.  Apply that same geometric rule to every silhouette.
HEADWEAR_CHAIN_LINK_RADIUS: Final = 20
HEADWEAR_DETACHED_DISTANCE: Final = 100

# The release portrait baseline contains 7,457 warm forehead pixels under this
# exact owner-supplied criterion; 3,923 are fully opaque outfit-hair pixels.
# Their luminance is preserved while chroma is neutralized in extraction, so
# the correction removes under-layer skin colour without inventing highlights.
HAIR_SPILL_BRIGHTNESS_MIN: Final = 70
HAIR_SPILL_BRIGHTNESS_MAX: Final = 150
HAIR_SPILL_RED_BLUE_MARGIN: Final = 18
# The permissive open=0 mask above recovers the missing forehead mass for the
# back slot.  A measured 5/3/0 opening scan left 2,807/1,463/630 candidate holes;
# 3 recovers fine strands while still rejecting the garment/facial drift seen at 0.
HAIR_FRONT_OPEN_KERNEL: Final = 3
# Keep the measured legacy 5 px opening below the fine-strand band: using 3
# globally painted hair onto the sealed front-crossed garment probe (610,853).
HAIR_BODY_OPEN_KERNEL: Final = 5
# The owner's measured forehead ROI ends at y=470 on a 1,254 px canvas
# (37.48%).  Rounding the fine-strand band to 38% includes that whole ROI while
# leaving the y=853 garment probe under the legacy 5 px opening.
HAIR_FINE_REGION_BOTTOM_RATIO: Final = 0.38

# 來源：scratchpad/layers/extract_layers.py；量測：既有對照表尺寸與暗底
# 顏色，僅影響證據圖，不影響產出層像素。
SHEET_TILE_WIDTH: Final = 300
SHEET_TILE_HEIGHT: Final = 450
SHEET_TILE_GAP: Final = 10
SHEET_BACKGROUND_BGR: Final = (36, 28, 28)
RECONSTRUCTION_ERROR_PIXEL_THRESHOLD: Final = 24

# 來源：scratchpad/layers/make_ref_crops.py；量測：無臉剪影與 YuNet 臉框
# 的裁切比例，保留原始局部參考的安全邊界。
SILHOUETTE_HEAD_HEIGHT_RATIO: Final = 0.11
SILHOUETTE_HEAD_Y_RATIO: Final = 0.35
SILHOUETTE_BODY_START_RATIO: Final = 0.16
SILHOUETTE_HEAD_LEFT_MULTIPLIER: Final = 1.0
SILHOUETTE_HEAD_RIGHT_MULTIPLIER: Final = 2.0
REF_HEAD_TOP_FACE_FACTOR: Final = 1.60
REF_HEAD_BOTTOM_FACE_FACTOR: Final = 0.15
REF_HEAD_LEFT_FACE_FACTOR: Final = 1.0
REF_HEAD_RIGHT_FACE_FACTOR: Final = 2.0
REF_FACE_TOP_FACTOR: Final = 0.35
REF_FACE_BOTTOM_FACTOR: Final = 1.15
REF_FACE_LEFT_FACTOR: Final = 0.35
REF_FACE_RIGHT_FACTOR: Final = 1.35

# 來源：scratchpad/layers/extract_layers.py 與官方 makeup-safe-regions 契約；
# 量測：優先順序確保重疊安全區只有一個槽取得像素。
MAKEUP_SLOT_PRIORITY: Final = ("eyes", "lips", "cheeks")
HALF_SILHOUETTES: Final = {
    "front": "front-crossed",
    "cheek": "cheek-rest",
    "lean": "left-neutral",
    "mock_scold": "front-mock-scold",
    "mock_hit_front": "front-mock-hit",
    "eureka_front": "front-eureka",
    "exasperated_front": "front-exasperated",
}
