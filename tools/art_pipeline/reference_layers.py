"""以 v4 樣式參考圖為來源抽出前髮與髮飾層。

差分抽層（``extract_layers``）只保留「與上一層不同」的像素，而第二代半身
渲染的前額垂髮本來就比 v4 原圖稀疏，所以不論差分做得多乾淨，鬢角都會露出
底下的皮膚，看起來像空心；髮飾的冠飾與流蘇結構也跟 v4 不同。擁有者 2026-09-05
裁決：頭髮與髮飾一律以 v4 原圖為準。

做法：用 YuNet 五點把對齊過的 v4 參考圖以相似變換（等比縮放＋平移）貼到素體
座標，再依顏色規則直接取參考圖像素——

* 髮飾：亮而低飽和（銀）限制在眉上區與右側流蘇欄；偏藍的珠飾只在流蘇欄
  （髮髻上的藍黑髮絲高光也偏藍，不能在髮髻區收藍色）。
* 頭髮：深色低飽和、或藍黑髮絲高光；排除臉核心、暖色皮膚（不論亮暗）、肩線
  以下的藍色布料；額頭橢圓內只收極暗像素。被「頭髮＋髮飾」包住的洞一律用
  參考圖的髮色像素補實（那是髮髻與冠飾內側），髮飾本身不進髮層，換髮飾時
  髮層在冠飾處留洞，與差分抽層的語意一致。

所有門檻集中在本模組頂端；量測依據寫在各常數旁。
"""

from __future__ import annotations

lazy import cv2
lazy import numpy as np
lazy from dataclasses import dataclass
lazy from pathlib import Path

lazy from .image_ops import key_file
lazy from .vision import face_landmarks

