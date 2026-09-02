"""內容不可見的智慧家庭動作，必須按風險上限分級。

2026-09-02 稽核：`script.turn_on` 落在 `home_control`（BLUE，零確認），
但腳本內容在伺服器上，用戶端看不見。一個名為「夜間模式」的腳本可以同時
執行 `lock.unlock` 與 `alarm_control_panel.alarm_disarm`——而那兩件事直接
表達時是 RED、需要兩次確認。使用者以為自己只授權了一般家電控制。

`scene` 同一個問題：情境會設定實體狀態，其中可以包含把門鎖設成解鎖。

無法分級的東西只能按上限分級。這裡的測試同時確認低風險動作**沒有**被
一起升級——把所有東西都變成 RED 不是修正，是把功能關掉。
"""
from __future__ import annotations


def test_server_side_script_is_not_low_risk() -> None:
    from integrations.home_assistant import classify_home_capability

    assert classify_home_capability("script", "turn_on") == "home_routine", (
        "伺服器端腳本仍被當成一般家電控制"
    )


def test_scene_is_not_low_risk() -> None:
    from integrations.home_assistant import classify_home_capability

    assert classify_home_capability("scene", "turn_on") == "home_routine"


def test_routine_capability_is_graded_at_the_ceiling() -> None:
    from domain.flagship_action_models import CAPABILITY_RISK, RiskLevel

    assert CAPABILITY_RISK["home_routine"] is RiskLevel.RED


def test_ordinary_devices_are_still_low_risk() -> None:
    """正例：修正不得把一般家電一起升級成需要兩次確認。"""
    from domain.flagship_action_models import CAPABILITY_RISK, RiskLevel
    from integrations.home_assistant import classify_home_capability

    for domain in ("light", "switch", "fan", "cover", "media_player"):
        capability = classify_home_capability(domain, "turn_on")
        assert capability == "home_control", f"{domain} 被誤升級為 {capability}"
    assert CAPABILITY_RISK["home_control"] is RiskLevel.BLUE


def test_existing_high_risk_domains_are_unchanged() -> None:
    from integrations.home_assistant import classify_home_capability

    assert classify_home_capability("lock", "unlock") == "home_lock"
    assert classify_home_capability("alarm_control_panel", "alarm_disarm") == (
        "home_alarm"
    )
    assert classify_home_capability("climate", "set_temperature") == "home_heat"
    assert classify_home_capability("climate", "turn_off") == "home_control"


def test_every_home_capability_is_registered_everywhere() -> None:
    """新增一個家庭能力需要改七個地方；漏掉任何一處都會壞得很安靜。

    漏掉風險表 → 分級查不到；漏掉 HOME_CAPABILITIES → 權限設定裡沒有這一
    項可調；漏掉執行器註冊 → 動作找不到執行者；漏掉標籤 → 確認視窗顯示
    原始鍵名。這個守衛存在的理由是：這次修正本身就要同時改七處。
    """
    from domain.flagship_action_models import CAPABILITY_RISK
    from presentation.flagship.home import HOME_CAPABILITIES
    from presentation.flagship.shared import CORE_PERMISSION_LABELS

    graded = {name for name in CAPABILITY_RISK if name.startswith("home_")}
    listed = set(HOME_CAPABILITIES)
    labelled = {
        name for name in CORE_PERMISSION_LABELS if name.startswith("home_")
    }

    assert graded == listed, (
        f"風險表與 HOME_CAPABILITIES 不一致：只在風險表 {graded - listed}；"
        f"只在清單 {listed - graded}"
    )
    assert graded <= labelled, f"缺少標籤：{graded - labelled}"

    # 標籤存在還不夠：非繁體中文的介面會拿標籤字串去查翻譯表，查不到就
    # 直接 KeyError。這個修正本身就漏了這一步，三個語言的設定往返測試
    # 才把它抓出來。
    from presentation.flagship_ui_localization import FLAGSHIP_TRANSLATIONS

    missing = {
        CORE_PERMISSION_LABELS[name]
        for name in graded
        if CORE_PERMISSION_LABELS[name] not in FLAGSHIP_TRANSLATIONS
    }
    assert not missing, f"標籤缺少四語翻譯，非繁中介面會直接崩潰：{missing}"


def test_routine_capability_reaches_the_executor_and_the_editor() -> None:
    """註冊迴圈與工作流程編輯器都必須認得這個能力。"""
    import inspect

    from presentation.flagship import home, workflow_editor

    registration = inspect.getsource(home).split("executor.register(\"home_read\"", 1)[1]
    assert "home_routine" in registration.split("def ", 1)[0], (
        "執行器註冊迴圈沒有涵蓋 home_routine"
    )
    assert "home_routine" in inspect.getsource(workflow_editor), (
        "工作流程編輯器無法為 home_routine 產生參數"
    )
