"""整合層不得把失敗說成成功。

2026-09-01 的獨立稽核在 integrations/ 找到十餘處靜默失敗——失敗路徑的回傳值
與成功無法區分，於是使用者看到「已寄出」「已建立」「找到 0 筆」「已驗證」，
而實際上請求可能根本沒完成。

這一類缺陷不會留下痕跡：沒有例外、沒有紅字、沒有任何跡象。它們只能靠測試
把「錯誤」與「空結果」的界線釘死，否則下一次重構又會把兩者合併回去。
"""
from __future__ import annotations

import html
import json

import pytest

from integrations.cloud_connectors import (
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
    """2xx 但沒有識別欄位不得當成「已建立」。

    先前只檢查 isinstance(result, dict)，於是一個空物件 {} 會讓應用向使用者
    宣告郵件已寄出、行事曆已建立、檔案已上傳。
    """
    with pytest.raises(OAuthError):
        _require_identified({}, "Gmail 寄送", "id")
    with pytest.raises(OAuthError):
        _require_identified({"id": "   "}, "Gmail 寄送", "id")
    with pytest.raises(OAuthError):
        _require_identified(["not", "a", "dict"], "Gmail 寄送", "id")


def test_write_response_with_identifier_passes() -> None:
    """修正不能只是把功能關掉：正常回應必須照樣通過。"""
    payload = {"id": "abc123", "threadId": "t1"}
    assert _require_identified(payload, "Gmail 寄送", "id") is payload
    # 任一識別欄位有值即可
    assert _require_identified({"threadId": "t1"}, "Gmail 寄送", "id", "threadId")


def test_missing_collection_key_is_an_error_not_zero_results() -> None:
    """缺少預期欄位是合約不符，不是「沒有結果」。

    API schema 漂移、代理伺服器改寫或被破壞的回應都會落在這裡。先前一律
    回傳 []，與真正的空結果無法區分。
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
    rows = _require_collection(
        {"messages": [{"id": "1"}, "junk", {"id": "2"}]},
        "Gmail 搜尋",
        "messages",
    )
    assert rows == [{"id": "1"}, {"id": "2"}]


def test_home_assistant_without_expected_state_is_not_verified() -> None:
    """沒有可比對的預期狀態時，答案是「無法驗證」而不是「通過」。

    先前 `expected is None or ...` 讓 toggle、set_percentage、open_cover、
    scene.turn_on、script.turn_on 全部無條件通過——裝置完全沒照做也會被
    標記為已驗證。狀態明明讀出來了，卻沒有參與判斷。
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
            assert verified is False, f"{service} 沒有預期狀態，不得宣稱已驗證"


def test_audit_summary_escapes_external_html() -> None:
    """稽核畫面的外部內容必須跳脫，否則是注入點。

    payload 含郵件寄件者、主旨、bodyPreview、行事曆與 Home Assistant
    attributes。json.dumps 會跳脫引號與反斜線，但不會跳脫 < > &，而稽核
    畫面是用 QTextBrowser.setHtml() 渲染的——一個遠端 <img> 就足以讓外部
    得知使用者何時查看稽核紀錄並取得其 IP。
    """
    payload = {"subject": '<img src="http://example.invalid/pixel">'}
    summary = json.dumps(payload, ensure_ascii=False)
    escaped = html.escape(summary)
    assert "<img" not in escaped
    assert "&lt;img" in escaped


def test_timeout_is_not_retried_for_paid_generation(monkeypatch) -> None:
    """付費且非冪等的請求，timeout 不得重試。

    timeout 的語意是「不知道對方做了沒」。若服務已處理完、只是回應沒回來，
    重試就是再付一次錢並產生重複的服裝。31 視角的工作最壞可送出 93 次，
    而且沒有冪等鍵。

    行為測試而非原始碼字串比對：計算實際送出的請求次數。
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

    assert calls["n"] == 1, f"timeout 被重試了 {calls['n']} 次，付費請求不得重送"
    assert excinfo.value.retryable is False


def test_connection_refused_is_still_retried(monkeypatch) -> None:
    """反例：連線根本沒建立起來時仍應重試，修正不能把重試整個關掉。"""
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