# 對齊：五點相似變換後，五點的最大殘差超過此值就視為對齊失敗（2026-09-05
# 量測：正面半身 3.65 px、各 yaw 全身 2–6 px）。
REFERENCE_ALIGN_MAX_ERROR_PX: float = 14.0
# 比例合理範圍：參考圖與素體同尺寸（全身模板）時約 1.0–1.16；半身畫布約 2.27–2.46。
# 超出範圍代表五點偵測錯位（2026-09-05：yaw-105 誤測成 0.586），一律視為對齊失敗。
REFERENCE_SCALE_RANGE_SAME_SIZE: tuple[float, float] = (0.85, 1.35)
REFERENCE_SCALE_RANGE_HALF_BODY: tuple[float, float] = (2.0, 2.7)
# 頭髮：max(RGB) 在 HAIR_DARK_FULL 以下為完全不透明，往上到 HAIR_DARK_ZERO 線性
# 遞減到 0；v4 髮色 max(RGB) 多在 20–70，皮膚陰影 90 以上。
HAIR_DARK_FULL: int = 50
HAIR_DARK_ZERO: int = 115
HAIR_SATURATION_MAX: int = 60
# 藍黑髮絲高光：藍分量高於紅分量、整體不亮；只在既有髮量附近採計。
HAIR_HIGHLIGHT_BLUE_MARGIN: int = 15
HAIR_HIGHLIGHT_BRIGHTNESS_MAX: int = 175
# 高光只在「深色髮量經 25 px 閉運算」的範圍內採計，藍色珠飾離髮量遠，不會被吃進來。
HAIR_HIGHLIGHT_CLOSE_KERNEL: int = 25
# 額頭橢圓（以眼距為單位）內只收 max(RGB) < HAIR_FOREHEAD_DARK_MAX 的像素，避免把
# 髮際線的皮膚陰影當成頭髮。
HAIR_FOREHEAD_DARK_MAX: int = 55
HAIR_FOREHEAD_CENTER_Y_FACTOR: float = -0.30
HAIR_FOREHEAD_RADIUS_X_FACTOR: float = 1.10
HAIR_FOREHEAD_RADIUS_Y_FACTOR: float = 0.85
# 臉核心橢圓：眉眼口一律排除，避免眉毛與眼線被當成頭髮。
FACE_CORE_CENTER_Y_FACTOR: float = 0.55
FACE_CORE_RADIUS_X_FACTOR: float = 0.95
FACE_CORE_RADIUS_Y_FACTOR: float = 1.35
# 皮膚：紅分量明顯高於藍分量就是暖色，不論亮暗都不是 v4 的藍黑頭髮。
SKIN_WARM_MARGIN: int = 12
# 衣領等藍色布料只在肩線以下排除（肩線＝眼睛下 2 倍眼距）；衣袍的暗部飽和度與藍黑
# 髮絲高光重疊，單靠顏色分不開（2026-09-05 量測：改用飽和度規則後髮層吃進整片袍褶）。
GARMENT_BLUE_MARGIN: int = 25
GARMENT_BLUE_MIN: int = 60
GARMENT_TOP_EYE_FACTOR: float = 2.0
# 全身參考圖（與素體同尺寸）的頭髮只到眼睛以下 4.5 倍眼距，再往下是裙襬陰影；
# 半身畫布不切，髮尾自然落在畫布內。
HAIR_BOTTOM_EYE_FACTOR: float = 4.5
# 姿勢遮擋物：舉起的手掌、手臂在這個姿勢的第二代髮層渲染裡是皮膚，而在正面中性
# 渲染（或下巴線以下的 v4 參考圖）同位置不是皮膚；這些像素在 v4 頭髮之前，髮層與
# 髮飾層都要讓開。
OCCLUDER_MIN_COMPONENT_AREA: int = 300
OCCLUDER_DILATE_PX: int = 3
OCCLUDER_CHIN_EYE_FACTOR: float = 1.6
OCCLUDER_SKIN_BRIGHTNESS_MIN: int = 90
HAIR_MIN_COMPONENT_AREA: int = 400
HAIR_EDGE_SUPPORT_KERNEL: int = 5
# 漸層 alpha 超過此值視為實心頭髮（用來找大塊與封閉洞）。
HAIR_SOLID_GRADE: float = 0.5
# 髮飾：銀色＝亮且低飽和；珠飾＝藍分量明顯高於紅且夠亮。
ORNAMENT_SILVER_MIN: int = 150
ORNAMENT_SILVER_SATURATION_MAX: int = 45
ORNAMENT_BLUE_MARGIN: int = 30
ORNAMENT_BLUE_MIN: int = 90
ORNAMENT_BROW_LINE_EYE_FACTOR: float = -0.60
ORNAMENT_TASSEL_TOP_EYE_FACTOR: float = -2.8
# 流蘇底端珠穗在眼睛上方約 0.25 倍眼距處結束；欄位再往下就是 v4 衣袍肩部的銀線刺繡
# （2026-09-05 量測：欄底設 1.2 時肩部混進三塊 43–73 px 的刺繡碎片）。
ORNAMENT_TASSEL_BOTTOM_EYE_FACTOR: float = 0.2
ORNAMENT_TASSEL_LEFT_EYE_FACTOR: float = 1.4
ORNAMENT_TASSEL_RIGHT_EYE_FACTOR: float = 2.8
ORNAMENT_MIN_COMPONENT_AREA: int = 40
ORNAMENT_FEATHER_PX: float = 1.5
# 髮飾周圍的深色描邊在 v4 原圖裡是飾品的一部分，不採計為頭髮。
ORNAMENT_HALO_PX: int = 7
# 流蘇欄內、緊貼銀／藍像素的深色描邊收進髮飾層（2026-09-05 量測：只收亮芯時流蘇
# 中段寬 10 px，原圖帶狀含描邊約 16 px）。
ORNAMENT_OUTLINE_PX: int = 5
ORNAMENT_OUTLINE_DARK_MAX: int = 90
# 流蘇欄內、中等亮度的低飽和灰是銀帶的陰影面（2026-09-05 量測：v4 對位後本體每列
# 非透明寬度中位數 22 px，只收亮芯與描邊時剩 11 px）。
ORNAMENT_TASSEL_SHADE_MIN: int = 60
ORNAMENT_TASSEL_SHADE_SATURATION_MAX: int = 60
# 陰影面規則只在流蘇本體所在的窄欄採計，避免把左側垂髮邊緣的灰藍像素收進髮飾層。
ORNAMENT_TASSEL_SHADE_LEFT_EYE_FACTOR: float = 1.55
# 陰影面與描邊還必須緊貼銀色亮芯（亮芯膨脹 9 px 內）：垂髮與流蘇在 x 上重疊時，
# 窄欄邊界會在髮層留下垂直直線切口（2026-09-05 量測：x=761 連續 53 px）。
ORNAMENT_CORE_REACH_PX: int = 9
# 髮飾遮住的頭髮：v4 原圖裡流蘇緊貼垂髮，被遮住的頭髮在參考圖不存在，髮層在那裡會
# 出現沿著流蘇邊的直線切口（2026-09-05 量測：x=762 連續 56 px）。緊鄰髮量
# HAIR_UNDER_ORNAMENT_REACH_PX 內的髮飾區域用周圍髮色補繪進髮層，髮飾層照常蓋在上面。
# 補繪要一路延伸到流蘇遠側（流蘇寬約 24 px、離髮量最多約 10 px），否則直線邊只是
# 從髮量邊移到補繪邊（2026-09-05 量測：reach 13 時 exasperated 仍有 63 px 直線邊）。
HAIR_UNDER_ORNAMENT_REACH_PX: int = 41
HAIR_EXTENSION_EDGE_ALPHA_MIN: int = 250
# 流蘇與垂髮之間在 v4 原圖有 2–3 px 的背景縫，補繪範圍把髮飾再外擴幾像素以蓋住這條縫。
HAIR_UNDER_ORNAMENT_GAP_PX: int = 17
# 垂髮邊緣從眼睛上方 1.6 倍眼距開始往下延伸；再往上是蝴蝶飾與小墜，可用整個流蘇欄。
ORNAMENT_TASSEL_HAIR_TOP_EYE_FACTOR: float = -1.6


