"""組裝 half-body 輸入，產生 assets/expressions 契約檔名。

輸入目錄與輸出目錄都由參數指定；產線不會在輸入目錄旁偷偷建立 keyed
副本，也不會從工作樹的 assets 讀取參考圖。
"""

from __future__ import annotations

lazy import argparse
lazy from pathlib import Path

lazy import numpy as np

lazy from .constants import CANVAS_SIZE, MOUTH_CLIPS
lazy from .derive_variants import blink_rects, outside_difference, paste_rect, rgba
lazy from .image_ops import chroma_key, load_image, save_png


SUFFIX = {"cheek": "", "lean": "_lean", "front": "_front"}
SPEECH_SOURCE = {
    "front": {
        "mid": "bare_viseme_mid_front",
        "open": "bare_viseme_wide_front",
        "round": "bare_viseme_o_front",
    },
    "cheek": {
        "mid": "bare_speaking_cheek",
        "open": "bare_viseme_o_cheek",
        "round": "bare_viseme_round_cheek",
    },
    "lean": {
        "mid": "bare_speaking_lean",
        "open": "bare_viseme_o_lean",
        "round": "bare_viseme_round_lean",
    },
}
POSE_FRAMES = {
    "front": {
        "speaking_front": "bare_speaking_front",
        "viseme_i_front": "bare_viseme_i_front",
        "viseme_round_front": "bare_viseme_round_front",
        "viseme_o_front": "bare_viseme_o_front",
        "viseme_mid_front": "bare_viseme_mid_front",
        "viseme_wide_front": "bare_viseme_wide_front",
    },
    "cheek": {
        "speaking": "bare_speaking_cheek",
        "viseme_i": "bare_viseme_i_cheek",
        "viseme_round": "bare_viseme_round_cheek",
        "viseme_o": "bare_viseme_o_cheek",
    },
    "lean": {
        "speaking_lean": "bare_speaking_lean",
        "viseme_i_lean": "bare_viseme_i_lean",
        "viseme_round_lean": "bare_viseme_round_lean",
        "viseme_o_lean": "bare_viseme_o_lean",
    },
}
BASE_STEM = "bare_{pose}.aligned"
BLINK_STEM = "bare_blink_{pose}"


def keyed_array(input_directory: Path, stem: str) -> np.ndarray | None:
    """讀取既有 keyed 輸入，或在記憶體內鍵出 RGBA；不改寫輸入。"""

    keyed_path = input_directory / f"{stem}.keyed.png"
    source_path = input_directory / f"{stem}.png"
    if keyed_path.is_file() and (
        not source_path.is_file()
        or keyed_path.stat().st_mtime >= source_path.stat().st_mtime
    ):
        return rgba(keyed_path)
    if not source_path.is_file():
        return None
    return rgba_array(chroma_key(load_image(source_path)))


def rgba_array(image: np.ndarray) -> np.ndarray:
    from .image_ops import resize_rgba

    if image.shape[:2] != (CANVAS_SIZE, CANVAS_SIZE):
        if image.shape[0] != image.shape[1]:
            raise ValueError(f"輸入不是正方形：{image.shape[:2]}")
        image = resize_rgba(image, (CANVAS_SIZE, CANVAS_SIZE))
    return image


def expression_rect(expression: str) -> tuple[int, int, int, int]:
    from domain.companion_animation_contract import EXPRESSION_SPEECH_MOUTH_RECTS

    rect = EXPRESSION_SPEECH_MOUTH_RECTS[expression]
    return rect.x(), rect.y(), rect.width(), rect.height()


def _save(destination: Path, name: str, image: np.ndarray) -> None:
    save_png(destination / f"{name}.png", image)


