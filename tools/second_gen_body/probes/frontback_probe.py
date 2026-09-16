"""驗證正面構圖的強度與種子條件。

yaw+000 的正面控制圖在 strength 0.85 下連續兩次產出背面，
眼距佔臉寬為 0.077 與 0.081；當時提示已明確指定胸腹朝向鏡頭。
染色初始圖的臉部對比較低，髮罩正反對稱；0.85 加噪後主要保留低頻，
因此需增加可辨識正反的線索。同種子的純 t2i 亦產出背面。

本探針比較兩項條件：降低強度以保留更多初始結構，並觀察膚色表現；
更換種子以確認先驗的影響。種子結果提供佐證，方位控制另以幾何驗證。
"""
import os
import sys
from pathlib import Path

import torch

# 本檔原於 session 暫存目錄開發，匯入路徑與資料根目錄都寫死。入庫時改為：
#   匯入路徑取自本檔所在目錄；資料根目錄可用 MOHAN_VISION_ROOT 覆寫，
#   預設保留原機器路徑，讓既有紀錄可重現。
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from thresholds import EYE_SPAN_FRONT_MIN
from lora_loader import load_aitoolkit_chroma_lora
from chroma_mass_produce_v9 import BODY, HAIR, LORA, TAIL, GGUF
from produce_v10_geo import BUNDLES, NEG
from produce_v11_geo import (
    ARMS, NEG_ARMS, control_mask, below_head_iou, face_metrics, orientation,
)
from tinted_init import tinted_init

ROOT = Path(os.environ.get(
    "MOHAN_VISION_ROOT",
    r"D:\FlamebladeStudio\CodexProjects\2026-08-13\mohan-multisensory-vision",
))
OUT = ROOT / "work/second-gen-body/frontback-probe"
OUT.mkdir(parents=True, exist_ok=True)
WIDTH, HEIGHT = 832, 1248

RUNS = [
    ("降強度 0.75", 0.75, 7),
    ("降強度 0.65", 0.65, 7),
    ("換種子", 0.85, 20260831),
]


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    from diffusers import (
        ChromaImg2ImgPipeline, ChromaTransformer2DModel, GGUFQuantizationConfig,
    )

    folder = BUNDLES / "yaw+000-pitch+00"
    init = tinted_init(folder, (WIDTH, HEIGHT), hair_hint=True)
    control = control_mask(folder)

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
        f"Asian woman, {HAIR}, elegant classical Chinese facial features, "
        f"{BODY}, {ARMS}. {orientation(0)}. {TAIL}"
    )
    print("手段            strength  seed        眼距比   頸下IoU  判讀", flush=True)
    for label, strength, seed in RUNS:
        image = pipe(
            prompt=prompt, negative_prompt=NEG_ARMS + NEG, image=init,
            strength=strength, height=HEIGHT, width=WIDTH,
            num_inference_steps=34, guidance_scale=5.0,
            generator=torch.Generator(device="cpu").manual_seed(seed),
        ).images[0]
        target = OUT / f"{label.replace(' ', '')}-s{int(strength*100):03d}-{seed}.png"
        image.save(target)
        _area, eye = face_metrics(target)
        geometry = below_head_iou(target, control)
        note = "正面" if eye >= EYE_SPAN_FRONT_MIN else "仍是背面"
        print(f"{label:14s}  {strength:.2f}    {seed:<10d} {eye:6.3f}  "
              f"{geometry:7.3f}  {note}", flush=True)

    print("FRONTBACK_PROBE_DONE", flush=True)


if __name__ == "__main__":
    main()
