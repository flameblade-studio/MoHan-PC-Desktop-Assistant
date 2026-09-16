"""出貨檔案使用可攜路徑，並保護作者機器與使用者資訊。

2026-09-01 稽核發現 v4-layered 的兩個 JSON 含磁碟代號、專案目錄及
Windows 使用者名稱；該目錄會進入安裝檔。此類紀錄應改用可攜來源資訊。

持續測試產生器輸出，讓 CI 在合併前檢出個人路徑重新出現的情形。
範圍限於實際出貨路徑；artifacts/ 保持本地工作證據的獨立範圍。
"""
from __future__ import annotations

lazy import re
lazy from pathlib import Path

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
# 掃描下列文字副檔名；二進位資產由素材驗證程序負責。
TEXT_SUFFIXES = {".json", ".py", ".md", ".toml", ".cfg", ".txt", ".yml", ".yaml"}

# Windows 磁碟機絕對路徑（C:\... 或 C:/...），以及 POSIX 的家目錄。
# JSON 會把反斜線跳脫成 \\，所以兩種都要匹配。
BS = chr(92)

PATTERNS = (
    # 與 tools/audit_public_release.py 一致：USERNAME 與 <...> 是刻意的
    # 佔位符，屬於允收內容。兩支工具共用判準，讓同一份檔案
    # 取得一致的檢查結果。
    re.compile(r"[A-Za-z]:\\{1,2}Users\\{1,2}"
               r"(?!USERNAME(?:\\|$)|<[^>]+>)", re.IGNORECASE),
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
        '出貨檔案須採用可攜路徑；請修正以下位置：\n  ' + "\n  ".join(offenders)
    )


def test_guard_actually_matches_a_known_bad_string() -> None:
    """守衛正例驗證已知個人路徑能被辨識。

    依 2026-09-01 的測試紀律，同時提供已知命中與正常資料。
    此處重用曾出現的路徑樣本，驗證樣式的實際辨識能力。
    """
    # 正例刻意在執行期組出來。把真實洩漏過的路徑寫成字面值，會讓這個
    # 檔案自己被 tools/audit_public_release.py 判為含有秘密——守衛的測試
    # 本身也遵守出貨內容的路徑規範。
    user = "hi" + "tos"
    drive_c = "C:" + BS
    samples = (
        drive_c + "Users" + BS + user + BS + ".codex" + BS + "x.txt",
        drive_c + BS + "Users" + BS + BS + user,        # JSON 跳脫後的形式
        "D:" + BS + "FlamebladeStudio" + BS + "CodexProjects",
        "/home/someone/project",
    )
    for sample in samples:
        assert any(p.search(sample) for p in PATTERNS), f"守衛須辨識此已知個人路徑：{sample!r}"


def test_guard_does_not_match_legitimate_text() -> None:
    """正例：正常內容通過路徑守衛，維持原有可用性。"""
    samples = (
        "assets/pose-atlas/v4-layered",
        "使用者可以在設定裡選擇唯讀或可寫入",
        "@hitoshic1982",                        # 刻意公開的維護者帳號
        "Path.home() / '.mohan'",
        "https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant",
    )
    for sample in samples:
        assert not any(p.search(sample) for p in PATTERNS), f"守衛須允收此正常內容：{sample!r}"