def _assemble_pose(
    input_directory: Path,
    destination: Path,
    pose: str,
    suffix: str,
) -> tuple[np.ndarray | None, list[str], list[str]]:
    missing: list[str] = []
    problems: list[str] = []
    base_path = input_directory / f"{BASE_STEM.format(pose=pose)}.png"
    if not base_path.is_file():
        return None, [base_path.name], problems
    try:
        base = rgba(base_path)
    except (OSError, ValueError) as error:
        return None, [f"{base_path.name}（{error}）"], problems
    _save(destination, f"idle{suffix}", base)
    blink = keyed_array(input_directory, BLINK_STEM.format(pose=pose))
    if blink is None:
        missing.append(f"{BLINK_STEM.format(pose=pose)}.keyed.png")
    else:
        blink_result = base
        for rect in blink_rects(pose):
            blink_result = paste_rect(blink_result, blink, rect)
        _save(destination, f"blink{suffix}", blink_result)
    for output_name, stem in POSE_FRAMES[pose].items():
        source = keyed_array(input_directory, stem)
        if source is None:
            missing.append(f"{stem}.keyed.png")
            continue
        frame = paste_rect(base, source, MOUTH_CLIPS[pose])
        outside = outside_difference(base, frame, MOUTH_CLIPS[pose])
        if outside:
            problems.append(f"{output_name}: 嘴框外有差異 {outside}")
        _save(destination, output_name, frame)
    return base, missing, problems


def _assemble_expressions(
    input_directory: Path,
    destination: Path,
    bases: dict[str, np.ndarray],
    missing: list[str],
    problems: list[str],
) -> None:
    from domain.companion_animation_contract import (
        EXPRESSION_BLINK_FRAMES,
        EXPRESSION_POSES,
    )

    for expression, pose in EXPRESSION_POSES.items():
        expression_image = keyed_array(input_directory, f"{expression}.face")
        if expression_image is None or pose not in bases:
            missing.append(f"{expression}.face.keyed.png")
            continue
        _save(destination, expression, expression_image)
        rect = expression_rect(expression)
        for frame_name, stem in SPEECH_SOURCE[pose].items():
            source = keyed_array(input_directory, stem)
            if source is None:
                missing.append(f"{stem}.keyed.png")
                continue
            variant = paste_rect(expression_image, source, rect)
            outside = outside_difference(expression_image, variant, rect)
            if outside:
                problems.append(
                    f"{expression}_speech_{frame_name}: 嘴框外有差異 {outside}"
                )
            _save(destination, f"{expression}_speech_{frame_name}", variant)
        if expression not in EXPRESSION_BLINK_FRAMES:
            continue
        blink = keyed_array(input_directory, BLINK_STEM.format(pose=pose))
        if blink is None:
            missing.append(f"{BLINK_STEM.format(pose=pose)}.keyed.png")
            continue
        variant = expression_image
        for rect in blink_rects(pose):
            variant = paste_rect(variant, blink, rect)
        _save(destination, EXPRESSION_BLINK_FRAMES[expression], variant)


def assemble(
    input_directory: Path, destination: Path
) -> tuple[int, list[str], list[str]]:
    """組裝一批素材，回傳 (寫出數量, 缺件, 契約問題)。"""

    destination.mkdir(parents=True, exist_ok=True)
    missing: list[str] = []
    problems: list[str] = []
    bases: dict[str, np.ndarray] = {}
    for pose, suffix in SUFFIX.items():
        base, pose_missing, pose_problems = _assemble_pose(
            input_directory, destination, pose, suffix
        )
        missing.extend(pose_missing)
        problems.extend(pose_problems)
        if base is not None:
            bases[pose] = base

    _assemble_expressions(input_directory, destination, bases, missing, problems)

    written = sorted(destination.glob("*.png"))
    return len(written), sorted(set(missing)), problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--input-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    written, missing, problems = assemble(args.input_dir, args.destination)
    print(f"寫出 {written} 檔到 {args.destination}")
    if missing:
        print("缺素材：", ", ".join(missing))
    if problems:
        print("契約違反：", "; ".join(problems))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
