"""染色初始圖 × 中段強度：驗證「顏色先驗錯了」是否就是單段 img2img 的瓶頸。

灰模版的強度曲線顯示一條很清楚的路徑：
    s0.55  IoU 0.919  灰模原樣通過，完全沒轉換
    s0.65  IoU 0.832  已是女性、泳裝長出來，但全身灰、光頭
    s0.95  IoU ~基準   幾何完全沒進去

s0.65 缺的只有顏色。而顏色缺席是可以解釋的——初始圖是灰的，模型得先花
去噪預算把灰變成膚色，預算一花，幾何跟著被改掉。所以把顏色先驗直接放進
初始圖，理論上能在同一個強度下同時拿到幾何與膚色。

這支探針就測這件事：同樣的強度，只換初始圖（灰模 vs 染色），比對
幾何保真（剪影 IoU）與風格轉換（前景彩度）兩軸。
"""
import os
import sys
from pathlib import Path

import numpy as np
import torch
from PIL import Image

# 本檔原於 session 暫存目錄開發，匯入路徑與資料根目錄都寫死。入庫時改為：
#   匯入路徑取自本檔所在目錄；資料根目錄可用 MOHAN_VISION_ROOT 覆寫，
#   預設保留原機器路徑，讓既有紀錄可重現。
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from thresholds import BACKGROUND_DISTANCE
from lora_loader import load_aitoolkit_chroma_lora
from chroma_mass_produce_v9 import BODY, HAIR, LORA, TAIL, GGUF
from produce_v10_geo import make_init, NEG
from tinted_init import tinted_init

ROOT = Path(os.environ.get(
    "MOHAN_VISION_ROOT",
    r"D:\FlamebladeStudio\CodexProjects\2026-08-13\mohan-multisensory-vision",
))
BUNDLE = (
    ROOT / "artifacts/pose-atlas-rebuild/2026-08-26"
    / "canonical24-control-bundles-agent-b/bundles/yaw+090-pitch+00"
)
OUT = ROOT / "work/second-gen-body/tinted-strength-probe"
OUT.mkdir(parents=True, exist_ok=True)
WIDTH, HEIGHT = 832, 1248
STRENGTHS = (0.65, 0.72, 0.80)


def masks(image: Image.Image) -> tuple[np.ndarray, float]:
    array = np.asarray(image.convert("RGB")).astype(np.int16)
    corners = np.concatenate([
        array[:40, :40].reshape(-1, 3), array[:40, -40:].reshape(-1, 3),
        array[-40:, :40].reshape(-1, 3), array[-40:, -40:].reshape(-1, 3),
    ])
    background = np.median(corners, axis=0)
    mask = np.abs(array - background).sum(axis=2) > BACKGROUND_DISTANCE
    high, low = array.max(axis=2), array.min(axis=2)
    sat = np.where(high > 0, (high - low) / np.maximum(high, 1), 0.0)
    return mask, float(sat[mask].mean()) if mask.any() else 0.0


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    from diffusers import (
        ChromaImg2ImgPipeline, ChromaTransformer2DModel, GGUFQuantizationConfig,
    )

    grey = make_init(BUNDLE)
    tinted = tinted_init(BUNDLE, (WIDTH, HEIGHT))
    tinted.save(OUT / "_init-tinted.png")
    control, _ = masks(grey)

    transformer = ChromaTransformer2DModel.from_single_file(
        str(GGUF),
        quantization_config=GGUFQuantizationConfig(compute_dtype=torch.bfloat16),
        torch_dtype=torch.bfloat16,
    )
    pipe = ChromaImg2ImgPipeline.from_pretrained(
        "lodestones/Chroma1-HD", transformer=transformer, torch_dtype=torch.bfloat16
    )
    load_aitoolkit_chroma_lora(pipe, LORA, weight=0.85)
    pipe.enable_model_cpu_offload()
    pipe.set_progress_bar_config(disable=True)

    prompt = (
        "mhn_identity, a full-body studio photograph of a beautiful young East "
        f"Asian woman, {HAIR}, elegant classical Chinese facial features, {BODY}. {TAIL}"
    )
    haired = tinted_init(BUNDLE, (WIDTH, HEIGHT), hair_hint=True)
    haired.save(OUT / "_init-tinted-hair.png")

    # 三個組合就夠分辨兩個變因：染色治不治得了顏色、髮量提示長不長得出頭髮
    # 灰模版跑完整條曲線後，s0.85 是最好的一張：手臂自己從 A-pose 垂下、
    # 皮膚有真實質感、側面精準、IoU 0.776 仍遠高於基準 0.396。
    # 只剩膚色偏灰藍與光頭兩個錯，而那正是染色與髮量提示各自要修的。
    runs = [
        ("染色+髮", haired, 0.85),
        ("染色+髮", haired, 0.80),
        ("染色", tinted, 0.85),
    ]
    print("初始圖      strength   IoU     彩度", flush=True)
    for label, init, strength in runs:
        image = pipe(
            prompt=prompt, negative_prompt=NEG, image=init, strength=strength,
            height=HEIGHT, width=WIDTH,
            num_inference_steps=34, guidance_scale=5.0,
            generator=torch.Generator(device="cpu").manual_seed(7),
        ).images[0]
        tag = "tinted" if label == "染色" else "tinted-hair"
        image.save(OUT / f"{tag}-s{int(strength*100):03d}.png")
        mask, colour = masks(image)
        union = np.logical_or(mask, control).sum()
        value = float(np.logical_and(mask, control).sum()) / union if union else 0.0
        print(f"{label:10s} {strength:.2f}     {value:.3f}   {colour:.3f}", flush=True)

    print("TINTED_PROBE_DONE", flush=True)


if __name__ == "__main__":
    main()
