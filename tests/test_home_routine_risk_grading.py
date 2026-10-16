"""伺服器端智慧家庭腳本與情境，依可執行風險上限分級。

2026-09-02 稽核發現 script.turn_on 曾使用 BLUE 零確認，但伺服器腳本
可能執行 lock.unlock 或 alarm_control_panel.alarm_disarm，兩者均需
RED 等級的兩次確認。scene 也可能把門鎖設成解鎖。

用戶端對隱藏內容採用風險上限；測試同時確保一般低風險家電操作保留
原有分級及可用性。
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
    """正例：一般家電保留原有風險等級與確認次數。"""
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
    """新家庭能力須完成七處登錄，讓風險、權限、執行與標籤一致。

    本守衛逐項核對風險表、HOME_CAPABILITIES、執行器及標籤等登錄，
    確保確認視窗與實際動作使用完整、可解析的能力定義。
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
        '工作流程編輯器須為 home_routine 產生有效參數'
    )