@dataclass(frozen=True, slots=True)
class ReferenceAlignment:
    scale: float
    translation: tuple[float, float]
    max_error_px: float
    eye_distance: float
    eye_center: tuple[float, float]


def align_reference_to_base(
    base: np.ndarray,
    reference: np.ndarray,
    model_path: Path,
) -> tuple[np.ndarray, ReferenceAlignment]:
    """用五點相似變換把參考圖貼到素體座標；回傳貼好的 RGBA 與對齊報告。"""
    base_points, _ = face_landmarks(base, model_path)
    reference_points, _ = face_landmarks(reference, model_path)
    base_eyes = float(np.hypot(*(base_points[1] - base_points[0])))
    reference_eyes = float(np.hypot(*(reference_points[1] - reference_points[0])))
    scale = base_eyes / reference_eyes
    base_center = (base_points[0] + base_points[1]) / 2.0
    reference_center = (reference_points[0] + reference_points[1]) / 2.0
    translation = base_center - scale * reference_center
    matrix = np.array(
        [[scale, 0.0, translation[0]], [0.0, scale, translation[1]]], np.float32
    )
    warped = cv2.warpAffine(
        reference,
        matrix,
        (base.shape[1], base.shape[0]),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=(0, 0, 0, 0),
    )
    projected = scale * reference_points + translation
    error = float(np.abs(projected - base_points).max())
    return warped, ReferenceAlignment(
        scale,
        (float(translation[0]), float(translation[1])),
        error,
        base_eyes,
        (float(base_center[0]), float(base_center[1])),
    )


