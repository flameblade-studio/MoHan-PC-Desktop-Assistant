"""量測「幾何到底有沒有進去」，而不是「哪個強度看起來順眼」。

先前選定 s0.95 的推理是反的：0.70/0.80/0.88 之所以殘留人偶體型，正是因為
幾何有進去；0.95 之所以乾淨，是因為幾何沒進去。diffusers 的算式可直接驗證——

    init_timestep = min(steps * strength, steps)
    t_start       = int(max(steps - init_timestep, 0))

steps=34、strength=0.95 時 t_start=1，34 步只跳過 1 步，初始圖被加噪到幾乎全是雜訊。
實測也對得上：兩張構圖完全不同的初始圖，輸出只差 2.1% 的像素。

所以這支探針改用一個能證偽的指標：輸出的人物剪影與控制網格剪影的 IoU。
幾何若真的進去，IoU 應隨 strength 下降而上升；若沒進去，IoU 會停在
「隨便畫一個人剛好也會重疊」的基準值附近。

順帶修掉另一個 bug：先前沒傳 height/width，管線退回預設 1024x1024 方形，
把 2:3 的初始圖壓成正方形，而方形畫布正是模型畫成角色設定表（兩個人）的誘因。
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
from lora_loader import load_aitoolkit_chroma_lora
from chroma_mass_produce_v9 import BODY, HAIR, LORA, TAIL, GGUF
from produce_v10_geo import make_init, NEG, PLATE

ROOT = Path(os.environ.get(
    "MOHAN_VISION_ROOT",
    r"D:\FlamebladeStudio\CodexProjects\2026-08-13\mohan-multisensory-vision",
))
BUNDLE = (
    ROOT / "artifacts/pose-atlas-rebuild/2026-08-26"
    / "canonical24-control-bundles-agent-b/bundles/yaw+090-pitch+00"
)
OUT = ROOT / "work/second-gen-body/strength-iou-probe"
OUT.mkdir(parents=True, exist_ok=True)
WIDTH, HEIGHT = 832, 1248
STRENGTHS = (0.55, 0.65, 0.75, 0.85, 0.95)


def foreground(image: Image.Image) -> np.ndarray:
    """以與淺灰底板的色差切出人物；底板是我們自己填的，顏色已知，不必猜。"""
    array = np.asarray(image.convert("RGB")).astype(np.int16)
    return np.abs(array - np.array(PLATE)).sum(axis=2) > 45


def iou(a: np.ndarray, b: np.ndarray) -> float:
    union = np.logical_or(a, b).sum()
    return float(np.logical_and(a, b).sum()) / union if union else 0.0


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    from diffusers import (
        ChromaImg2ImgPipeline, ChromaTransformer2DModel, GGUFQuantizationConfig,
    )

    init = make_init(BUNDLE)
    init.save(OUT / "_init.png")
    control = foreground(init)
    print(f"初始圖 {init.size}，控制剪影佔畫面 {control.mean()*100:.1f}%", flush=True)

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

    # 基準線：完全不給初始圖的純文生圖。任何強度的 IoU 必須顯著高過它，
    # 才算「幾何真的進去了」；否則只是「隨便畫個人剛好也會重疊」。
    from diffusers import ChromaPipeline
    t2i = ChromaPipeline(**{k: v for k, v in pipe.components.items()})
    t2i.set_progress_bar_config(disable=True)
    baseline_img = t2i(
        prompt=prompt, negative_prompt=NEG, height=HEIGHT, width=WIDTH,
        num_inference_steps=34, guidance_scale=5.0,
        generator=torch.Generator(device="cpu").manual_seed(7),
    ).images[0]
    baseline_img.save(OUT / "baseline-t2i.png")
    base_iou = iou(foreground(baseline_img), control)
    print(f"\n純文生圖基準 IoU = {base_iou:.3f}", flush=True)

    print("\nstrength   IoU     相對基準", flush=True)
    for strength in STRENGTHS:
        target = OUT / f"s{int(strength*100):03d}.png"
        image = pipe(
            prompt=prompt, negative_prompt=NEG, image=init, strength=strength,
            height=HEIGHT, width=WIDTH,          # 不傳就退回 1024x1024 方形
            num_inference_steps=34, guidance_scale=5.0,
            generator=torch.Generator(device="cpu").manual_seed(7),
        ).images[0]
        image.save(target)
        value = iou(foreground(image), control)
        steps_kept = 34 - int(max(34 - min(34 * strength, 34), 0))
        print(f"  {strength:.2f}    {value:.3f}   {value - base_iou:+.3f}"
              f"   （跑 {steps_kept}/34 步）", flush=True)

    print("\nIOU_PROBE_DONE", flush=True)


if __name__ == "__main__":
    main()
