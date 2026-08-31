"""v11：真正接上幾何條件化的 24 視角量產。

與 v10 的差別，每一項都對應今晚實測到的一個錯：

  顯式傳 height/width   v10 沒傳，管線退回 1024x1024 方形，方形畫布誘導模型
                        畫成正面+側面的角色設定表，一張圖兩個人
  strength 0.85         v10 用 0.95，而 s0.95 的剪影 IoU 只有 0.325，低於純
                        文生圖基準 0.396——幾何完全脫鉤。0.85 是量測中唯一
                        同時守住幾何與完成上色的一檔
  染色初始圖            灰模在 0.55~0.85 全程輸出灰皮膚（彩度貼著灰模自身的
                        0.120 不動）。顏色是低頻訊號，提高強度治不了，
                        只能換掉初始圖的顏色先驗
  頭頂髮量提示          同理，網格光頭，低頻就一路說「沒有頭髮」。實測補上
                        低頻暗色髮罩後，輸出的髮髻與後頸規格全中
  明確的手臂措辭        提示詞原本完全沒指定手臂，姿勢全靠模型先驗；
                        24 視角轉盤需要各角度一致

自我閘門沿用 v10 的設計並加嚴：第一張要同時通過人數、臉部、以及頸下剪影
IoU 三關才放行後續 23 張。IoU 必須量頸部以下——控制剪影是光頭的，
輸出長出頭髮會讓全身 IoU 無條件下降，那是指標的混淆項不是幾何退步。
"""
import os
import sys
from pathlib import Path

import cv2
import numpy as np
import torch
from PIL import Image

# 本檔原於 session 暫存目錄開發，匯入路徑與資料根目錄都寫死。入庫時改為：
#   匯入路徑取自本檔所在目錄；資料根目錄可用 MOHAN_VISION_ROOT 覆寫，
#   預設保留原機器路徑，讓既有紀錄可重現。
sys.path.insert(0, str(Path(__file__).resolve().parent))
from lora_loader import load_aitoolkit_chroma_lora
from chroma_mass_produce_v9 import BODY, HAIR, LORA, TAIL, GGUF, YUNET
from produce_v10_geo import BUNDLES, NEG, formal_yaw
from tinted_init import tinted_init

ROOT = Path(os.environ.get(
    "MOHAN_VISION_ROOT",
    r"D:\FlamebladeStudio\CodexProjects\2026-08-13\mohan-multisensory-vision",
))
OUT = ROOT / "work/second-gen-body/chroma-views-v11-geo"
OUT.mkdir(parents=True, exist_ok=True)
WIDTH, HEIGHT = 832, 1248
STRENGTH = 0.85
LORA_WEIGHT = 0.85
ARMS = ("her arms hang relaxed straight down at her sides with her hands beside "
        "her thighs, arms not crossed, hands not touching each other")
NEG_ARMS = ("crossed arms, folded arms, hands clasped, hands together, "
            "arms raised, hands on hips, ")


def orientation(yaw: int) -> str:
    """粗方位交給提示詞，細角度交給幾何條件化。

    v9 已量測到提示詞做不到 15/30/45 這種細分（+015 到 +105 全擠在同一個
    鼻眼偏移值），但它做得到正面／四分之三／側面／背面這種粗分——v9 的
    yaw+000 就是正面。而幾何條件化恰好相反：它守得住細角度，卻分不出正反，
    因為 A-pose 的正反剪影幾乎一樣。

    第一次跑 v11 時我把方位措辭整個拿掉，結果 yaw+000 的正面控制圖產出背面，
    剪影 IoU 還給了 0.573「通過」。兩者要一起用，缺一不可。
    """
    angle = abs(yaw)
    if angle <= 22:
        return ("she faces the camera directly, her whole face clearly visible, "
                "her chest and navel toward the camera")
    if angle <= 67:
        # 「一邊肩膀朝向鏡頭、臉仍可見」對背面四分之三也成立——實測 yaw+030
        # 就這樣被種子的背面先驗奪走。每個非背面的段落都要明白斷言正面。
        return ("seen from the front at a three-quarter angle, her face and the "
                "front of her chest and her navel are visible to the camera, "
                "her back is away from the camera")
    if angle <= 112:
        return ("a pure side profile seen from her side, her body turned ninety "
                "degrees, the front of her chest and her face in profile against "
                "the background")
    if angle <= 157:
        return ("seen from behind at an angle, her back toward the camera, "
                "her face turned away")
    return ("seen directly from behind, her back to the camera, "
            "the nape of her neck visible, her face not visible at all")


def orientation_negative(yaw: int) -> str:
    """非背面視角要明確排除背面，否則模型的先驗會把人轉過去。"""
    return "" if abs(yaw) >= 113 else (
        "seen from behind, back view, rear view, facing away from camera, "
        "back turned to the viewer, ")