def _ellipse(
    shape: tuple[int, int],
    center: tuple[float, float],
    radii: tuple[float, float],
) -> np.ndarray:
    mask = np.zeros(shape, np.uint8)
    cv2.ellipse(
        mask,
        (int(center[0]), int(center[1])),
        (max(1, int(radii[0])), max(1, int(radii[1]))),
        0,
        0,
        360,
        1,
        -1,
    )
    return mask.astype(bool)


def _keep_large_components(mask: np.ndarray, minimum_area: int) -> np.ndarray:
    count, labels, stats, _ = cv2.connectedComponentsWithStats(
        mask.astype(np.uint8), 8
    )
    keep = np.zeros(mask.shape, np.uint8)
    for index in range(1, count):
        if stats[index, cv2.CC_STAT_AREA] >= minimum_area:
            keep[labels == index] = 1
    return keep


def _enclosed_holes(solid: np.ndarray) -> np.ndarray:
    """回傳被 ``solid`` 完全包住（碰不到畫布邊緣）的洞。"""
    inverse = (~solid).astype(np.uint8)
    _count, labels, _stats, _centroids = cv2.connectedComponentsWithStats(inverse, 4)
    border = np.unique(
        np.concatenate((labels[0, :], labels[-1, :], labels[:, 0], labels[:, -1]))
    )
    return np.isin(labels, border, invert=True) & (labels > 0)


def _ornament_zone(shape: tuple[int, int], alignment: ReferenceAlignment) -> tuple[np.ndarray, np.ndarray]:
    """回傳（眉上區, 流蘇欄）兩個布林區域。"""
    height, width = shape
    eye_distance = alignment.eye_distance
    center_x, eye_y = alignment.eye_center
    brow = np.zeros((height, width), bool)
    brow[: max(0, int(eye_y + ORNAMENT_BROW_LINE_EYE_FACTOR * eye_distance)), :] = True
    tassel = np.zeros((height, width), bool)
    tassel[
        max(0, int(eye_y + ORNAMENT_TASSEL_TOP_EYE_FACTOR * eye_distance)) : int(
            eye_y + ORNAMENT_TASSEL_BOTTOM_EYE_FACTOR * eye_distance
        ),
        int(center_x + ORNAMENT_TASSEL_LEFT_EYE_FACTOR * eye_distance) : int(
            center_x + ORNAMENT_TASSEL_RIGHT_EYE_FACTOR * eye_distance
        ),
    ] = True
    return brow, tassel


def ornament_mask(warped: np.ndarray, alignment: ReferenceAlignment) -> np.ndarray:
    """髮飾的實心遮罩（uint8 0/1）：銀色在眉上區或流蘇欄，藍色珠飾只在流蘇欄。"""
    rgb = warped[:, :, :3].astype(np.int16)
    alpha = warped[:, :, 3]
    brightest = rgb.max(axis=2)
    saturation = brightest - rgb.min(axis=2)
    brow, tassel = _ornament_zone(warped.shape[:2], alignment)
    # 銀是中性或偏冷；亮而低飽和的暖色是額頭皮膚，不是飾品。
    warm = rgb[:, :, 2] > rgb[:, :, 0] + SKIN_WARM_MARGIN
    silver = (
        (brightest > ORNAMENT_SILVER_MIN)
        & (saturation < ORNAMENT_SILVER_SATURATION_MAX)
        & ~warm
    )
    bluish = (rgb[:, :, 0] > rgb[:, :, 2] + ORNAMENT_BLUE_MARGIN) & (
        rgb[:, :, 0] > ORNAMENT_BLUE_MIN
    )
    # 流蘇欄的左段在垂髮邊緣以下會碰到頭髮：藍色珠飾、陰影面與描邊只在「本體窄欄」
    # 或「垂髮邊緣以上（蝴蝶飾所在）」採計。
    center_x, eye_y = alignment.eye_center
    narrow = tassel.copy()
    narrow[
        int(eye_y + ORNAMENT_TASSEL_HAIR_TOP_EYE_FACTOR * alignment.eye_distance) :,
        : int(center_x + ORNAMENT_TASSEL_SHADE_LEFT_EYE_FACTOR * alignment.eye_distance),
    ] = False
    core = ((silver | bluish) & narrow & (alpha > 0)).astype(np.uint8)
    near_core = cv2.dilate(
        core, np.ones((ORNAMENT_CORE_REACH_PX, ORNAMENT_CORE_REACH_PX), np.uint8)
    ).astype(bool)
    shade = (
        (brightest >= ORNAMENT_TASSEL_SHADE_MIN)
        & (saturation < ORNAMENT_TASSEL_SHADE_SATURATION_MAX)
        & ~warm
        & near_core
    )
    candidate = ((silver & (brow | tassel)) | (bluish & narrow) | shade) & (alpha > 0)
    # 流蘇本體與珠飾在 v4 原圖有深色描邊；描邊緊貼銀／藍亮芯，只在亮芯附近收回，
    # 讓流蘇維持原圖的帶狀寬度而不是只剩亮芯。
    outline = (
        cv2.dilate(
            candidate.astype(np.uint8),
            np.ones((ORNAMENT_OUTLINE_PX, ORNAMENT_OUTLINE_PX), np.uint8),
        ).astype(bool)
        & (brightest < ORNAMENT_OUTLINE_DARK_MAX)
        & near_core
        & (alpha > 0)
    )
    return _keep_large_components(candidate | outline, ORNAMENT_MIN_COMPONENT_AREA)


