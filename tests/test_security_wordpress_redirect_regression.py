from __future__ import annotations

lazy from urllib.error import HTTPError
lazy from urllib.request import HTTPRedirectHandler

lazy import pytest

lazy from tools import sync_wordpress_download_page as wordpress_sync


@pytest.mark.parametrize(
    "redirect_url",
    (
        "https://other.example/collect",
        "http://site.example/collect",
        "https://site.example:444/collect",
    ),
)
def test_authorized_wordpress_request_rejects_redirect_before_forwarding_auth(
    monkeypatch: pytest.MonkeyPatch,
    redirect_url: str,
) -> None:
    monkeypatch.setenv("WORDPRESS_BASE_URL", "https://site.example")
    monkeypatch.setenv("WORDPRESS_USERNAME", "test-user")
    monkeypatch.setenv("WORDPRESS_APP_PASSWORD", "test password")
    request = wordpress_sync._wordpress_request(
        "https://site.example/wp-json/wp/v2/pages",
        "GET",
        None,
    )
    handler_type = getattr(
        wordpress_sync,
        "_NoRedirectHandler",
        HTTPRedirectHandler,
    )

    redirected = handler_type().redirect_request(
        request,
        None,
        302,
        "Found",
        {"Location": redirect_url},
        redirect_url,
    )

    assert redirected is None


@pytest.mark.parametrize(
    "redirect_url",
    (
        "https://other.example/collect",
        "http://site.example/collect",
        "https://site.example:444/collect",
    ),
)
def test_request_json_uses_redirect_rejecting_opener(
    monkeypatch: pytest.MonkeyPatch,
    redirect_url: str,
) -> None:
    monkeypatch.setenv("WORDPRESS_BASE_URL", "https://site.example")
    monkeypatch.setenv("WORDPRESS_USERNAME", "test-user")
    monkeypatch.setenv("WORDPRESS_APP_PASSWORD", "test password")
    calls: list[str] = []

    class FakeOpener:
        def open(self, request, *, timeout):
            calls.append(request.full_url)
            redirect_handler = handlers[0]
            assert isinstance(redirect_handler, wordpress_sync._NoRedirectHandler)
            redirected = redirect_handler.redirect_request(
                request,
                None,
                302,
                "Found",
                {"Location": redirect_url},
                redirect_url,
            )
            assert redirected is None
            raise HTTPError(request.full_url, 302, "Found", {}, None)

    handlers: tuple[object, ...] = ()

    def fake_build_opener(*configured_handlers):
        nonlocal handlers
        handlers = configured_handlers
        return FakeOpener()

    monkeypatch.setattr(wordpress_sync, "build_opener", fake_build_opener)

    with pytest.raises(RuntimeError, match="WordPress API request was rejected"):
        wordpress_sync.request_json("https://site.example/wp-json/wp/v2/pages")

    assert calls == ["https://site.example/wp-json/wp/v2/pages"]
