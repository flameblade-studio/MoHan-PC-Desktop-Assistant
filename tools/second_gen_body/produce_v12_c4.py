"""v12：以 candidate4-P25 控制圖 + 兩段式，量產 24 視角素體。

與 v11 的差別，每一項都對應一個已查證的問題：

  控制圖換成 candidate4-P25   上臂從 34.4 cm（常模第 94 百分位）降到 24.5 cm；
                              成品會忠實繼承控制網格，網格不改，調任何擴散參數都沒用
  yaw 不再取負號              bundle 資料夾名本來就是 formal view id（yaw+090 的
                              formal_yaw 就是 +90），v10/v11 又多取一次負號，
                              每張輸出都被貼上相反的角度標籤，24 視角序列會反向
  染色保留對比                窄帶重映射把明暗動態範圍壓掉 28%，而明暗承載正反資訊，
                              正面因此連兩次翻成背面
  兩段式                      單段做不到幾何與外觀兼得：0.85 正面翻背面、
                              0.75 若染色壓縮明暗則臉糊。第一段鎖方位、第二段修外觀，
                              實測第二段的頸下 IoU 只變動 0.004

閘門在第一張就檢查人數、頸下 IoU、正反方向，不過就停，不讓 24 張帶同一缺陷跑完。
"""
import os
import sys
from pathlib import Path

import numpy as np
import torch

# 本檔原於 session 暫存目錄開發，匯入路徑與資料根目錄都寫死。入庫時改為：
#   匯入路徑取自本檔所在目錄；資料根目錄可用 MOHAN_VISION_ROOT 覆寫，
#   預設保留原機器路徑，讓既有紀錄可重現。
sys.path.insert(0, str(Path(__file__).resolve().parent))
from thresholds import (
    BACKGROUND_DISTANCE,
    BACK_MIN,
    BINARY_MIDPOINT,
    CHEST_BAND,
    CHEST_GARMENT_MIN,
    EYE_SPAN_FRONT_MIN,
    EYE_SPAN_TURNED_MIN,
    FRONT_MAX,
    GARMENT_CHECK_MAX_YAW,
    MAX_FAILED_VIEWS,
    SILHOUETTE_ON,
    SKIN_WARM_MARGIN,
    THREE_QUARTER_MAX,
    THREE_QUARTER_MIN,
)
from lora_loader import load_aitoolkit_chroma_lora
from chroma_mass_produce_v9 import BODY, HAIR, LORA, TAIL, GGUF
from produce_v10_geo import NEG
from produce_v11_geo import (
    ARMS, NEG_ARMS, below_head_iou, face_metrics, figure_count, orientation,
    orientation_negative,
)
from tinted_init import tinted_from_paths

ROOT = Path(os.environ.get(
    "MOHAN_VISION_ROOT",
    r"D:\FlamebladeStudio\CodexProjects\2026-08-13\mohan-multisensory-vision",
))
# candidate6 = candidate4 的四肢圍度 + DQS 放下的手臂（取代 candidate5 的 LBS 版）。
# 不可退回 candidate4：出貨中的 assets/pose-atlas/v4 是實機全身展示資產，
# A-pose 會直接出現在使用者眼前，且 DLC 服裝是疊在素體上，張臂對不上垂袖。
CONTROLS = ROOT / "work/second-gen-body/candidate6-controls"
OUT = ROOT / "work/second-gen-body/chroma-views-v12-c4"
OUT.mkdir(parents=True, exist_ok=True)
WIDTH, HEIGHT = 832, 1248
STAGE1, STAGE2 = 0.75, 0.60
LORA_WEIGHT = 0.85
# 轉盤順序：0 度起繞一圈。第一張是正面，也是最容易翻面的視角，適合當閘門。
VIEWS = list(range(0, 181, 15)) + list(range(-165, 0, 15))
# 重試階梯：換種子治不了系統性的角度吸附——yaw+060 兩組種子都超轉到約 90 度。
# 擴散模型有離散的鏡頭模式（正面／四分之三／側面／背面），中間角度會被拉向
# 最近的那個。對策是讓第一段的幾何更強勢（降 strength），同時把外觀修復
# 交給更強的第二段，維持兩段式「一段管幾何、一段管外觀」的分工。
# 第一組必須維持 (0.75, 0.60, 7, 11)，才與已產出的 yaw+000~+045 同源。
ATTEMPTS = (
    (0.75, 0.60, 7, 11),
    (0.68, 0.66, 20260831, 4157),
    (0.60, 0.72, 99173, 60422),
)