def _hair_exclusions(
    warped: np.ndarray,
    alignment: ReferenceAlignment,
    ornament: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """回傳（一律排除, 額頭橢圓, 暖色皮膚）三個布林遮罩。"""
    height, width = warped.shape[:2]
    rgb = warped[:, :, :3].astype(np.int16)
    eye_distance = alignment.eye_distance
    center_x, eye_y = alignment.eye_center
    face_core = _ellipse(
        (height, width),
        (center_x, eye_y + FACE_CORE_CENTER_Y_FACTOR * eye_distance),
        (FACE_CORE_RADIUS_X_FACTOR * eye_distance, FACE_CORE_RADIUS_Y_FACTOR * eye_distance),
    )
    forehead = _ellipse(
        (height, width),
        (center_x, eye_y + HAIR_FOREHEAD_CENTER_Y_FACTOR * eye_distance),
        (HAIR_FOREHEAD_RADIUS_X_FACTOR * eye_distance, HAIR_FOREHEAD_RADIUS_Y_FACTOR * eye_distance),
    )
    warm_skin = rgb[:, :, 2] > rgb[:, :, 0] + SKIN_WARM_MARGIN
    garment_blue = (rgb[:, :, 0] > rgb[:, :, 2] + GARMENT_BLUE_MARGIN) & (
        rgb[:, :, 0] > GARMENT_BLUE_MIN
    )
    garment_blue[: int(eye_y + GARMENT_TOP_EYE_FACTOR * eye_distance), :] = False
    excluded = (
        face_core | warm_skin | garment_blue | ornament.astype(bool) | (warped[:, :, 3] == 0)
    )
    return excluded, forehead, warm_skin


def _warm_skin(image: np.ndarray) -> np.ndarray:
    rgb = image[:, :, :3].astype(np.int16)
    return (
        (rgb[:, :, 2] > rgb[:, :, 0] + SKIN_WARM_MARGIN)
        & (rgb.max(axis=2) > OCCLUDER_SKIN_BRIGHTNESS_MIN)
        & (image[:, :, 3] > 0)
    )


def pose_occluder_mask(
    pose_render: np.ndarray,
    neutral_render: np.ndarray | None,
    warped: np.ndarray,
    alignment: ReferenceAlignment,
) -> np.ndarray:
    """舉起的手掌、手臂等在 v4 頭髮之前的遮擋物（uint8 0/1）。

    兩個來源取聯集：這個姿勢的渲染是皮膚而正面中性渲染同位置不是（手舉到臉旁）；
    下巴線以下這個姿勢是皮膚而 v4 參考圖同位置不是（交叉的手臂）。鬢角在中性渲染
    與本姿勢都是皮膚，不會被當成遮擋物。
    """
    pose_skin = _warm_skin(pose_render)
    candidate = np.zeros(pose_skin.shape, bool)
    if neutral_render is not None:
        candidate |= pose_skin & ~_warm_skin(neutral_render)
    below_chin = np.zeros(pose_skin.shape, bool)
    below_chin[int(alignment.eye_center[1] + OCCLUDER_CHIN_EYE_FACTOR * alignment.eye_distance) :, :] = True
    candidate |= pose_skin & ~_warm_skin(warped) & below_chin
    kept = _keep_large_components(candidate, OCCLUDER_MIN_COMPONENT_AREA)
    return cv2.dilate(kept, np.ones((OCCLUDER_DILATE_PX, OCCLUDER_DILATE_PX), np.uint8))


def _apply_occluder(layer: np.ndarray, occluder: np.ndarray) -> tuple[np.ndarray, int]:
    output = layer.copy()
    hit = occluder.astype(bool) & (output[:, :, 3] > 0)
    output[hit] = 0
    return output, int(hit.sum())


def reference_hair_layer(
    warped: np.ndarray,
    alignment: ReferenceAlignment,
    ornament: np.ndarray,
    full_body: bool = False,
) -> tuple[np.ndarray, dict[str, int]]:
    """從貼好的參考圖取前髮層（RGBA）；``ornament`` 是髮飾遮罩，用來封洞但不入髮層。"""
    rgb = warped[:, :, :3].astype(np.int16)
    alpha = warped[:, :, 3]
    brightest = rgb.max(axis=2)
    saturation = brightest - rgb.min(axis=2)
    excluded, forehead, warm_skin = _hair_exclusions(warped, alignment, ornament)
    # 髮飾的深色描邊不是頭髮：髮飾周圍 ORNAMENT_HALO_PX 內不採計，但封洞時仍可補回
    # 緊貼冠飾的髮髻像素。
    halo = cv2.dilate(
        ornament, np.ones((ORNAMENT_HALO_PX, ORNAMENT_HALO_PX), np.uint8)
    ).astype(bool)
    grade = np.clip(
        (HAIR_DARK_ZERO - brightest.astype(np.float32))
        / float(HAIR_DARK_ZERO - HAIR_DARK_FULL),
        0.0,
        1.0,
    )
    grade *= saturation < HAIR_SATURATION_MAX
    grade[excluded | halo] = 0.0
    grade[forehead & (brightest >= HAIR_FOREHEAD_DARK_MAX)] = 0.0
    solid = _keep_large_components(grade > HAIR_SOLID_GRADE, HAIR_MIN_COMPONENT_AREA)
    # 藍黑髮絲高光只在深色髮量閉運算後的範圍內採計。
    highlight_zone = cv2.morphologyEx(
        solid,
        cv2.MORPH_CLOSE,
        cv2.getStructuringElement(
            cv2.MORPH_ELLIPSE, (HAIR_HIGHLIGHT_CLOSE_KERNEL, HAIR_HIGHLIGHT_CLOSE_KERNEL)
        ),
    ).astype(bool)
    highlight = (
        (rgb[:, :, 0] > rgb[:, :, 2] + HAIR_HIGHLIGHT_BLUE_MARGIN)
        & (brightest < HAIR_HIGHLIGHT_BRIGHTNESS_MAX)
        & highlight_zone
        & ~excluded
    )
    grade[highlight] = 1.0
    support = cv2.dilate(
        (grade > HAIR_SOLID_GRADE).astype(np.uint8),
        np.ones((HAIR_EDGE_SUPPORT_KERNEL, HAIR_EDGE_SUPPORT_KERNEL), np.uint8),
    ).astype(bool)
    grade *= support
    # 封洞只補「髮色」像素：臉被頭髮包住時也是洞，但皮膚是暖色，不能補進髮層。
    enclosure = (grade > HAIR_SOLID_GRADE) | ornament.astype(bool)
    hair_like = ~warm_skin & (brightest < HAIR_HIGHLIGHT_BRIGHTNESS_MAX)
    holes = _enclosed_holes(enclosure) & hair_like & ~excluded
    grade[holes] = 1.0
    if full_body:
        grade[int(alignment.eye_center[1] + HAIR_BOTTOM_EYE_FACTOR * alignment.eye_distance) :, :] = 0.0
    layer = warped.copy()
    layer[:, :, 3] = np.rint(grade * alpha).astype(np.uint8)
    solid_hair = grade > HAIR_SOLID_GRADE
    under = _hair_under_ornament(solid_hair, ornament, halo, excluded, alpha, alignment)
    if under.any():
        # 延伸起點要取「參考圖本身也完全不透明」的髮緣，否則髮緣抗鋸齒的低 alpha 尾巴
        # 會夾在髮量與延伸段之間，封裝時被低 alpha 清理挖成一條直線縫。
        layer = _extend_hair_rightwards(
            layer, solid_hair & (alpha >= HAIR_EXTENSION_EDGE_ALPHA_MIN), under
        )
    layer[layer[:, :, 3] == 0] = 0
    return layer, {
        "opaque_pixels": int((layer[:, :, 3] > 0).sum()),
        "filled_hole_pixels": int(holes.sum()),
        "under_ornament_pixels": int(under.sum()),
    }


def _hair_under_ornament(
    solid: np.ndarray,
    ornament: np.ndarray,
    halo: np.ndarray,
    excluded: np.ndarray,
    alpha: np.ndarray,
    alignment: ReferenceAlignment,
) -> np.ndarray:
    """流蘇欄內、緊鄰髮量的髮飾（含描邊與背景縫）區域，之後用左側髮色延伸成被遮住的頭髮。

    只處理流蘇欄：冠飾下的髮髻已由封洞規則補實，不需要也不該延伸。
    """
    reach = cv2.dilate(
        solid.astype(np.uint8),
        np.ones((HAIR_UNDER_ORNAMENT_REACH_PX, HAIR_UNDER_ORNAMENT_REACH_PX), np.uint8),
    ).astype(bool)
    covered = cv2.dilate(
        (ornament.astype(bool) | halo).astype(np.uint8),
        np.ones((HAIR_UNDER_ORNAMENT_GAP_PX, HAIR_UNDER_ORNAMENT_GAP_PX), np.uint8),
    ).astype(bool)
    _brow, tassel = _ornament_zone(solid.shape, alignment)
    # 髮飾以外的排除（臉核心、皮膚、衣袍）不補；髮飾本身與透明的背景縫才補。
    other_exclusions = excluded & ~ornament.astype(bool) & (alpha > 0)
    return covered & reach & tassel & ~other_exclusions


def _extend_hair_rightwards(layer: np.ndarray, solid: np.ndarray, under: np.ndarray) -> np.ndarray:
    """把髮量向右延伸到流蘇遠側，填進 ``under`` 所在的列。

    每一列從最靠右的髮像素起、一路填到該列 ``under`` 的最右欄（連背景縫一起補），
    像素以髮緣為軸鏡射取樣，保留近乎垂直的髮絲紋理。
    """
    height, width = solid.shape
    columns = np.arange(width)[None, :]
    last_hair = np.maximum.accumulate(np.where(solid, columns, 0), axis=1)
    row_has_under = under.any(axis=1)
    right_limit = np.where(under, columns, -1).max(axis=1)
    output = layer.copy()
    for row in np.nonzero(row_has_under)[0]:
        edge = int(last_hair[row, right_limit[row]])
        if edge <= 0 or right_limit[row] - edge > HAIR_UNDER_ORNAMENT_REACH_PX:
            continue
        cols = np.arange(edge + 1, right_limit[row] + 1)
        source = np.clip(2 * edge - cols, 0, edge)
        source = np.where(solid[row, source], source, edge)
        output[row, cols, :3] = layer[row, source, :3]
        output[row, cols, 3] = 255
    return output


def reference_headwear_layer(
    warped: np.ndarray, ornament: np.ndarray
) -> tuple[np.ndarray, dict[str, int]]:
    """從貼好的參考圖取髮飾層（冠飾、簪頭珠飾、流蘇）。"""
    alpha = warped[:, :, 3]
    distance = cv2.distanceTransform(ornament, cv2.DIST_L2, 3)
    grade = np.clip(distance / ORNAMENT_FEATHER_PX, 0.0, 1.0)
    layer = warped.copy()
    layer[:, :, 3] = np.rint(grade * alpha).astype(np.uint8)
    layer[layer[:, :, 3] == 0] = 0
    return layer, {"opaque_pixels": int((layer[:, :, 3] > 0).sum())}


def extract_reference_layers(
    base: np.ndarray,
    reference_path: Path,
    model_path: Path,
    pose_render_path: Path | None = None,
    neutral_render_path: Path | None = None,
) -> tuple[np.ndarray, np.ndarray, dict[str, object]] | None:
    """對齊參考圖並抽出（前髮層, 髮飾層, 報告）；對齊失敗回傳 None。

    ``pose_render_path`` 是這個姿勢的第二代髮層渲染（含手勢），``neutral_render_path``
    是正面中性姿勢的同一層；兩者用來找出在 v4 頭髮之前的手掌與手臂。
    """
    # 參考圖是洋紅底：去背即可，不做去色溢（本模組的顏色規則本來就排除高飽和像素）。
    reference = key_file(reference_path)
    try:
        warped, alignment = align_reference_to_base(base, reference, model_path)
    except ValueError:
        return None
    if alignment.max_error_px > REFERENCE_ALIGN_MAX_ERROR_PX:
        return None
    low, high = (
        REFERENCE_SCALE_RANGE_SAME_SIZE
        if base.shape[:2] == reference.shape[:2]
        else REFERENCE_SCALE_RANGE_HALF_BODY
    )
    if not low <= alignment.scale <= high:
        return None
    full_body = base.shape[:2] == reference.shape[:2]
    ornament = ornament_mask(warped, alignment)
    hair, hair_report = reference_hair_layer(warped, alignment, ornament, full_body)
    headwear, headwear_report = reference_headwear_layer(warped, ornament)
    occluded_pixels = {"hair": 0, "headwear": 0}
    if pose_render_path is not None and pose_render_path.is_file():
        pose_render = key_file(pose_render_path)
        neutral_render = (
            key_file(neutral_render_path)
            if neutral_render_path is not None and neutral_render_path.is_file()
            else None
        )
        if pose_render.shape[:2] == base.shape[:2] and (
            neutral_render is None or neutral_render.shape[:2] == base.shape[:2]
        ):
            occluder = pose_occluder_mask(pose_render, neutral_render, warped, alignment)
            hair, occluded_pixels["hair"] = _apply_occluder(hair, occluder)
            headwear, occluded_pixels["headwear"] = _apply_occluder(headwear, occluder)
    report: dict[str, object] = {
        "occluded_pixels": occluded_pixels,
        "reference": reference_path.name,
        "alignment": {
            "scale": round(alignment.scale, 4),
            "translation_px": [
                round(alignment.translation[0], 1),
                round(alignment.translation[1], 1),
            ],
            "max_landmark_error_px": round(alignment.max_error_px, 2),
        },
        "hair": hair_report,
        "headwear": headwear_report,
    }
    return hair, headwear, report
