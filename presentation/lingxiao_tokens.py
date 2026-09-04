"""墨寒・凌霄（Lingxiao）設計 token：控制中心唯一的色彩、字級、間距與動效來源。

擁有者 2026-09-02 裁定：以 A「墨金・凌霄」為基底（墨黑漆底、金線飾角、玉青正向、
硃砂危險），B／C 方向走主題包重染。這個模組只放**值**與極少量純函式，讓
flagship_theme.py 的樣式表、lingxiao_widgets.py 的自繪元件與測試共用同一組數字。

對比：每一組會在同一條 QSS 規則裡同時出現的「文字色／背景色」都列在
TEXT_ON_SURFACE_PAIRS，測試逐對驗 WCAG 1.4.3（≥ 4.5:1）。高對比模式改用更黑的地
與更亮的金／月白，其餘 token 相同。
"""
from __future__ import annotations

lazy import ctypes
lazy import os
lazy from dataclasses import dataclass
lazy from typing import Final

__all__ = (
    "LingxiaoPalette",
    "MOTION",
    "PALETTE",
    "PALETTE_HIGH_CONTRAST",
    "TEXT_ON_SURFACE_PAIRS",
    "TYPE_SCALE",
    "contrast_ratio",
    "font_stack",
    "palette_for",
    "reduced_motion_requested",
)


@dataclass(frozen=True, slots=True)
class LingxiaoPalette:
    """凌霄色板。名字取自材質而非用途，用途在樣式表裡指定。"""

    ink: str          # 頁面地、舞台底
    ink_deep: str     # 更深一層（輸入框、清單底）
    lacquer: str      # 面板第一層
    lacquer_2: str    # 面板第二層（浮起的卡）
    line: str         # 邊線
    moon: str         # 主文字
    mist: str         # 說明文字、標籤
    dim: str          # 最弱的提示字
    gold: str         # 強調、飾角、主鈕邊
    gold_2: str       # 亮金：標題、主鈕文字
    gold_dim: str     # 暗金：主鈕邊、釘選邊
    jade: str         # 正向狀態
    amber: str        # 警示（AMBER 級）
    cinnabar: str     # 危險（RED 級、緊急停止）
    cinnabar_text: str  # 硃砂底上的可讀文字
    sky: str          # 資訊（BLUE 級）
    on_gold: str      # 金底上的文字
    selection: str    # 選取底（配白字）


PALETTE: Final = LingxiaoPalette(
    ink="#0b1220",
    ink_deep="#070d18",
    lacquer="#131c2e",
    lacquer_2="#1a2540",
    line="#2b3a57",
    moon="#f1ebdd",
    mist="#a7b3c6",
    dim="#6f7d95",
    gold="#d9b26f",
    gold_2="#f0d194",
    gold_dim="#8e7647",
    jade="#4fb3a5",
    amber="#e0a43a",
    cinnabar="#d2523a",
    cinnabar_text="#ffd9cf",
    sky="#6fa7d9",
    on_gold="#0b1220",
    selection="#7a5a1e",
)

PALETTE_HIGH_CONTRAST: Final = LingxiaoPalette(
    ink="#000000",
    ink_deep="#000000",
    lacquer="#0a0f1a",
    lacquer_2="#111a2b",
    line="#5a6a85",
    moon="#ffffff",
    mist="#d6dde8",
    dim="#aab5c6",
    gold="#f3cf7a",
    gold_2="#ffe2a3",
    gold_dim="#c9a75a",
    jade="#7fe0d2",
    amber="#ffc65c",
    cinnabar="#ff7a5c",
    cinnabar_text="#ffffff",
    sky="#9cc9ff",
    on_gold="#000000",
    selection="#4a3a10",
)

# 字級（px，scale=1.0）：標籤／內文／強調內文／卡題／頁題／區題／品牌。
TYPE_SCALE: Final = frozendict(
    {
        "label": 12,
        "body": 14,
        "body_strong": 15,
        "card_title": 17,
        "page_title": 24,
        "section_title": 30,
        "brand": 22,
        "numeral": 16,
    }
)

# 動效預算（毫秒）。擁有者要「更華麗」：切頁、光暈、呼吸、粒子都開，
# 但一律受 reduced_motion_requested() 控制，關掉就全部靜止。
MOTION: Final = frozendict(
    {
        "page_transition_ms": 260,
        "hover_glow_ms": 160,
        "press_ms": 90,
        "pulse_ms": 2800,
        "seal_press_ms": 240,
        "motes_frame_ms": 33,
        "motes_count": 26,
    }
)

# 同一條 QSS 規則裡會同時出現的文字／背景組合。測試逐對驗 4.5:1。
TEXT_ON_SURFACE_PAIRS: Final = (
    ("moon", "ink"),
    ("moon", "lacquer"),
    ("moon", "lacquer_2"),
    ("mist", "ink"),
    ("mist", "lacquer"),
    ("mist", "lacquer_2"),
    ("gold_2", "ink"),
    ("gold_2", "lacquer"),
    ("gold", "ink"),
    ("gold", "lacquer"),
    ("jade", "ink"),
    ("amber", "ink"),
    ("sky", "ink"),
    ("cinnabar_text", "ink"),
    ("on_gold", "gold"),
    ("on_gold", "gold_2"),
    ("moon", "ink_deep"),
)


def palette_for(*, high_contrast: bool) -> LingxiaoPalette:
    return PALETTE_HIGH_CONTRAST if high_contrast else PALETTE


def font_stack(role: str) -> str:
    """回傳 QSS 用的字型串。楷體與 Cinzel 若未隨附即逐級回退，不會空白。"""

    if role == "display":
        return '"LXGW WenKai TC", "DFKai-SB", "標楷體", "KaiTi", "Microsoft JhengHei UI"'
    if role == "caps":
        return '"Cinzel", "Georgia", "Times New Roman", serif'
    return '"LXGW WenKai TC", "Microsoft JhengHei UI", "Noto Sans TC", "PingFang TC", sans-serif'


_SRGB_LINEAR_THRESHOLD: Final = 0.04045


def _channel(value: float) -> float:
    if value <= _SRGB_LINEAR_THRESHOLD:
        return value / 12.92
    return ((value + 0.055) / 1.055) ** 2.4


def _luminance(color: str) -> float:
    red, green, blue = (int(color[index:index + 2], 16) / 255 for index in (1, 3, 5))
    return 0.2126 * _channel(red) + 0.7152 * _channel(green) + 0.0722 * _channel(blue)


def contrast_ratio(foreground: str, background: str) -> float:
    lighter, darker = sorted((_luminance(foreground), _luminance(background)), reverse=True)
    return (lighter + 0.05) / (darker + 0.05)


_SPI_GETCLIENTAREAANIMATION: Final = 0x1042


def reduced_motion_requested() -> bool:
    """使用者在 Windows 關掉「顯示動畫」時，凌霄的所有動效都要停。

    非 Windows 或查詢失敗時回 False（照常播放）：查不到不等於使用者要求靜止。
    """

    if os.name != "nt":
        return False
    try:
        enabled = ctypes.c_int(1)
        ok = ctypes.windll.user32.SystemParametersInfoW(
            _SPI_GETCLIENTAREAANIMATION, 0, ctypes.byref(enabled), 0
        )
    except (AttributeError, OSError):
        return False
    return bool(ok) and not bool(enabled.value)
