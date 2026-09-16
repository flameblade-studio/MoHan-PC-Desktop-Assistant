"""兩段式生成：第一段固定幾何與方位，第二段改善外觀。

yaw+000 的單段實測：
    s0.55~0.75 保留幾何與方位，膚色、臉部及胸部細節仍待校正。
    s0.85 外觀較佳，方位為背面，眼距比 0.077 與 0.081。
    s0.95 剪影 IoU 0.325，純 t2i 基準為 0.396，幾何作用仍待加強。

正反辨識與細節都依賴高頻訊號。兩段式先產出方位正確的人物照片，
再將它作為第二段初始圖，讓低頻先驗保留方位並以較高強度處理細節。

Windows 路徑使用 ASCII 檔名，以符合此環境 cv2.imread 的讀取條件。
先前中文檔名的讀取結果為 None，此規範保留該次實測所得的相容方式。
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
from produce_v10_geo import BUNDLES, NEG
from produce_v11_geo import (
    ARMS, NEG_ARMS, below_head_iou, control_mask, face_metrics, figure_count,
    orientation,
)
from tinted_init import tinted_init

ROOT = Path(os.environ.get(
    "MOHAN_VISION_ROOT",
    r"D:\FlamebladeStudio\CodexProjects\2026-08-13\mohan-multisensory-vision",
))
OUT = ROOT / "work/second-gen-body/two-stage-probe"
OUT.mkdir(parents=True, exist_ok=True)
WIDTH, HEIGHT = 832, 1248
STAGE1 = 0.75
STAGE2 = (0.45, 0.60)


def report(label: str, path: Path, control) -> None:
    area, eye = face_metrics(path)
    print(f"  {label:22s} 眼距比 {eye:5.3f}  頸下IoU {below_head_iou(path, control):5.3f}"
          f"  臉部 {area:.4f}  人數 {figure_count(path)}", flush=True)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    from diffusers import (
        ChromaImg2ImgPipeline, ChromaTransformer2DModel, GGUFQuantizationConfig,
    )

    folder = BUNDLES / "yaw+000-pitch+00"
    control = control_mask(folder)
    # 染色改用保留對比版：窄帶重映射把明暗動態範圍從 148 壓到 106，
    # 而明暗正是承載正反 3D 資訊的訊號
    init = tinted_init(folder, (WIDTH, HEIGHT), hair_hint=True, preserve_contrast=True)
    init.save(OUT / "_init.png")

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

    def run(image, strength, seed):
        return pipe(
            prompt=prompt, negative_prompt=NEG_ARMS + NEG, image=image,
            strength=strength, height=HEIGHT, width=WIDTH,
            num_inference_steps=34, guidance_scale=5.0,
            generator=torch.Generator(device="cpu").manual_seed(seed),
        ).images[0]

    print("第一段：鎖定幾何與方位", flush=True)
    first = run(init, STAGE1, 7)
    first_path = OUT / "stage1-s075.png"
    first.save(first_path)
    report("第一段 s0.75", first_path, control)

    print("第二段：以第一段輸出為初始圖修外觀", flush=True)
    for strength in STAGE2:
        second = run(first, strength, 11)
        path = OUT / f"stage2-s{int(strength * 100):03d}.png"
        second.save(path)
        report(f"第二段 s{strength:.2f}", path, control)

    print("TWO_STAGE_DONE", flush=True)


if __name__ == "__main__":
    main()
