from __future__ import annotations

lazy import re
lazy import string
lazy import sys
lazy from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from flagship_ui_localization import FlagshipTranslator

VISION_UI_SOURCES = (
    "啟用墨寒本機視覺感知",
    "辨識我已明確登錄的臉部身分",
    "允許墨寒主動寒暄與關心",
    "安靜（不主動寒暄）",
    "適度（推薦）",
    "積極（較常主動關心）",
    "套用靈視設定",
    "登錄我的臉部身分",
    "刪除全部臉部身分",
    "刪除選取的臉部身分",
    "編輯多情境陪伴詞庫",
    "已登錄身分",
    "<b>主動陪伴</b>",
    "主動程度",
    "短暫離席不問候（分鐘）",
    "安靜多久後主動關心（分鐘）",
    "臉部身分登錄",
    "請先啟用靈視與臉部身分辨識。",
    "墨寒辨識到你時使用的稱呼",
    "無法開始臉部登錄：{error}",
    "這會刪除本機加密的臉部特徵，且無法復原。是否繼續？",
    "這會刪除選取的本機加密臉部特徵。是否繼續？",
    "已刪除全部臉部身分。",
    "多情境陪伴詞庫",
    "每行一句；留白時使用公開版中性預設。",
    "靈視環境已就緒",
    "正在登錄臉部：{current}/{total}",
    "已完成 {name} 的臉部登錄。",
    "請讓畫面中只出現一張清楚的正面臉孔。",
    "短暫回座",
    "一般歸來",
    "久候歸來",
    "早晨相見",
    "深夜歸來",
    "帶著飲品",
    "帶著書本",
    "寒暄與主動關心",
    "歸來問候",
    "日常關心",
    "健康提醒",
    "特殊節日",
    "用膳提醒・首次",
    "用膳提醒・克制加強",
    "飲水提醒・首次",
    "飲水提醒・克制加強",
    "休息提醒・首次",
    "休息提醒・克制加強",
    "久坐提醒・首次",
    "久坐提醒・克制加強",
    "墨寒生日・含蓄暗示",
    "墨寒生日・小聲埋怨",
    "情人節・含蓄暗示",
    "情人節・小聲埋怨",
    "聖誕節・含蓄暗示",
    "聖誕節・小聲埋怨",
)

HAN_CHARACTER = re.compile(r"[\u3400-\u9fff]")


def _fields(value: str) -> set[str]:
    return {
        field_name
        for _, field_name, _, _ in string.Formatter().parse(value)
        if field_name is not None
    }


def test_vision_ui_has_complete_four_language_contract() -> None:
    translators = {
        language: FlagshipTranslator(language)
        for language in ("zh-CN", "en", "ja-JP")
    }
    for source in VISION_UI_SOURCES:
        for language, translator in translators.items():
            translated = translator.text(source)
            assert translated.strip()
            assert translated != source
            assert _fields(translated) == _fields(source)
            if language == "en":
                assert not HAN_CHARACTER.search(translated)


def test_vision_ui_runtime_values_are_preserved() -> None:
    english = FlagshipTranslator("en")
    japanese = FlagshipTranslator("ja-JP")
    assert english.text(
        "正在登錄臉部：{current}/{total}", current=3, total=5
    ) == "Enrolling face: 3/5"
    assert japanese.text(
        "已完成 {name} 的臉部登錄。", name="主上"
    ) == "主上 の顔登録が完了しました。"


if __name__ == "__main__":
    test_vision_ui_has_complete_four_language_contract()
    test_vision_ui_runtime_values_are_preserved()
    print("FLAGSHIP_VISION_LOCALIZATION_OK")
