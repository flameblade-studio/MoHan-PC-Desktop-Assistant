"""正面視角為何翻成背面，以及哪一個手段治得了。

現象：yaw+000 的正面控制圖，在 strength 0.85 下連續兩次產出背面，
即使提示詞明寫 "she faces the camera directly, her chest and navel toward
the camera"。眼距佔臉寬 0.077 與 0.081，兩次都是背面。

診斷：0.85 只有低頻訊號存活，而正反的判別資訊多半在高頻（五官）。
染色初始圖的臉被壓成低對比的膚色塊，頭頂髮罩又正反對稱，
模型拿不到足夠的正反線索，就回退到自己的先驗——而同種子的純 t2i 基準
也是背面，可見這個種子的先驗就是背面。

兩個候選解法各有代價，一次測完再選：
  降強度   讓更多初始圖結構存活。代價是可能回到「灰皮膚」那一側
  換種子   若翻面是種子先驗造成的，換一個就好。代價是每個視角都可能要挑種子，
           那是碰運氣不是控制，只能當佐證不能當方案
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
