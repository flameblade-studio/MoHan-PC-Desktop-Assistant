"""Strict four-language localization boundary for the flagship control center."""

from __future__ import annotations

lazy import re
lazy from dataclasses import dataclass
lazy from typing import Any

lazy from domain.language_support import canonical_ui_language
lazy from presentation.flagship.localization_catalog import (
    merge_translation_catalogs,
)
lazy from presentation.flagship.localization_cloud_home import (
    CLOUD_HOME_TRANSLATIONS,
)
lazy from presentation.flagship.localization_interaction import (
    INTERACTION_TRANSLATIONS,
)
lazy from presentation.flagship.localization_remote_vision import (
    REMOTE_VISION_TRANSLATIONS,
)
lazy from presentation.flagship.localization_security_audit import (
    SECURITY_AUDIT_TRANSLATIONS,
)
lazy from presentation.flagship.localization_themes import THEME_TRANSLATIONS
lazy from presentation.flagship.localization_workflows import (
    WORKFLOW_TRANSLATIONS,
)

_TRANSLATION_INDEX = frozendict({"zh-CN": 0, "en": 1, "ja-JP": 2})

# Traditional Chinese remains the canonical source and public default. Keeping
# one ordered merged catalog preserves the legacy API while each responsibility
# has an independently maintainable owner.
FLAGSHIP_TRANSLATIONS = merge_translation_catalogs(
    INTERACTION_TRANSLATIONS,
    WORKFLOW_TRANSLATIONS,
    CLOUD_HOME_TRANSLATIONS,
    REMOTE_VISION_TRANSLATIONS,
    SECURITY_AUDIT_TRANSLATIONS,
    THEME_TRANSLATIONS,
)

_SYSTEM_PATTERNS = (
    (r"^安全政策已阻擋：(?P<reason>.*)$", "安全政策已阻擋：{reason}"),
    (r"^工具執行失敗：(?P<detail>.*)$", '工具執行需要處理：{detail}'),
    (r"^已開啟資料夾：(?P<value>.*)$", "已開啟資料夾：{value}"),
    (r"^已啟動：(?P<value>.*)$", "已啟動：{value}"),
    (r"^已建立檔案：(?P<value>.*)$", "已建立檔案：{value}"),
    (r"^找到 (?P<count>\d+) 個符合項目$", "找到 {count} 個符合項目"),
    (r"^已移動至：(?P<value>.*)$", "已移動至：{value}"),
    (r"^目前有 (?P<count>\d+) 個可見視窗$", "目前有 {count} 個可見視窗"),
    (r"^已切換至：(?P<value>.*)$", "已切換至：{value}"),
    (r"^已執行 (?P<value>.*)$", "已執行 {value}"),
)

_VISION_AUTHORIZATION_SUMMARY = (
    '公開版預設關閉。明確啟用並全域保存後，系統沿用持續授權處理所選事件，直到你主動關閉；狀態始終可見，並可設定配額與成本上限或立即撤銷。本機 OpenCV 獨立運作。'
)
_VISION_AUTHORIZATION_DETAILS = (
    '明確啟用並全域保存後，雲端視覺依所選事件與用量限制沿用持續授權，直到你主動關閉；狀態始終可見，並可設定配額與成本上限或立即撤銷。原始影像僅供即時處理，網路查詢由你明確決定。'
)


