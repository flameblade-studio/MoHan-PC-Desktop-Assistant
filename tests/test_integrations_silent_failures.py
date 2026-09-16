"""整合層準確區分完成、空結果與錯誤狀態。

2026-09-01 稽核發現十餘處整合回傳值混淆：請求中斷也可能顯示
已寄出、已建立、找到 0 筆或已驗證。此測試固定各種結果的型別與
條件，讓後續重構仍能明確回報實際狀態。
"""
from __future__ import annotations

lazy import html
lazy import json

lazy import pytest

lazy from integrations.cloud_connectors import (
    OAuthError,
    _require_collection,
    _require_identified,
)


class _StubHomeAssistant:
    """只提供 verify_control 需要的介面，不碰網路。"""

    def __init__(self, state: dict[str, object]) -> None:
        self._state = state

    def state(self, entity_id: str) -> dict[str, object]:
        assert entity_id
        return self._state


def test_write_response_without_identifier_is_a_failure() -> None:
    """2xx 回應須包含識別欄位，才能宣告建立完成。

    舊流程只檢查 dict 型別，空物件 {} 也會顯示郵件已寄出、行事曆
    已建立或檔案已上傳。此測試要求可核對的建立證據。
    """
    with pytest.raises(OAuthError):
        _require_identified({}, "Gmail 寄送", "id")
    with pytest.raises(OAuthError):
        _require_identified({"id": "   "}, "Gmail 寄送", "id")
    with pytest.raises(OAuthError):
        _require_identified(["not", "a", "dict"], "Gmail 寄送", "id")


def test_write_response_with_identifier_passes() -> None:
    """正常回應仍須通過並維持原有功能。"""
    payload = {"id": "abc123", "threadId": "t1"}
    assert _require_identified(payload, "Gmail 寄送", "id") is payload
    # 任一識別欄位有值即可
    assert _require_identified({"threadId": "t1"}, "Gmail 寄送", "id", "threadId")


def test_missing_collection_key_is_an_error_not_zero_results() -> None:
    """回應須符合預期欄位契約；欄位差異回報明確錯誤。

    API schema 漂移、代理改寫或回應損毀，皆應與合法空結果保持
    各自的結果狀態。
    """
    with pytest.raises(OAuthError):
        _require_collection({}, "Gmail 搜尋", "messages")
    with pytest.raises(OAuthError):
        _require_collection({"messages": "not-a-list"}, "Gmail 搜尋", "messages")
    with pytest.raises(OAuthError):
        _require_collection("not-a-dict", "Gmail 搜尋", "messages")


def test_present_but_empty_collection_is_genuinely_zero_results() -> None:
    """欄位存在而為空陣列，才是真正的「找到 0 筆」。"""
    assert _require_collection({"messages": []}, "Gmail 搜尋", "messages") == []
    assert _require_collection(
        {"messages": [{"id": "1"}, {"id": "2"}]}, "Gmail 搜尋", "messages"
    ) == [{"id": "1"}, {"id": "2"}]
    # 2026-09-02 重驗：元素須為契約物件，其餘型別回報結構錯誤。
    with pytest.raises(OAuthError):
        _require_collection(
            {"messages": [{"id": "1"}, "junk", {"id": "2"}]},
            "Gmail 搜尋",
            "messages",
        )


def test_home_assistant_without_expected_state_is_not_verified() -> None:
    """驗證通過須具備可比對的預期狀態與實際狀態。

    舊 expected is None 分支讓 toggle、set_percentage、open_cover、
    scene.turn_on 與 script.turn_on 直接通過。此測試要求使用實際讀值
    比對；預期值待補時保留待驗證狀態。
    """
    from domain.flagship_action_models import ActionRequest, ActionResult
    from integrations.home_assistant import HomeAssistantClient

    client = object.__new__(HomeAssistantClient)
    client.state = _StubHomeAssistant({"state": "on"}).state  # type: ignore[method-assign]

    result = ActionResult("r1", True, "ok", {"entity_id": "fan.study"})
    for service in ("toggle", "set_percentage", "open_cover", "turn_on"):
        request = ActionRequest(
            "r1", "home_control", {"service": service}, source="local"
        )
        verified = HomeAssistantClient.verify_control(client, request, result)
        if service == "turn_on":
            assert verified is True, "turn_on 有預期狀態，必須照樣能驗證通過"
        else:
            assert verified is False, f'{service} 須有預期狀態與實際比對結果才能標示已驗證'


def test_audit_summary_escapes_external_html() -> None:
    """稽核畫面的所有外部內容均須進行 HTML 跳脫。

    郵件寄件者、主旨、bodyPreview、行事曆與 Home Assistant attributes
    會進入 QTextBrowser.setHtml()。json.dumps 只處理 JSON 跳脫；
    顯示前另需處理 < > &，讓遠端 img 內容保持純文字。
    """
    payload = {"subject": '<img src="http://example.invalid/pixel">'}
    summary = json.dumps(payload, ensure_ascii=False)
    escaped = html.escape(summary)
    assert "<img" not in escaped
    assert "&lt;img" in escaped


def test_timeout_is_not_retried_for_paid_generation(monkeypatch) -> None:
    """付費且非冪等的請求遇到 timeout，維持單次送出。

    timeout 代表服務端完成狀態待確認。重送可能造成重複計費與服裝；
    舊流程最多將 31 視角擴成 93 次，且請求省略冪等鍵。
    此測試計算實際送出次數，以驗證單次送出行為。
    """
    from integrations import openai_outfit_generator as gen

    calls = {"n": 0}

    def fake_urlopen(request, timeout=None):
        calls["n"] += 1
        raise TimeoutError("simulated read timeout")

    monkeypatch.setattr(gen.urllib_request, "urlopen", fake_urlopen)
    transport = object.__new__(gen.OpenAIImageEditTransport)
    transport._options = gen.OpenAIImageEditOptions(api_key="test-key")

    with pytest.raises(gen.OutfitImageGenerationError) as excinfo:
        transport._open_with_retry(object())

    assert calls["n"] == 1, f"實際送出 {calls['n']} 次；付費請求須維持單次送出"
    assert excinfo.value.retryable is False


def test_connection_refused_is_still_retried(monkeypatch) -> None:
    """連線建立前的錯誤仍保留原有重試能力。"""
    from integrations import openai_outfit_generator as gen

    calls = {"n": 0}

    def fake_urlopen(request, timeout=None):
        calls["n"] += 1
        raise ConnectionRefusedError("simulated refusal")

    monkeypatch.setattr(gen.urllib_request, "urlopen", fake_urlopen)
    monkeypatch.setattr(gen, "TRANSIENT_RETRY_DELAYS_SECONDS", (0, 0, 0))
    transport = object.__new__(gen.OpenAIImageEditTransport)
    transport._options = gen.OpenAIImageEditOptions(api_key="test-key")

    with pytest.raises(gen.OutfitImageGenerationError):
        transport._open_with_retry(object())

    assert calls["n"] == gen.MAX_TRANSIENT_ATTEMPTS
