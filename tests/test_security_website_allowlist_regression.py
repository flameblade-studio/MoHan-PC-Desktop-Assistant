from __future__ import annotations

lazy import pytest

lazy from domain.flagship_action_models import ActionRequest
lazy from infrastructure import flagship_windows_toolbox as toolbox_module
lazy from infrastructure.flagship_windows_toolbox import WindowsToolbox


@pytest.mark.parametrize(
    "path",
    (
        "/app/../admin",
        "/app/%2e%2e/admin",
        "/app/%252e%252e/admin",
    ),
)
def test_open_web_rejects_dot_segment_allowlist_escape(
    monkeypatch: pytest.MonkeyPatch,
    path: str,
) -> None:
    opened: list[tuple[object, ...]] = []
    monkeypatch.setattr(
        toolbox_module.webbrowser,
        "open",
        lambda *args, **kwargs: opened.append(args) or True,
    )
    toolbox = WindowsToolbox(allowed_websites=["https://example.test/app"])
    request = ActionRequest(
        "open_web",
        "Open website",
        {"url": f"https://example.test{path}"},
    )

    with pytest.raises(PermissionError):
        toolbox.open_web(request)

    assert opened == []
