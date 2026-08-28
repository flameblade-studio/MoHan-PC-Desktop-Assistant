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
        "activation-failed": translate(
            "wardrobe_generation_activation_failed",
            "新衣已通過稽核並安裝，但未能安全套用；目前衣裝保持不變。",
        ),
        "not-enabled": translate("wardrobe_generation_not_enabled", "請先勾選允許雲端自創新衣。"),
        "api-key-unavailable": translate("wardrobe_generation_no_key", "尚未設定可用的 OpenAI API Key。"),
        "already-generating": translate("wardrobe_generation_running", "正在生成、稽核並封裝新衣……"),
        "capacity-blocked": translate("wardrobe_generation_capacity", "已達自創服裝容量或冷卻限制。"),
        "cooldown-blocked": translate(
            "wardrobe_generation_cooldown",
            "自動生成仍在失敗冷卻期；可按「立即生成新衣」手動重試。",
        ),
        "quarantined": translate("wardrobe_generation_quarantined", "新衣未通過稽核，已隔離且未套用。"),
        "automatic-selection-disabled": translate("wardrobe_automatic_selection_disabled", "自主選裝目前已關閉。"),
        "automatic-selection-failed": translate("wardrobe_automatic_selection_failed", "自主選裝評估失敗，已保留目前衣裝。"),
        "outfit-selected": translate("wardrobe_automatic_outfit_selected", "墨寒已依情境自主換裝。"),
        "failed:rate-limited": translate(
            "wardrobe_generation_rate_limited",
            "圖片服務目前流量繁忙；墨寒已安全重試，稍後可從既有進度續作。",
        ),
        "failed:authentication-failed": translate(
            "wardrobe_generation_auth_failed",
            "OpenAI API Key 驗證失敗，請在設定分頁重新儲存金鑰。",
        ),
        "failed:model-access-denied": translate(
            "wardrobe_generation_access_denied",
            "目前的 OpenAI 專案尚無 GPT Image 2 使用權限或尚未完成組織驗證。",
        ),
        "failed:moderation-blocked": translate(
            "wardrobe_generation_moderation_blocked",
            "這次圖像請求未通過供應器內容檢查，未扣入服裝庫。",
        ),
        "failed:invalid-request": translate(
            "wardrobe_generation_invalid_request",
            "圖片服務拒絕了生成規格；錯誤已保留供修復，未安裝不完整素材。",
        ),
        "failed:network-unavailable": translate(
            "wardrobe_generation_network_unavailable",
            "目前無法連線至圖片服務，未安裝不完整素材。",
        ),
        "failed:provider-unavailable": translate(
            "wardrobe_generation_provider_unavailable",
            "圖片服務暫時無法使用，未安裝不完整素材。",
        ),
    }
    return messages.get(
        status,
        translate(
            "wardrobe_generation_failed",
            "新衣生成失敗；已保留安全化錯誤資訊，未安裝不完整素材。",
        ),
    )
