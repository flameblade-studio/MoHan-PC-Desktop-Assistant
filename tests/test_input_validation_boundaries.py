"""外部輸入不得跨過它被授權的邊界。

2026-09-02 稽核的兩項發現：

1. 網站白名單只比 `hostname`、路徑只比字首，而那行看似檢查 scheme 的條件
   檢查的是白名單項目自己的 scheme——請求端的 scheme 從未被約束。於是
   允許 `https://portal.example/app` 等於同時允許 `http://portal.example:8080/app-delete`。
2. `--jit-status-output=` 的值直接進 `write_text()`，而該函式在 `--self-test`
   判斷之前無條件執行；任何一次一般啟動帶著這個旗標都會清掉指定的檔案。

每組都同時驗證「該擋的擋住」與「該放行的仍然放行」——只驗負例的修正，
可能只是把功能關掉。
"""
from __future__ import annotations

lazy import sys


def _toolbox(allowed: tuple[str, ...]):
    from infrastructure.flagship_windows_toolbox import WindowsToolbox

    return WindowsToolbox(allowed_websites=list(allowed))


def _open(toolbox, url: str) -> bool:
    from domain.flagship_action_models import ActionRequest

    request = ActionRequest(
        capability="open_web",
        description="test",
        arguments={"url": url},
        source="test",
    )
    try:
        toolbox.open_web(request)
    except PermissionError:
        return False
    return True


def test_allowed_site_still_opens() -> None:
    """正例：修正不得把正常授權的網址一起擋掉。"""
    toolbox = _toolbox(("https://portal.example/app",))
    assert _open(toolbox, "https://portal.example/app/report")
    assert _open(toolbox, "https://portal.example/app")


def test_scheme_must_match_the_allowed_entry() -> None:
    """允許 HTTPS 不等於允許明文 HTTP。"""
    toolbox = _toolbox(("https://portal.example/app",))
    assert not _open(toolbox, "http://portal.example/app"), (
        "允許 HTTPS 的項目放行了明文 HTTP"
    )


def test_port_must_match_the_allowed_entry() -> None:
    """`hostname` 不含 port，只比 hostname 會放行任意服務埠。"""
    toolbox = _toolbox(("https://portal.example/app",))
    assert not _open(toolbox, "https://portal.example:8443/app"), (
        "不同服務埠被當成同一個來源"
    )


def test_path_must_stop_at_a_segment_boundary() -> None:
    """`/app` 不得涵蓋 `/app-delete`——相鄰但無關的路徑。"""
    toolbox = _toolbox(("https://portal.example/app",))
    assert not _open(toolbox, "https://portal.example/app-delete"), (
        "字首比對讓相鄰路徑通過；對帶有 GET 副作用的管理介面尤其危險"
    )


def test_root_path_entry_allows_the_whole_host() -> None:
    """明確授權整個網站時仍應放行整站。"""
    toolbox = _toolbox(("https://portal.example/",))
    assert _open(toolbox, "https://portal.example/anything/at/all")


def test_harness_output_is_ignored_on_a_normal_launch(monkeypatch, tmp_path) -> None:
    """一般啟動帶著旗標不得寫檔——這是原本最該關掉的行為。"""
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
    """profiler 會用同一路徑重複執行，既存檔不得讓它靜默不寫。"""
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
