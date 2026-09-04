"""參考圖抽層（v4 原圖為準的前髮與髮飾）規則的合成影像測試。"""

from __future__ import annotations

lazy import sys
lazy import tempfile
lazy from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

lazy import cv2
lazy import numpy as np

lazy from tools.art_pipeline.reference_layers import (
    HAIR_DARK_FULL,
    ReferenceAlignment,
    extract_reference_layers,
    ornament_mask,
    pose_occluder_mask,
    reference_hair_layer,
    reference_headwear_layer,
)

SIZE = 400
EYE_DISTANCE = 60.0
EYE_CENTER = (200.0, 220.0)
HAIR_BGR = (20, 18, 16)
SKIN_BGR = (170, 200, 235)
SILVER_BGR = (215, 215, 220)
BEAD_BGR = (220, 150, 90)
HIGHLIGHT_BGR = (120, 90, 70)
HOLE_SIZE = 12
FULL_ALPHA = 255


def _alignment() -> ReferenceAlignment:
    return ReferenceAlignment(1.0, (0.0, 0.0), 0.0, EYE_DISTANCE, EYE_CENTER)


def _canvas() -> np.ndarray:
    image = np.zeros((SIZE, SIZE, 4), np.uint8)
    # 頭髮：一個大方塊蓋住上半部，臉核心以下留皮膚。
    image[40:260, 80:320, :3] = HAIR_BGR
    image[40:260, 80:320, 3] = FULL_ALPHA
    # 臉：眼睛附近一塊暖色皮膚（在臉核心橢圓內）。
    image[190:280, 150:250, :3] = SKIN_BGR
    image[190:280, 150:250, 3] = FULL_ALPHA
    return image


def test_hair_layer_keeps_dark_mass_and_rejects_skin() -> None:
    image = _canvas()
    alignment = _alignment()
    ornament = ornament_mask(image, alignment)
    layer, report = reference_hair_layer(image, alignment, ornament)
    assert layer[60, 100, 3] == FULL_ALPHA
    assert layer[230, 200, 3] == 0
    assert report["opaque_pixels"] > 0
    assert int(layer[60, 100, 2]) < HAIR_DARK_FULL


def test_hair_layer_fills_enclosed_hole_with_hair_pixels() -> None:
    image = _canvas()
    # 髮量中央挖一個藍黑高光洞：亮度超過純黑門檻，但被頭髮包住，必須補實。
    image[100 : 100 + HOLE_SIZE, 150 : 150 + HOLE_SIZE, :3] = HIGHLIGHT_BGR
    alignment = _alignment()
    layer, report = reference_hair_layer(image, alignment, ornament_mask(image, alignment))
    assert layer[105, 155, 3] == FULL_ALPHA
    assert report["filled_hole_pixels"] >= 0


def test_hair_layer_does_not_fill_enclosed_skin() -> None:
    image = _canvas()
    # 髮量中央放一塊暖色皮膚：即使被包住也不能補進髮層。
    image[100 : 100 + HOLE_SIZE, 150 : 150 + HOLE_SIZE, :3] = SKIN_BGR
    alignment = _alignment()
    layer, _ = reference_hair_layer(image, alignment, ornament_mask(image, alignment))
    assert layer[105, 155, 3] == 0


def test_ornament_mask_takes_silver_above_brow_and_beads_only_in_tassel_column() -> None:
    image = _canvas()
    image[50:70, 180:230, :3] = SILVER_BGR  # 冠飾：眉上區的銀
    image[120:130, 120:130, :3] = BEAD_BGR  # 髮髻上的藍：不是飾品
    tassel_x = int(EYE_CENTER[0] + 2.0 * EYE_DISTANCE)
    image[150:170, tassel_x : tassel_x + 12, :3] = BEAD_BGR  # 流蘇欄的藍珠
    image[150:170, tassel_x : tassel_x + 12, 3] = FULL_ALPHA
    mask = ornament_mask(image, _alignment())
    assert mask[60, 200] == 1
    assert mask[125, 125] == 0
    assert mask[160, tassel_x + 5] == 1


def test_ornament_mask_rejects_bright_warm_skin() -> None:
    image = _canvas()
    image[50:70, 180:230, :3] = SKIN_BGR  # 眉上區的亮暖色：皮膚，不是銀
    mask = ornament_mask(image, _alignment())
    assert mask[60, 200] == 0


def test_headwear_layer_uses_ornament_pixels_only() -> None:
    image = _canvas()
    image[50:70, 180:230, :3] = SILVER_BGR
    alignment = _alignment()
    ornament = ornament_mask(image, alignment)
    layer, report = reference_headwear_layer(image, ornament)
    assert layer[60, 205, 3] == FULL_ALPHA
    assert layer[150, 100, 3] == 0
    assert report["opaque_pixels"] > 0


def test_pose_occluder_masks_raised_hand_but_not_temple_skin() -> None:
    lazy_alignment = _alignment()
    warped = _canvas()
    # 中性渲染：鬢角（髮量左緣）是皮膚；本姿勢渲染：鬢角一樣是皮膚，另外多了舉到臉旁的手。
    neutral = np.zeros((SIZE, SIZE, 4), np.uint8)
    neutral[:, :, 3] = FULL_ALPHA
    neutral[60:200, 80:100, :3] = SKIN_BGR
    pose = neutral.copy()
    pose[80:160, 240:300, :3] = SKIN_BGR
    mask = pose_occluder_mask(pose, neutral, warped, lazy_alignment)
    assert mask[120, 270] == 1
    assert mask[120, 90] == 0


def test_pose_occluder_masks_arms_below_chin_against_reference() -> None:
    alignment = _alignment()
    warped = _canvas()
    pose = np.zeros((SIZE, SIZE, 4), np.uint8)
    pose[:, :, 3] = FULL_ALPHA
    chin = int(EYE_CENTER[1] + 1.6 * EYE_DISTANCE)
    pose[chin + 10 : chin + 60, 120:280, :3] = SKIN_BGR  # 下巴線以下的交叉手臂
    pose[100:140, 100:140, :3] = SKIN_BGR  # 下巴線以上、參考圖是頭髮：不算（中性渲染缺席時）
    mask = pose_occluder_mask(pose, None, warped, alignment)
    assert mask[chin + 30, 200] == 1
    assert mask[120, 120] == 0


def test_extract_reference_layers_returns_none_when_no_face(tmp_path: Path) -> None:
    blank = np.zeros((SIZE, SIZE, 3), np.uint8)
    blank[:, :] = (255, 0, 255)
    reference = tmp_path / "reference.png"
    assert cv2.imwrite(str(reference), blank)
    model = ROOT / "assets/vision-models/face_detection_yunet_2023mar.onnx"
    base = np.zeros((SIZE, SIZE, 4), np.uint8)
    assert extract_reference_layers(base, reference, model) is None


def main() -> int:
    test_hair_layer_keeps_dark_mass_and_rejects_skin()
    test_hair_layer_fills_enclosed_hole_with_hair_pixels()
    test_hair_layer_does_not_fill_enclosed_skin()
    test_ornament_mask_takes_silver_above_brow_and_beads_only_in_tassel_column()
    test_ornament_mask_rejects_bright_warm_skin()
    test_headwear_layer_uses_ornament_pixels_only()
    test_pose_occluder_masks_raised_hand_but_not_temple_skin()
    test_pose_occluder_masks_arms_below_chin_against_reference()
    with tempfile.TemporaryDirectory() as raw:
        test_extract_reference_layers_returns_none_when_no_face(Path(raw))
    print("REFERENCE_LAYERS_TESTS_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