def control_mask(formal: int) -> np.ndarray:
    """控制剪影套用與初始圖完全相同的裁切幾何。"""
    from PIL import Image
    mask = Image.open(CONTROLS / f"yaw{formal:+04d}-pitch+00_silhouette.png").convert("L")
    inside = np.asarray(mask) > SILHOUETTE_ON
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
    return np.asarray(cropped.resize((WIDTH, HEIGHT), Image.NEAREST)) > BINARY_MIDPOINT


_CONTROL_CACHE: dict[int, np.ndarray] = {}


def all_controls() -> dict[int, np.ndarray]:
    if not _CONTROL_CACHE:
        for view in VIEWS:
            _CONTROL_CACHE[view] = control_mask(view)
    return _CONTROL_CACHE


def figure_mask(path: Path) -> np.ndarray:
    from PIL import Image
    array = np.asarray(Image.open(path).convert("RGB")).astype(np.int16)
    corners = np.concatenate([
        array[:40, :40].reshape(-1, 3), array[:40, -40:].reshape(-1, 3),
        array[-40:, :40].reshape(-1, 3), array[-40:, -40:].reshape(-1, 3),
    ])
    return np.abs(array - np.median(corners, axis=0)).sum(axis=2) > BACKGROUND_DISTANCE


def lower_body(mask: np.ndarray) -> np.ndarray:
    """髖部以下。手臂搆不到這裡，是唯一不受手臂姿勢污染的角度訊號。

    控制圖是 A-pose 張臂、成品依提示詞是雙臂垂放。這個姿勢差異會讓全身剪影
    變窄，於是更像「轉更多的控制圖」——實測 yaw+075 的全身峰值誤落在 +090，
    改用下半身後正確回到 +075（IoU 0.720）。當時我只拿下半身驗過 +060，
    沒回頭重驗 +075，就宣稱手臂不是原因，那個推廣是錯的。
    """
    rows = np.where(mask.any(axis=1))[0]
    top, bottom = rows[0], rows[-1]
    return mask[top + int((bottom - top) * 0.52):bottom]


def garment_fraction(path: Path, low: float, high: float) -> float:
    """指定身高帶內「非膚色布料」的像素佔比。

    膚色偏暖（R 明顯大於 B），這套泳裝是淺灰藍（R 約等於或小於 B），
    所以用 R-B 當判別量，不需固定色票。實測有上衣 0.123~0.344、
    無上衣 0.046~0.059，門檻 0.09 落在間隙中央。正樣本 4 個、負樣本 2 個，
    樣本少，是絆線不是證明。
    """
    from PIL import Image
    array = np.asarray(Image.open(path).convert("RGB")).astype(np.int16)
    body = figure_mask(path)
    rows = np.where(body.any(axis=1))[0]
    top, bottom = rows[0], rows[-1]
    height = bottom - top
    band = np.zeros_like(body)
    band[top + int(height * low):top + int(height * high)] = True
    selected = body & band
    if not selected.any():
        return 0.0
    difference = (array[..., 0] - array[..., 2])[selected]
    return float((difference <= SKIN_WARM_MARGIN).mean())