_SOURCE_COPY_ALIASES = frozendict({
    '{platform} 的原生安全金鑰保存尚未完成實機驗證，因此 OAuth 連線暫停；墨寒不會改用明文保存。': '{platform} 的原生安全金鑰保存等待實機驗證；OAuth 連線保持暫停，權杖僅採已驗證的加密保存。',
    '測試失敗：{error}': '測試需要處理：{error}',
    '尚未測試': '等待測試',
    '尚未完成 OAuth 連線': '請完成 OAuth 連線',
    '尚未連線 Google 或 Microsoft，或工具計畫未指定供應商': '請連線 Google 或 Microsoft，並在工具計畫指定供應商',
    '門鎖、警報與加熱設備永遠套用高風險政策。墨寒不能因對話內容自行降低安全等級。': '門鎖、警報與加熱設備永遠套用高風險政策，安全等級持續以明確授權為準。',
    '{platform} 的安全金鑰保存尚未完成實機驗證；Home Assistant 連線暫停，且不會儲存明文權杖。': '{platform} 的安全金鑰保存等待實機驗證；Home Assistant 連線保持暫停，權杖僅採已驗證的加密保存。',
    'Home Assistant 尚未啟用': '請啟用 Home Assistant',
    '尚未保存 Home Assistant 權杖': '請儲存 Home Assistant 權杖',
    '連線失敗：{error}': '連線需要處理：{error}',
    '讀取失敗：{error}': '讀取需要處理：{error}',
    '主動提醒設定無法讀取，已保留上一組有效值。': '讀取主動提醒設定需要處理，上一組有效值持續使用。',
    '可錄製手部特徵；不保存照片或影像。': '錄製僅保存手部特徵資料。',
    '目前沒有可用的手部 landmark 訊號，無法安全錄製。': '請先取得穩定的手部 landmark 訊號，再開始安全錄製。',
    '錄製已取消，沒有保存任何資料。': '錄製已取消，既有保存資料維持原樣。',
    '手勢辨識已就緒；不保存照片或影像。': '手勢辨識已就緒，保存內容僅限手部特徵資料。',
    '攝影機尚未就緒，手勢互動保持停用。': '攝影機就緒後即可啟用手勢互動。',
    '手部模型無法載入，手勢互動保持停用。': '請檢查手部模型載入狀態；手勢互動保持暫停。',
    '手勢辨識連續失敗，已安全停用。': '手勢辨識連續出現錯誤，已安全暫停，請檢查模型後再試。',
    '此手勢需要既有權限確認，尚未執行。': '完成既有權限確認後，才可執行此手勢。',
    '手勢動作執行失敗，未變更其他功能。': '手勢動作執行需要處理；其他功能維持運作。',
    '手勢設定尚未完成': '請完成手勢設定',
    '公開版預設關閉。明確啟用並全域保存後即持續授權，直到你主動關閉；系統不會逐幀詢問，狀態始終可見，並可設定配額與成本上限或立即撤銷。本機 OpenCV 不受此設定影響。': '公開版預設關閉。明確啟用並全域保存後，系統沿用持續授權處理所選事件，直到你主動關閉；狀態始終可見，並可設定配額與成本上限或立即撤銷。本機 OpenCV 獨立運作。',
    '✓ 原始影像不保存；設定檔不包含 API Key。': '✓ 原始影像僅供即時處理；API Key 由獨立安全儲存管理。',
    '明確啟用並全域保存後，雲端視覺會依所選事件與用量限制持續運作，直到你主動關閉；系統不會逐幀詢問，狀態始終可見，並可設定配額與成本上限或立即撤銷。原始影像不保存，也不會自動上網。': '明確啟用並全域保存後，雲端視覺依所選事件與用量限制沿用持續授權，直到你主動關閉；狀態始終可見，並可設定配額與成本上限或立即撤銷。原始影像僅供即時處理，網路查詢由你明確決定。',
    '● 雲端視覺服務目前無法使用': '● 雲端視覺服務需要處理',
    '攝影機預設關閉；啟用時必須顯示狀態。畫面不會默默上傳，也不會辨識未登錄的陌生人。': '攝影機預設關閉，啟用時持續顯示狀態；影像上傳須明確授權，身分辨識僅適用已登錄人物。',
    '本機臉部、虹膜與手勢模型尚未啟動': '本機臉部、虹膜與手勢模型等待啟動',
    '本機細緻臉部與虹膜模型無法使用；其餘功能維持運作': '本機細緻臉部與虹膜模型需要處理；其餘功能維持運作',
    '墨寒會在本機分析在場狀態、臉部與眼神特徵、手勢及場景線索；不保存原始影像、不傳送雲端，未登錄的人物不會建立身分。是否啟用？': '墨寒會僅在本機即時分析在場狀態、臉部與眼神特徵、手勢及場景線索；原始影像限於即時處理，身分建立僅適用已登錄人物。是否啟用？',
    '攝影機啟動失敗：{error}': '攝影機啟動需要處理：{error}',
    '這會刪除本機加密的臉部特徵，且無法復原。是否繼續？': '這會永久刪除本機加密的臉部特徵。是否繼續？',
    '啟動失敗：{error}': '啟動需要處理：{error}',
    '遠端服務已停止，既有權杖未刪除但無法連線。': '遠端服務已停止，既有權杖保持保存；重新啟動服務後才可連線。',
    '請只在可信任裝置輸入下列權杖。關閉視窗後不會再次顯示：\n\n{token}': '請只在可信任裝置輸入下列權杖；權杖僅在目前視窗顯示一次：\n\n{token}',
    '付款、購買、密碼匯出、停用安全防護、任意 PowerShell／管理員命令永遠禁止自動執行，無法由此頁解除。': '付款、購買、密碼匯出、停用安全防護及任意 PowerShell／管理員命令，永久排除於自動執行範圍；本頁持續遵守此界線。',
    '尚未安裝此工具的執行器': '請安裝此工具的執行器',
    '工具回報完成，但結果驗證未通過': '工具回報完成；結果驗證需要處理',
    '工具執行失敗：{detail}': '工具執行需要處理：{detail}',
    '此能力永不允許自動執行': '此能力永久排除於自動執行範圍',
    '權限設定為禁止': '權限維持封鎖',
    '排程設定無法讀取': '讀取排程設定需要處理',
    '自動備份失敗': '自動備份需要處理',
    '禁止': '封鎖',
    '備份失敗：{error}': '備份需要處理：{error}',
    '這句話沒有明確要求執行操作，因此不會產生工具計畫。': '請明確指定要執行的操作，再建立工具計畫。',
    '（目前沒有白名單目標）': '（請先加入白名單目標）',
    '計畫驗證失敗：{error}': '計畫驗證需要處理：{error}',
    '資料不足或並非明確操作要求，因此沒有產生任何步驟。': '請補齊操作資訊並明確提出執行要求，再建立步驟。',
    '無法產生計畫：{error}': '產生計畫需要處理：{error}',
    'Home Assistant：{home}\n遠端服務：{remote}\n已啟用工作流程：{workflows}\n有效配對裝置：{devices}\n安全狀態：高風險操作不允許免確認；任意命令列與付款永久禁止。': 'Home Assistant：{home}\n遠端服務：{remote}\n已啟用工作流程：{workflows}\n有效配對裝置：{devices}\n安全狀態：高風險操作須確認；任意命令列與付款永久排除於執行範圍。',
    '沒有可執行步驟': '請建立可執行步驟',
    '無法安全保存 OAuth 權杖：{error}': '請檢查設定後安全保存 OAuth 權杖：{error}',
    '{provider} 連線失敗：{error}': '{provider} 連線需要注意：{error}，請檢查設定後重試',
    '無法安全更新 OAuth 權杖：{error}': '請檢查設定後安全更新 OAuth 權杖：{error}',
    '無法安全保存權杖：{error}': '請檢查設定後安全保存權杖：{error}',
    '無法開始臉部登錄：{error}': '臉部登錄需要注意：{error}，請檢查設定後重試',
    '失敗': '需要處理',
})


