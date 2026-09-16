"""臉部細修：裁臉、放大、LoRA 重繪，再柔邊貼回。

擁有者於 2026-08-30 指出，全身構圖中的臉約佔 8%（100×120 像素），
細部五官需要更多像素呈現。本流程將臉放大到 1024² 後重繪貼回，
提供約 70 倍的臉部像素預算。
"""
import os
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

__all__ = ("detect_face_box", "detail_face")

YUNET = Path(os.environ.get("MOHAN_VISION_ROOT",
    r"D:\FlamebladeStudio\CodexProjects\2026-08-13\mohan-multisensory-vision")) / "assets/vision-models/face_detection_yunet_2023mar.onnx"


def detect_face_box(image: Image.Image, confidence: float = 0.5):
    """回傳最大臉的 (x, y, w, h)，找不到回 None。"""
    bgr = cv2.cvtColor(np.asarray(image.convert("RGB")), cv2.COLOR_RGB2BGR)
    height, width = bgr.shape[:2]
    detector = cv2.FaceDetectorYN.create(
        str(YUNET), "", (320, 320), confidence, 0.3, 5000
    )
    detector.setInputSize((width, height))
    _, found = detector.detect(bgr)
    if found is None or len(found) == 0:
        return None
    box = max(found, key=lambda f: f[2] * f[3])
    return tuple(int(v) for v in box[:4])


def _square_region(box, image_size, expand: float):
    x, y, w, h = box
    cx, cy = x + w / 2, y + h / 2
    side = max(w, h) * expand
    iw, ih = image_size
    side = min(side, iw, ih)
    left = int(max(0, min(iw - side, cx - side / 2)))
    top = int(max(0, min(ih - side, cy - side / 2)))
    return left, top, int(side)


def detail_face(
    pipe,
    image: Image.Image,
    prompt: str,
    negative_prompt: str,
    *,
    strength: float = 0.55,
    expand: float = 2.4,
    work_size: int = 1024,
    steps: int = 30,
    guidance: float = 4.5,
    seed: int = 7,
    feather: float = 0.16,
) -> Image.Image | None:
    """裁臉放大重繪再貼回；找不到臉回 None。"""
    import torch

    box = detect_face_box(image)
    if box is None:
        return None
    left, top, side = _square_region(box, image.size, expand)
    crop = image.crop((left, top, left + side, top + side))
    work = crop.resize((work_size, work_size), Image.LANCZOS)
    detailed = pipe(
        prompt=prompt,
        negative_prompt=negative_prompt,
        image=work,
        strength=strength,
        num_inference_steps=steps,
        guidance_scale=guidance,
        generator=torch.Generator("cuda").manual_seed(seed),
    ).images[0]
    back = detailed.resize((side, side), Image.LANCZOS)

    # 柔邊橢圓遮罩，避免貼回接縫
    mask = Image.new("L", (side, side), 0)
    inset = int(side * 0.06)
    ImageDraw.Draw(mask).ellipse(
        (inset, inset, side - inset, side - inset), fill=255
    )
    mask = mask.filter(ImageFilter.GaussianBlur(radius=side * feather))

    result = image.copy()
    result.paste(back, (left, top), mask)
    return result