def angle_match(path: Path, yaw: int) -> tuple[int, float, bool]:
    """這張圖最像哪一個角度的控制圖。

    固定門檻（例如「IoU 要 ≥0.50」）不能判角度：實測一張正確的 45 度圖只有
    0.528，而斜角本來就比正面低。要判的是**峰值落在哪裡**——
    量對全部 24 組控制圖的 IoU，最高的那個就是這張圖的角度。

    front/back 的並列必須容忍：A-pose 的正反剪影完全相同，+045 與 +135
    的 IoU 一模一樣，所以只要求「要求的角度落在前兩名」，正反由眼距比另外判。
    """
    band = lower_body(figure_mask(path))
    scores = {}
    for view, mask in all_controls().items():
        reference = lower_body(mask)
        height = min(len(band), len(reference))
        a, b = band[-height:], reference[-height:]
        union = np.logical_or(a, b).sum()
        scores[view] = float(np.logical_and(a, b).sum()) / union if union else 0.0
    ranked = sorted(scores, key=scores.get, reverse=True)
    return ranked[0], scores[ranked[0]], yaw in ranked[:2]


def check(path: Path, yaw: int, control: np.ndarray) -> tuple[str, bool]:
    people = figure_count(path)
    area, eye = face_metrics(path)
    geometry = below_head_iou(path, control)
    peak, peak_score, matched = angle_match(path, yaw)
    problems = []
    if people != 1:
        problems.append(f"人數 {people}")
    if not matched:
        problems.append(f"角度不符：最像 yaw{peak:+04d}（{peak_score:.3f}）")
    # 服裝檢查。閘門原本完全沒查這一項，yaw+015 整件上衣消失卻一路通過，
    # 是擁有者用眼睛抓到的。
    #
    # 有效範圍只到 |yaw| <= 90——門檻 0.09 是拿 0/15/30/45/75/90 的樣本
    # 校準的（0.121~0.344）。實測 yaw+105 的上衣明明在身上卻只有 0.085，
    # 因為胸前已大半轉離鏡頭。**本輪已三次把某範圍內校準的門檻套到範圍外**
    # （單一視角的強度曲線當通則、眼距比套到側面帶、服裝門檻套到後四分之三），
    # 所以每個門檻都必須帶著它的有效範圍，範圍外一律回報「不適用」而非硬判。
    chest = (garment_fraction(path, *CHEST_BAND)
             if abs(yaw) <= GARMENT_CHECK_MAX_YAW else None)
    if chest is not None and chest < CHEST_GARMENT_MIN:
        problems.append(f"胸前布料佔比 {chest:.3f} 過低（疑似上衣消失）")
    # 眼距比只在「臉大致朝向鏡頭」的角度帶有意義。
    #
    # 68-112 度是純側面，只看得到一隻眼，眼距必然極小——實測一張乾淨正確的
    # 90 度側面只有 0.064，被 0.20 的門檻誤殺。那個門檻是拿 v9 的「45/90 度」
    # 樣本（0.303/0.330）校準的，而 **v9 的角度是壓縮過的**，它的「90 度」
    # 根本不是真正的側面。用角度不準的樣本去校準角度相關的門檻，等於用壞尺
    # 量長度——本輪已經因此犯錯兩次，v9 不可再當角度基準。
    #
    # 側面帶的方位正確性改由角度指標（下半身剪影峰值）負責，那個指標在
    # yaw+090 給出 0.721，是全部視角裡最高的幾個之一。
    angle = abs(yaw)
    if angle <= FRONT_MAX and eye < EYE_SPAN_FRONT_MIN:
        problems.append(f"正面眼距比 {eye:.3f} 過低（疑似正反顛倒）")
    elif THREE_QUARTER_MIN <= angle <= THREE_QUARTER_MAX and eye < EYE_SPAN_TURNED_MIN:
        problems.append(f"{angle} 度視角的眼距比 {eye:.3f} 過低（疑似轉成背面）")
    elif angle >= BACK_MIN and eye >= EYE_SPAN_FRONT_MIN:
        problems.append(f"背面卻量到正面眼距比 {eye:.3f}")
    summary = (f"人數 {people}  最像 yaw{peak:+04d}({peak_score:.3f})"
               f"  眼距比 {eye:.3f}  胸前布料 "
               + (f"{chest:.3f}" if chest is not None else "不適用")
               + f"  頸下IoU {geometry:.3f}")
    return (summary + "  " + "；".join(problems) if problems else summary + "  通過",
            not problems)