def _current_source(source: str) -> str:
    """Map retired UI copy to the current catalog while preserving behavior."""

    if source.startswith("公開版預設關閉。") and source.endswith(
        "本機 OpenCV 不受此設定影響。"
    ):
        return _VISION_AUTHORIZATION_SUMMARY
    if source.startswith("啟用並保存後會依所選事件與用量限制持續運作"):
        return _VISION_AUTHORIZATION_DETAILS
    return _SOURCE_COPY_ALIASES.get(source, source)


@dataclass(frozen=True, slots=True)
class FlagshipTranslator:
    """Translate flagship UI text while preserving runtime-provided values."""

    language: str = "zh-TW"

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "language",
            canonical_ui_language(self.language),
        )

    def text(self, source: str, /, **values: Any) -> str:
        current_source = _current_source(source)
        template = current_source
        if self.language != "zh-TW":
            try:
                template = FLAGSHIP_TRANSLATIONS[current_source][
                    _TRANSLATION_INDEX[self.language]
                ]
            except KeyError as exc:
                raise KeyError(
                    f"Missing flagship translation for {current_source!r} in {self.language}"
                ) from exc
        return template.format_map(values) if values else template

    def system_message(self, message: str) -> str:
        """Translate known system prose while preserving data and diagnostic detail."""

        value = _current_source(str(message))
        if self.language == "zh-TW":
            return value
        if value in FLAGSHIP_TRANSLATIONS:
            return self.text(value)
        for pattern, source in _SYSTEM_PATTERNS:
            match = re.fullmatch(pattern, value)
            if match is None:
                continue
            fields = match.groupdict()
            if "reason" in fields:
                fields["reason"] = self.system_message(fields["reason"])
            return self.text(source, **fields)
        return value

    def home_issue(self, message: str) -> str:
        """Translate Home Assistant status prose while preserving entity data."""

        value = str(message)
        if self.language == "zh-TW":
            return value
        if " 電量只剩 " in value:
            name, remaining = value.rsplit(" 電量只剩 ", 1)
            return self.text(
                "{name} 電量只剩 {value}",
                name=name,
                value=remaining,
            )
        if " 目前" in value:
            name, state = value.rsplit(" 目前", 1)
            return self.text("{name} 目前{state}", name=name, state=state)
        return value


def validate_flagship_translations() -> None:
    """Validate each catalog row before use and report the row requiring complete text."""

    for source, translations in FLAGSHIP_TRANSLATIONS.items():
        if not source or len(translations) != len(_TRANSLATION_INDEX):
            raise ValueError(f"Invalid flagship translation row: {source!r}")
        if any(not value.strip() for value in translations):
            raise ValueError(f"Blank flagship translation: {source!r}")


validate_flagship_translations()

__all__ = (
    "FLAGSHIP_TRANSLATIONS",
    "FlagshipTranslator",
    "validate_flagship_translations",
)
