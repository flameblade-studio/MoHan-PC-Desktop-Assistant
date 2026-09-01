"""出貨檔案不得含作者機器的絕對路徑或使用者名稱。

2026-09-01 的安全稽核發現 assets/pose-atlas/v4-layered/ 底下兩個 JSON
帶著磁碟機代號、專案目錄與 Windows 使用者名稱，而那個目錄會被打包進
安裝檔——每一位下載者都拿得到。不是憑證外洩，但既無意義又不可攜：
換一台機器重建就對不上。

寫成測試而不是一次性清理，是因為產生器會重新寫出這些檔案。清了不擋，
下次重建又回來；擋住了，CI 會在合併前就攔下，不必等下一次稽核。

範圍刻意只涵蓋**會出貨的路徑**。artifacts/ 是工作證據與一次性腳本，
不隨產品散布，用同一把尺去量它只會製造噪音。
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# 會被打包進安裝檔或直接構成產品的目錄。
SHIPPED = (
    "assets",
    "domain",
    "application",
    "infrastructure",
    "integrations",
    "presentation",
)
# 這些副檔名才檢查——二進位資產不必掃，也掃不出有意義的結果。
TEXT_SUFFIXES = {".json", ".py", ".md", ".toml", ".cfg", ".txt", ".yml", ".yaml"}

# Windows 磁碟機絕對路徑（C:\... 或 C:/...），以及 POSIX 的家目錄。
# JSON 會把反斜線跳脫成 \\，所以兩種都要匹配。
PATTERNS = (
    re.compile(r"[A-Za-z]:\\{1,2}(?:Users|使用者)\\{1,2}", re.IGNORECASE),
    re.compile(r"[A-Za-z]:/Users/", re.IGNORECASE),
    re.compile(r"/(?:home|Users)/[A-Za-z0-9_.-]+/"),
    re.compile(r"[A-Za-z]:\\{1,2}FlamebladeStudio", re.IGNORECASE),
    re.compile(r"[A-Za-z]:/FlamebladeStudio", re.IGNORECASE),
)


def _shipped_text_files() -> list[Path]:
    files: list[Path] = []
    for folder in SHIPPED:
        base = ROOT / folder
        if not base.is_dir():
            continue
        for path in base.rglob("*"):
            if path.is_file() and path.suffix.lower() in TEXT_SUFFIXES:
                if "__pycache__" in path.parts:
                    continue
                files.append(path)
    return files


def test_shipped_files_have_no_personal_absolute_paths() -> None:
    offenders: list[str] = []
    for path in _shipped_text_files():
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for pattern in PATTERNS:
            match = pattern.search(text)
            if match:
                line = text[: match.start()].count("\n") + 1
                offenders.append(
                    f"{path.relative_to(ROOT).as_posix()}:{line} → "
                    f"{match.group(0)!r}"
                )
                break
    assert not offenders, (
        "出貨檔案不得含作者機器的絕對路徑：\n  " + "\n  ".join(offenders)
    )


def test_guard_actually_matches_a_known_bad_string() -> None:
    """守衛自己要先被驗證：正例必須真的被抓到。

    只有負樣本的門檻不算驗證過——這是本專案 2026-09-01 記下的紀律。
    這裡用實際洩漏過的字串當正例，確認樣式沒有寫壞。
    """
    samples = (
        r"C:\Users\hitos\.codex\attachments\x.txt",
        "C:\\\\Users\\\\hitos\\\\.codex",      # JSON 跳脫後的形式
        r"D:\FlamebladeStudio\CodexProjects\2026-08-13",
        "/home/someone/project",
    )
    for sample in samples:
        assert any(p.search(sample) for p in PATTERNS), f"守衛漏掉了 {sample!r}"


def test_guard_does_not_match_legitimate_text() -> None:
    """反例：正常內容不得被誤判，否則守衛會變成噪音。"""
    samples = (
        "assets/pose-atlas/v4-layered",
        "使用者可以在設定裡選擇唯讀或可寫入",
        "@hitoshic1982",                        # 刻意公開的維護者帳號
        "Path.home() / '.mohan'",
        "https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant",
    )
    for sample in samples:
        assert not any(p.search(sample) for p in PATTERNS), f"守衛誤判了 {sample!r}"