class RunLock:
    """拒絕第二個實例同時寫入同一個輸出目錄。

    2026-08-31 實際事故：修完閘門後直接啟動新的量產卻沒停掉前一個，兩個程序
    交錯寫入同一目錄，新程序判定通過的 body2-yaw+120.png 被舊程序的重試邏輯
    改名成 _rejected-try2——一個程序的重試摧毀了另一個程序的合格產出。
    症狀只有時間戳錯序看得出來（被改名的檔案時間晚於後續視角的成品），
    日誌照樣顯示「通過」，單看日誌抓不到。

    這件事寫成紀律沒有用——「不要同時跑兩個」本來就是已知的坑，卻仍然發生。
    所以改由程式擋：偵測到活著的另一個實例就直接退出。
    """

    def __init__(self, directory: Path) -> None:
        self.path = directory / ".produce.lock"

    def __enter__(self) -> "RunLock":
        if self.path.exists():
            holder = self.path.read_text(encoding="utf-8").strip()
            if self._alive(holder):
                raise SystemExit(
                    f"另一個量產實例仍在執行（{holder}）。同時寫入同一個輸出目錄會讓\n"
                    f"其中一方的重試邏輯刪掉另一方的合格產出。請先停止它，或刪除\n"
                    f"{self.path} 若確定該程序已不存在。")
            print(f"清除已失效的鎖檔（{holder}）", flush=True)
        self.path.write_text(str(os.getpid()), encoding="utf-8")
        return self

    def __exit__(self, *_exc: object) -> None:
        self.path.unlink(missing_ok=True)

    @staticmethod
    def _alive(pid_text: str) -> bool:
        """程序是否仍在執行。

        **不要用 os.kill(pid, 0)。** 第一版這樣寫，兩個缺陷同時存在：
        在 Windows 上它對活著的程序拋出 OSError，於是守衛在唯一該生效的情境
        （另一個實例正在跑）失效；更糟的是 Windows 的 os.kill 對非 CTRL 訊號
        會呼叫 TerminateProcess——一支用來「偵測」的函式有可能直接殺掉
        它想偵測的程序。實測時 PID 是正在跑的量產，僥倖只拋例外沒被終止。

        改為：Windows 走 OpenProcess + GetExitCodeProcess，POSIX 才用
        os.kill(pid, 0)（該平台上這是標準且無副作用的存在探測，
        PermissionError 代表程序存在但無權限，仍算活著）。
        """
        try:
            pid = int(pid_text)
        except ValueError:
            return False
        if pid <= 0 or pid == os.getpid():
            return False
        if sys.platform == "win32":
            import ctypes
            PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
            STILL_ACTIVE = 259
            kernel32 = ctypes.windll.kernel32
            handle = kernel32.OpenProcess(
                PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
            if not handle:
                return False
            try:
                code = ctypes.c_ulong()
                if not kernel32.GetExitCodeProcess(handle, ctypes.byref(code)):
                    return False
                return code.value == STILL_ACTIVE
            finally:
                kernel32.CloseHandle(handle)
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return False
        except PermissionError:
            return True
        return True


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    with RunLock(OUT):
        _run()


def _run() -> None:
    from diffusers import (
        ChromaImg2ImgPipeline, ChromaTransformer2DModel, GGUFQuantizationConfig,
    )

    missing = [v for v in VIEWS
               if not (CONTROLS / f"yaw{v:+04d}-pitch+00_shaded-render.png").exists()]
    if missing:
        raise SystemExit(f"缺控制圖：{missing}")
    print(f"控制圖 {len(VIEWS)} 組齊備（candidate6-P25-DQS）", flush=True)

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
    print(f"v12 ready：兩段式 {STAGE1}/{STAGE2}，LoRA {LORA_WEIGHT}，{WIDTH}x{HEIGHT}",
          flush=True)

    gated = False
    report: list = []
    failures: list[int] = []
    for yaw in VIEWS:
        target = OUT / f"body2-yaw{yaw:+04d}.png"
        if target.exists():
            gated = True
            continue
        init = tinted_from_paths(
            CONTROLS / f"yaw{yaw:+04d}-pitch+00_shaded-render.png",
            CONTROLS / f"yaw{yaw:+04d}-pitch+00_silhouette.png",
            (WIDTH, HEIGHT), hair_hint=True, preserve_contrast=True,
        )
        prompt = (
            "mhn_identity, a full-body studio photograph of a beautiful young East "
            f"Asian woman, {HAIR}, elegant classical Chinese facial features, "
            f"{BODY}, {ARMS}. {orientation(yaw)}. {TAIL}"
        )

        negative = orientation_negative(yaw) + NEG_ARMS + NEG

        def run(image, strength, seed):
            return pipe(
                prompt=prompt, negative_prompt=negative, image=image,
                strength=strength, height=HEIGHT, width=WIDTH,
                num_inference_steps=34, guidance_scale=5.0,
                generator=torch.Generator(device="cpu").manual_seed(seed),
            ).images[0]

        # 換種子重試：yaw+045 曾在髖部長出畸形的多餘肢體，負向詞的
        # extra limbs / deformed 沒擋住。這類是取樣的隨機缺陷，不是配方問題，
        # 對策是換種子重抽，不是放寬門檻——第一次看到 IoU 0.498 時我以為是
        # 門檻訂太嚴，開圖才發現是真的畸形。指標說有問題就先信它。
        control = control_mask(yaw)
        ok, verdict = False, ""
        for attempt, (s1, s2, seed1, seed2) in enumerate(ATTEMPTS, start=1):
            # 已經跑過且失敗的參數組合不要重跑。生成是確定性的，同參數同種子
            # 必得同圖，重跑只是把已知的失敗再算一次。yaw+060 的三個階梯就
            # 因為缺這道判斷而被重算了第二輪，白費半小時。
            archived = OUT / f"_rejected-yaw{yaw:+04d}-try{attempt}.png"
            if archived.exists():
                print(f"skip yaw{yaw:+04d} 第 {attempt} 次（已知失敗）", flush=True)
                continue
            first = run(init, s1, seed1)
            second = run(first, s2, seed2)
            second.save(target)
            (OUT / f"_stage1-yaw{yaw:+04d}.png").unlink(missing_ok=True)
            first.save(OUT / f"_stage1-yaw{yaw:+04d}.png")
            verdict, ok = check(target, yaw, control)
            suffix = "" if attempt == 1 else f"（第 {attempt} 次：s1={s1} s2={s2}）"
            print(f"done body2-yaw{yaw:+04d}{suffix} :: {verdict}", flush=True)
            if ok:
                break
            target.replace(OUT / f"_rejected-yaw{yaw:+04d}-try{attempt}.png")
        report.append((yaw, verdict))

        if not ok:
            failures.append(yaw)
            print(f"REJECTED yaw{yaw:+04d}：{len(ATTEMPTS)} 次嘗試皆未通過"
                  f"（累計 {len(failures)}）", flush=True)
            # 閘門只看第一張是不夠的：yaw+030 的轉背失敗出現在第三張。
            # 每個視角都已重試過，仍失敗兩個視角代表是系統性問題，停下來。
            if len(failures) >= MAX_FAILED_VIEWS:
                print(f"GATE_FAILED 累計 {len(failures)} 個視角未通過：{failures}，停止量產",
                      flush=True)
                return
        elif not gated:
            gated = True
            print("GATE_PASSED 繼續量產", flush=True)

    print("── 彙總 ──", flush=True)
    for yaw, verdict in report:
        print(f"yaw{yaw:+05d}  {verdict}", flush=True)
    print(f"未通過視角：{failures}" if failures else "全部通過", flush=True)
    print("V12_C4_DONE", flush=True)


if __name__ == "__main__":
    main()
