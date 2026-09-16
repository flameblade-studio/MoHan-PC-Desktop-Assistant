from __future__ import annotations

"""Localized status copy for the Dashboard cloud-wardrobe bridge."""

lazy from collections.abc import Callable

Translate = Callable[[str, str], str]


def wardrobe_generation_message(status: str, translate: Translate) -> str:
    messages = {
        "generating": translate("wardrobe_generation_running", "正在生成、稽核並封裝新衣……"),
        "generating-with-trend-search": translate(
            "wardrobe_generation_trend_search",
            "正在以已同意的五類情境搜尋趨勢，接著生成、稽核並封裝新衣（可能產生費用）……",
        ),
        "installed": translate("wardrobe_generation_installed", "新衣已通過稽核、安裝並套用。"),
        "installed-manual-lock": translate(
            "wardrobe_generation_installed_manual_lock",
            "新衣已通過稽核並安裝；目前手動衣裝仍在鎖定期，因此保持不變。",
        ),
        "body-profile-outdated": translate(
            "wardrobe_body_profile_outdated",
            "這套服裝需要二代素體素材；請用一鍵製衣重新生成",
        ),
        "activation-failed": translate(
            "wardrobe_generation_activation_failed",
            '新衣已通過稽核並安裝；套用步驟需要處理，目前衣裝持續使用。',
        ),
        "not-enabled": translate("wardrobe_generation_not_enabled", "請先勾選允許雲端自創新衣。"),
        "api-key-unavailable": translate("wardrobe_generation_no_key", '請在設定頁儲存可用的 OpenAI API Key。'),
        "already-generating": translate("wardrobe_generation_running", "正在生成、稽核並封裝新衣……"),
        "capacity-blocked": translate("wardrobe_generation_capacity", "已達自創服裝容量或冷卻限制。"),
        "cooldown-blocked": translate(
            "wardrobe_generation_cooldown",
            '自動生成正在錯誤後的冷卻期；可按「立即生成新衣」手動重試。',
        ),
        "quarantined": translate("wardrobe_generation_quarantined", '新衣的稽核結果需要修正，目前保持隔離；通過稽核後才可套用。'),
        "automatic-selection-disabled": translate("wardrobe_automatic_selection_disabled", '請啟用自主選裝後使用此功能。'),
        "automatic-selection-failed": translate("wardrobe_automatic_selection_failed", '自主選裝評估需要處理；目前衣裝持續使用。'),
        "outfit-selected": translate("wardrobe_automatic_outfit_selected", "墨寒已依情境自主換裝。"),
        "failed:rate-limited": translate(
            "wardrobe_generation_rate_limited",
            "圖片服務目前流量繁忙；墨寒已安全重試，稍後可從既有進度續作。",
        ),
        "failed:authentication-failed": translate(
            "wardrobe_generation_auth_failed",
            'OpenAI API Key 驗證需要處理，請在設定分頁重新儲存金鑰。',
        ),
        "failed:model-access-denied": translate(
            "wardrobe_generation_access_denied",
            '請檢查目前 OpenAI 專案的 GPT Image 2 使用權限與組織驗證狀態，完成所需設定後再試。',
        ),
        "failed:moderation-blocked": translate(
            "wardrobe_generation_moderation_blocked",
            '這次圖像請求需要調整以通過供應器內容檢查；服裝庫保留既有素材。',
        ),
        "failed:invalid-request": translate(
            "wardrobe_generation_invalid_request",
            '請修正圖片服務要求的生成規格；錯誤資訊已保留，既有安裝素材保持完整。',
        ),
        "failed:network-unavailable": translate(
            "wardrobe_generation_network_unavailable",
            '連線至圖片服務需要處理；既有安裝素材保持完整。',
        ),
        "failed:provider-unavailable": translate(
            "wardrobe_generation_provider_unavailable",
            '圖片服務恢復後即可繼續生成；既有安裝素材保持完整。',
        ),
    }
    return messages.get(
        status,
        translate(
            "wardrobe_generation_failed",
            '新衣生成需要處理；安全化錯誤資訊已保留，既有安裝素材保持完整。',
        ),
    )
