from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ui_localization import _ENGLISH, _SIMPLIFIED_CHINESE
from ui_localization_ja import JAPANESE_UI


def main() -> None:
    translations = {
        "en": _ENGLISH,
        "zh-CN": _SIMPLIFIED_CHINESE,
        "ja-JP": JAPANESE_UI,
    }
    expected_keys = set(_ENGLISH)
    for language, values in translations.items():
        assert set(values) == expected_keys, language
        assert all(str(value).strip() for value in values.values()), language

    app_source = (ROOT / "app.py").read_text(encoding="utf-8")
    used_keys = set(
        re.findall(r'(?:self\.)?_t\(\s*["\']([^"\']+)', app_source)
    )
    for language, values in translations.items():
        missing = used_keys - set(values)
        assert not missing, f"{language} missing UI keys: {sorted(missing)}"

    assert "<b>歡迎使用墨寒桌面陪伴工作助理</b>" in app_source
    assert "墨寒" in _SIMPLIFIED_CHINESE["first_run_heading"]
    assert "MoHan" in _ENGLISH["first_run_heading"]
    assert "墨寒" in JAPANESE_UI["first_run_heading"]
    print("TRANSLATION_COMPLETENESS_OK")


if __name__ == "__main__":
    main()