def control_mask(folder: Path) -> np.ndarray:
    """控制剪影取自 bundle，且套用與初始圖完全相同的裁切幾何。"""
    mask = Image.open(folder / f"{folder.name}_silhouette.png").convert("L")
    inside = np.asarray(mask) > 24
    solid = Image.fromarray((inside * 255).astype(np.uint8))
    left, top, right, bottom = solid.getbbox()
    pad_x, pad_y = int((right - left) * 0.16), int((bottom - top) * 0.05)
    left, top = max(0, left - pad_x), max(0, top - pad_y)
    right, bottom = min(mask.width, right + pad_x), min(mask.height, bottom + pad_y)
    ratio = WIDTH / HEIGHT
    if (right - left) / (bottom - top) < ratio:
        need = int((bottom - top) * ratio) - (right - left)
        left = max(0, left - need // 2)
        right = min(mask.width, right + need - need // 2)
    cropped = solid.crop((left, top, right, bottom))
    if cropped.width / cropped.height < ratio:
        board = Image.new("L", (int(cropped.height * ratio), cropped.height), 0)
        board.paste(cropped, ((board.width - cropped.width) // 2, 0))
        cropped = board
    return np.asarray(cropped.resize((WIDTH, HEIGHT), Image.NEAREST)) > 127


def below_head_iou(path: Path, control: np.ndarray) -> float:
    # 尺寸不一致會讓廣播直接拋例外，把整批量產在中途炸掉。閘門是拿來擋問題的，
    # 自己不該是新的失敗點——尺寸不符就先縮到控制遮罩的尺寸再比。
    opened = Image.open(path).convert("RGB")
    if opened.size != (control.shape[1], control.shape[0]):
        opened = opened.resize((control.shape[1], control.shape[0]), Image.LANCZOS)
    array = np.asarray(opened).astype(np.int16)
    corners = np.concatenate([
        array[:40, :40].reshape(-1, 3), array[:40, -40:].reshape(-1, 3),
        array[-40:, :40].reshape(-1, 3), array[-40:, -40:].reshape(-1, 3),
    ])
    mask = np.abs(array - np.median(corners, axis=0)).sum(axis=2) > 40
    rows = np.where(control.any(axis=1))[0]
    neck = int(rows[0] + (rows[-1] - rows[0]) * 0.13)
    union = np.logical_or(mask[neck:], control[neck:]).sum()
    return float(np.logical_and(mask[neck:], control[neck:]).sum()) / union if union else 0.0


def face_metrics(path: Path) -> tuple[float, float]:
    """回傳（臉部佔畫面比例、眼距佔臉寬比例）。

    第二個數字才是能分辨正反的那一個。YuNet 的信心分數完全分不開——
    實測正面 0.932、背面 0.891，而且它會在背面的髮髻上偵測出「臉」。
    眼距佔臉寬則有乾淨的間隔：正面 0.511，各種背面落在 0.077~0.277。

    這個門檻的證據強度必須誠實標明：**正面樣本只有一個**（v9 yaw+000）。
    n=1 訂出來的門檻是絆線不是證明，量產後仍須目視覆核。
    """
    bgr = cv2.imread(str(path))
    height, width = bgr.shape[:2]
    detector = cv2.FaceDetectorYN.create(str(YUNET), "", (320, 320), 0.6, 0.3, 5000)
    detector.setInputSize((width, height))
    _, found = detector.detect(bgr)
    if found is None or len(found) == 0:
        return 0.0, 0.0
    box = max(found, key=lambda f: f[2] * f[3])
    right_eye, left_eye = np.array(box[4:6]), np.array(box[6:8])
    span = float(np.linalg.norm(left_eye - right_eye))
    return (float(box[2] * box[3]) / (width * height),
            span / max(float(box[2]), 1e-6))


def figure_count(path: Path) -> int:
    """數畫面裡有幾個人。不要用灰階——淺膚色與淺灰背景的亮度只差約 10。

    v10 的版本用灰階、門檻 18，結果把一個人切成頭與身體兩塊、數成兩人：
    頸部膚色亮度約 205，背景 194，差 11 落在門檻內被判成背景。
    改用 RGB 色距，並把水平範圍重疊的分量視為同一個人（頭與軀幹必然重疊）。
    """
    rgb = cv2.cvtColor(cv2.imread(str(path)), cv2.COLOR_BGR2RGB).astype(np.int16)
    corners = np.concatenate([
        rgb[:30, :30].reshape(-1, 3), rgb[:30, -30:].reshape(-1, 3),
        rgb[-30:, :30].reshape(-1, 3), rgb[-30:, -30:].reshape(-1, 3),
    ])
    background = np.median(corners, axis=0)
    mask = (np.abs(rgb - background).sum(axis=2) > 26).astype(np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((25, 25), np.uint8))
    number, _labels, stats, _ = cv2.connectedComponentsWithStats(mask, 8)
    area = rgb.shape[0] * rgb.shape[1]
    spans = []
    for i in range(1, number):
        if stats[i, cv2.CC_STAT_AREA] <= area * 0.015:
            continue
        left = stats[i, cv2.CC_STAT_LEFT]
        spans.append((left, left + stats[i, cv2.CC_STAT_WIDTH]))
    spans.sort()
    merged = 0
    reach = -1
    for left, right in spans:
        if left > reach:
            merged += 1
            reach = right
        else:
            reach = max(reach, right)
    return merged


def check(path: Path, yaw: int, control: np.ndarray) -> tuple[str, bool]:
    people = figure_count(path)
    area, eye_ratio = face_metrics(path)
    geometry = below_head_iou(path, control)
    problems = []
    if people != 1:
        problems.append(f"人數 {people}")
    if geometry < 0.50:
        problems.append(f"頸下 IoU {geometry:.3f} 過低（純 t2i 基準 0.364）")
    # 剪影 IoU 分不出正反——A-pose 的正反剪影幾乎相同，v11 初版就是正面控制圖
    # 產出背面而 IoU 仍給 0.573「通過」。臉部「有沒有偵測到」也分不出，
    # YuNet 會在背面的髮髻上偵測出臉。只有眼距佔臉寬有乾淨間隔。
    if abs(yaw) <= 22 and eye_ratio < 0.35:
        problems.append(f"正面視角的眼距比 {eye_ratio:.3f} 過低（疑似正反顛倒）")
    if abs(yaw) >= 150 and eye_ratio >= 0.35:
        problems.append(f"背面視角卻量到正面的眼距比 {eye_ratio:.3f}")
    summary = (f"人數 {people}  頸下IoU {geometry:.3f}  "
               f"臉部 {area:.4f}  眼距比 {eye_ratio:.3f}")
    return (summary + "  " + "；".join(problems) if problems else summary + "  通過",
            not problems)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    from diffusers import (
        ChromaImg2ImgPipeline, ChromaTransformer2DModel, GGUFQuantizationConfig,
    )

    # 排序刻意把原生視角（yaw <= 0 與 180）排在前面。那 13 張在「直接生成 24 張」
    # 與「生 13 張再水平鏡像出 +yaw」兩種方案下都需要，先跑完就不會做白工，
    # 也不必在出跑前先要到鏡像與否的裁決。
    folders = sorted(
        (f for f in BUNDLES.iterdir() if f.is_dir()),
        key=lambda f: (formal_yaw(f.name) > 0, abs(formal_yaw(f.name))),
    )
    native = sum(1 for f in folders if formal_yaw(f.name) <= 0)
    print(f"bundles {len(folders)}（原生視角 {native} 張優先）", flush=True)

    transformer = ChromaTransformer2DModel.from_single_file(
        str(GGUF),
        quantization_config=GGUFQuantizationConfig(compute_dtype=torch.bfloat16),
        torch_dtype=torch.bfloat16,
    )
    pipe = ChromaImg2ImgPipeline.from_pretrained(
        "lodestones/Chroma1-HD", transformer=transformer, torch_dtype=torch.bfloat16
    )
    load_aitoolkit_chroma_lora(pipe, LORA, weight=LORA_WEIGHT)
    pipe.enable_model_cpu_offload()
    pipe.set_progress_bar_config(disable=True)
    print(f"v11 ready @ strength {STRENGTH} LoRA {LORA_WEIGHT} {WIDTH}x{HEIGHT}",
          flush=True)

    gated = False
    report = []
    for folder in folders:
        yaw = formal_yaw(folder.name)
        target = OUT / f"body2-yaw{yaw:+04d}.png"
        if target.exists():
            gated = True
            continue
        image = pipe(
            prompt=(
                "mhn_identity, a full-body studio photograph of a beautiful young "
                f"East Asian woman, {HAIR}, elegant classical Chinese facial "
                f"features, {BODY}, {ARMS}. {orientation(yaw)}. {TAIL}"
            ),
            negative_prompt=NEG_ARMS + NEG,
            image=tinted_init(folder, (WIDTH, HEIGHT), hair_hint=True),
            strength=STRENGTH,
            height=HEIGHT, width=WIDTH,
            num_inference_steps=34, guidance_scale=5.0,
            generator=torch.Generator(device="cpu").manual_seed(7),
        ).images[0]
        image.save(target)
        verdict, ok = check(target, yaw, control_mask(folder))
        report.append((yaw, verdict))
        print(f"done {target.name} :: {verdict}", flush=True)

        if not gated:
            gated = True
            if not ok:
                print("GATE_FAILED 第一張未通過，停止量產", flush=True)
                return
            print("GATE_PASSED 繼續量產", flush=True)

    print("── 彙總 ──", flush=True)
    for yaw, verdict in report:
        print(f"yaw{yaw:+05d}  {verdict}", flush=True)
    print("V11_GEO_DONE", flush=True)


if __name__ == "__main__":
    main()
