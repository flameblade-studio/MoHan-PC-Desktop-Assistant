"""外部輸入只在其授權邊界內執行。

2026-09-02 稽核發現網站白名單僅比 hostname 與路徑字首；scheme
檢查套在白名單自身，導致 https://portal.example/app 的授權擴及
http://portal.example:8080/app-delete。測試要求完整比對協定、埠與路徑。

另有 --jit-status-output= 在一般啟動時直接覆寫指定檔案的問題；
輸出現在須受 --self-test 範圍約束。每組同時驗證正常授權與越界案例。
"""
from __future__ import annotations

lazy import sys


def _toolbox(allowed: tuple[str, ...]):
    from infrastructure.flagship_windows_toolbox import WindowsToolbox

    return WindowsToolbox(allowed_websites=list(allowed))


def _open(toolbox, url: str, monkeypatch) -> bool:
    """以替身記錄白名單判斷，將瀏覽器操作留在測試邊界內。

    初版直接呼叫 webbrowser.open 曾在 CI 啟動 Edge，鎖住
    component_crx_cache，清理時回報 PermissionError [WinError 32]。
    此版本使用替身記錄呼叫，讓授權正例也保持隔離。
    """
    import webbrowser

    from domain.flagship_action_models import ActionRequest

    launched: list[str] = []
    monkeypatch.setattr(webbrowser, "open", lambda url, **_: launched.append(url) or True)
    request = ActionRequest(
        capability="open_web",
        description="test",
        arguments={"url": url},
        source="test",
    )
    try:
        toolbox.open_web(request)
    except PermissionError:
        assert not launched, '網址開啟必須先通過授權'
        return False
    assert launched == [url], "放行的網址必須恰好開啟一次"
    return True


def test_allowed_site_still_opens(monkeypatch) -> None:
    """正例：正常授權的網址仍可使用。"""
    toolbox = _toolbox(("https://portal.example/app",))
    assert _open(toolbox, monkeypatch=monkeypatch, url="https://portal.example/app/report")
    assert _open(toolbox, monkeypatch=monkeypatch, url="https://portal.example/app")


def test_scheme_must_match_the_allowed_entry(monkeypatch) -> None:
    """允許 HTTPS 不等於允許明文 HTTP。"""
    toolbox = _toolbox(("https://portal.example/app",))
    assert not _open(toolbox, monkeypatch=monkeypatch, url="http://portal.example/app"), (
        "允許 HTTPS 的項目放行了明文 HTTP"
    )


def test_port_must_match_the_allowed_entry(monkeypatch) -> None:
    """`hostname` 不含 port，只比 hostname 會放行任意服務埠。"""
    toolbox = _toolbox(("https://portal.example/app",))
    assert not _open(toolbox, monkeypatch=monkeypatch, url="https://portal.example:8443/app"), (
        "不同服務埠被當成同一個來源"
    )


def test_path_must_stop_at_a_segment_boundary(monkeypatch) -> None:
    """`/app` 授權只涵蓋該路徑及其子路徑；`/app-delete` 保持獨立。"""
    toolbox = _toolbox(("https://portal.example/app",))
    assert not _open(toolbox, monkeypatch=monkeypatch, url="https://portal.example/app-delete"), (
        "字首比對讓相鄰路徑通過；對帶有 GET 副作用的管理介面尤其危險"
    )


def test_root_path_entry_allows_the_whole_host(monkeypatch) -> None:
    """明確授權整個網站時仍應放行整站。"""
    toolbox = _toolbox(("https://portal.example/",))
    assert _open(toolbox, monkeypatch=monkeypatch, url="https://portal.example/anything/at/all")


def test_harness_output_is_ignored_on_a_normal_launch(monkeypatch, tmp_path) -> None:
    """一般啟動保持檔案原樣；狀態輸出旗標限於核准的自我測試流程。"""
    from application import application_bootstrap

    target = tmp_path / "victim.txt"
    target.write_text("原本的內容", encoding="utf-8")
    monkeypatch.setattr(
        sys, "argv", ["MoHan.exe", f"--jit-status-output={target}"]
    )
    assert application_bootstrap._harness_output_path("--jit-status-output=") is None
    application_bootstrap._write_jit_status()
    assert target.read_text(encoding="utf-8") == "原本的內容", (
        "一般啟動仍然覆寫了指定的檔案"
    )


def test_harness_output_is_accepted_in_self_test_mode(monkeypatch, tmp_path) -> None:
    """正例：測試工具本來的用途必須仍然可用。"""
    from application import application_bootstrap

    target = tmp_path / "jit.txt"
    monkeypatch.setattr(
        sys, "argv", ["MoHan.exe", "--self-test", f"--jit-status-output={target}"]
    )
    assert application_bootstrap._harness_output_path("--jit-status-output=") == target


def test_harness_output_may_be_rewritten_across_repeated_runs(
    monkeypatch, tmp_path
) -> None:
    """profiler 重複使用同一路徑時，仍須明確更新既存狀態檔。"""
    from application import application_bootstrap

    target = tmp_path / "smoke.txt"
    target.write_text("上一輪", encoding="utf-8")
    monkeypatch.setattr(
        sys, "argv", ["MoHan.exe", "--smoke-auto-exit", f"--smoke-output={target}"]
    )
    assert application_bootstrap._harness_output_path("--smoke-output=") == target


def test_harness_output_rejects_a_missing_parent_directory(
    monkeypatch, tmp_path
) -> None:
    """不替呼叫者建立目錄；路徑打錯時應該不寫，而不是散落檔案。"""
    from application import application_bootstrap

    target = tmp_path / "no-such-dir" / "jit.txt"
    monkeypatch.setattr(
        sys, "argv", ["MoHan.exe", "--self-test", f"--jit-status-output={target}"]
    )
    assert application_bootstrap._harness_output_path("--jit-status-output=") is None
