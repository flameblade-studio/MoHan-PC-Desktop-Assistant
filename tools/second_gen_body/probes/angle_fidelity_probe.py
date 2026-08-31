"""第一段的強度該多低，才守得住斜角？

現象：yaw+045 在第一段 s0.75 就已經變成正面。而同一個視角換另一組種子時角度
是對的——**角度受種子影響大於受控制圖影響**，代表 0.75 對角度的約束力不足。

0.75 是照著正面視角挑的，但正面是最容易的情形：它與模型的預設先驗一致，
所以看不出約束力不夠。斜角才是真正的考驗。

先前在 candidate3 上量過的剪影 IoU（yaw+090）：
    s0.55 → 0.863   s0.65 → 0.814   s0.75 → 0.876   s0.85 → 0.839
那是與控制圖的重疊，強度越低本來就越貼近；問題是低強度會讓外觀留在灰模那側。
但兩段式改變了取捨——**第一段只需要負責幾何，外觀交給第二段**，
所以第一段其實可以壓得比 0.75 更低。

這支探針就測這件事：yaw+045 與 yaw+090 兩個斜角，第一段取 0.55/0.65/0.75，
第二段固定 0.60，量最終的角度保真度。判準用剪影 IoU（與該視角的控制圖比），
不用眼距比——眼距比只分得出正面與背面，分不出 45 度與 0 度。
"""
import os
import sys
from pathlib import Path

import torch

# 本檔原於 session 暫存目錄開發，匯入路徑與資料根目錄都寫死。入庫時改為：
#   匯入路徑取自本檔所在目錄；資料根目錄可用 MOHAN_VISION_ROOT 覆寫，
#   預設保留原機器路徑，讓既有紀錄可重現。
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lora_loader import load_aitoolkit_chroma_lora
from chroma_mass_produce_v9 import BODY, HAIR, LORA, TAIL, GGUF
from produce_v10_geo import NEG
from produce_v11_geo import ARMS, NEG_ARMS, orientation, orientation_negative
from produce_v12_c4 import CONTROLS, WIDTH, HEIGHT, control_mask, check
from tinted_init import tinted_from_paths

ROOT = Path(os.environ.get(
    "MOHAN_VISION_ROOT",
    r"D:\FlamebladeStudio\CodexProjects\2026-08-13\mohan-multisensory-vision",
))
OUT = ROOT / "work/second-gen-body/angle-fidelity-probe"
OUT.mkdir(parents=True, exist_ok=True)
STAGE1_LADDER = (0.55, 0.65, 0.75)
STAGE2 = 0.60
TEST_VIEWS = (45, 90)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    from diffusers import (
        ChromaImg2ImgPipeline, ChromaTransformer2DModel, GGUFQuantizationConfig,
    )

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
    print("角度保真探針 ready", flush=True)

    print(f"\n{'視角':>6s}{'第一段':>8s}{'頸下IoU':>10s}{'眼距比':>9s}  判讀", flush=True)
    for yaw in TEST_VIEWS:
        init = tinted_from_paths(
            CONTROLS / f"yaw{yaw:+04d}-pitch+00_shaded-render.png",
            CONTROLS / f"yaw{yaw:+04d}-pitch+00_silhouette.png",
            (WIDTH, HEIGHT), hair_hint=True, preserve_contrast=True,
        )
        control = control_mask(yaw)
        prompt = (
            "mhn_identity, a full-body studio photograph of a beautiful young East "
            f"Asian woman, {HAIR}, elegant classical Chinese facial features, "
            f"{BODY}, {ARMS}. {orientation(yaw)}. {TAIL}"
        )
        negative = orientation_negative(yaw) + NEG_ARMS + NEG
        for strength in STAGE1_LADDER:
            target = OUT / f"yaw{yaw:+04d}-s1_{int(strength*100):03d}.png"
            if target.exists():
                continue
            first = pipe(
                prompt=prompt, negative_prompt=negative, image=init,
                strength=strength, height=HEIGHT, width=WIDTH,
                num_inference_steps=34, guidance_scale=5.0,
                generator=torch.Generator(device="cpu").manual_seed(7),
            ).images[0]
            second = pipe(
                prompt=prompt, negative_prompt=negative, image=first,
                strength=STAGE2, height=HEIGHT, width=WIDTH,
                num_inference_steps=34, guidance_scale=5.0,
                generator=torch.Generator(device="cpu").manual_seed(11),
            ).images[0]
            second.save(target)
            first.save(OUT / f"yaw{yaw:+04d}-s1_{int(strength*100):03d}-stage1.png")
            verdict, _ok = check(target, yaw, control)
            iou = float(verdict.split("頸下IoU")[1].split()[0])
            eye = float(verdict.split("眼距比")[1].split()[0])
            print(f"{yaw:+6d}{strength:8.2f}{iou:10.3f}{eye:9.3f}  {verdict}", flush=True)

    print("ANGLE_PROBE_DONE", flush=True)


if __name__ == "__main__":
    main()
