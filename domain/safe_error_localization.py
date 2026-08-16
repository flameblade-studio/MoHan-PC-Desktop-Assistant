from __future__ import annotations

lazy from collections.abc import Mapping

lazy from domain.language_support import canonical_ui_language
lazy from domain.safe_error import (
    SafeDiagnostic,
    SafeError,
    SafeErrorType,
    sanitize_error,
)

__all__ = ["safe_error_message"]


def _text(
    traditional_chinese: str,
    simplified_chinese: str,
    english: str,
    japanese: str,
) -> Mapping[str, str]:
    return frozendict({
        "zh-TW": traditional_chinese,
        "zh-CN": simplified_chinese,
        "en": english,
        "ja-JP": japanese,
    })


_MESSAGES: Mapping[SafeDiagnostic, Mapping[str, str]] = frozendict({
    SafeDiagnostic.AUTHENTICATION_REQUIRED: _text(
        "驗證資料無效或已失效，請重新檢查設定。",
        "验证资料无效或已失效，请重新检查设置。",
        "Authentication is missing or no longer valid. Check the settings and try again.",
        "認証情報が無効、または期限切れです。設定を確認して再試行してください。",
    ),
    SafeDiagnostic.ACCESS_DENIED: _text(
        "服務拒絕這項操作，請檢查帳號或權限。",
        "服务拒绝此操作，请检查账号或权限。",
        "The service denied this operation. Check the account and permissions.",
        "サービスがこの操作を拒否しました。アカウントと権限を確認してください。",
    ),
    SafeDiagnostic.RATE_LIMITED: _text(
        "服務目前請求過多或已達使用上限，請稍後重試。",
        "服务当前请求过多或已达到使用上限，请稍后重试。",
        "The service is busy or its usage limit was reached. Try again later.",
        "サービスが混雑しているか、使用上限に達しました。しばらくしてから再試行してください。",
    ),
    SafeDiagnostic.REQUEST_TIMEOUT: _text(
        "服務回應逾時，請稍後重試。",
        "服务响应超时，请稍后重试。",
        "The service timed out. Try again later.",
        "サービスの応答がタイムアウトしました。しばらくしてから再試行してください。",
    ),
    SafeDiagnostic.NETWORK_UNAVAILABLE: _text(
        "無法連線至服務，請檢查網路後重試。",
        "无法连接到服务，请检查网络后重试。",
        "The service could not be reached. Check the network and try again.",
        "サービスに接続できません。ネットワークを確認して再試行してください。",
    ),
    SafeDiagnostic.RESOURCE_NOT_FOUND: _text(
        "找不到指定資源，或目前帳號無權使用。",
        "找不到指定资源，或当前账号无权使用。",
        "The requested resource was not found or is unavailable to this account.",
        "指定したリソースが見つからないか、このアカウントでは使用できません。",
    ),
    SafeDiagnostic.CONFLICT: _text(
        "服務狀態發生衝突，請重新整理後再試。",
        "服务状态发生冲突，请刷新后重试。",
        "The service state changed unexpectedly. Refresh and try again.",
        "サービスの状態が競合しました。更新してから再試行してください。",
    ),
    SafeDiagnostic.INVALID_INPUT: _text(
        "輸入或設定不完整，請檢查後重試。",
        "输入或设置不完整，请检查后重试。",
        "The input or settings are incomplete. Check them and try again.",
        "入力または設定が不完全です。確認して再試行してください。",
    ),
    SafeDiagnostic.INVALID_RESPONSE: _text(
        "服務回傳無法辨識的內容，請稍後重試。",
        "服务返回了无法识别的内容，请稍后重试。",
        "The service returned an unreadable response. Try again later.",
        "サービスから読み取れない応答が返されました。しばらくしてから再試行してください。",
    ),
    SafeDiagnostic.OPERATION_CANCELLED: _text(
        "操作已取消。",
        "操作已取消。",
        "The operation was cancelled.",
        "操作はキャンセルされました。",
    ),
    SafeDiagnostic.LOCAL_IO_FAILURE: _text(
        "本機檔案或裝置操作失敗，請檢查權限與可用空間。",
        "本地文件或设备操作失败，请检查权限与可用空间。",
        "A local file or device operation failed. Check permissions and available space.",
        "ローカルのファイルまたはデバイス操作に失敗しました。権限と空き容量を確認してください。",
    ),
    SafeDiagnostic.REMOTE_SERVICE_FAILURE: _text(
        "遠端服務暫時無法使用，請稍後重試。",
        "远程服务暂时不可用，请稍后重试。",
        "The remote service is temporarily unavailable. Try again later.",
        "リモートサービスを一時的に利用できません。しばらくしてから再試行してください。",
    ),
    SafeDiagnostic.UNEXPECTED_RESPONSE: _text(
        "服務回傳非預期結果，請稍後重試。",
        "服务返回了意外结果，请稍后重试。",
        "The service returned an unexpected result. Try again later.",
        "サービスから予期しない結果が返されました。しばらくしてから再試行してください。",
    ),
    SafeDiagnostic.INTERNAL_FAILURE: _text(
        "墨寒執行此操作時發生內部錯誤，請重試。",
        "墨寒执行此操作时发生内部错误，请重试。",
        "MoHan encountered an internal error while performing this operation. Try again.",
        "墨寒がこの操作を実行中に内部エラーが発生しました。再試行してください。",
    ),
    SafeDiagnostic.UNKNOWN_FAILURE: _text(
        "操作未能完成，請重試。",
        "操作未能完成，请重试。",
        "The operation could not be completed. Try again.",
        "操作を完了できませんでした。再試行してください。",
    ),
})


def safe_error_message(
    language: str,
    error: BaseException | str | SafeError,
    *,
    http_status: int | None = None,
) -> str:
    """Return a four-language message without retaining provider detail."""

    safe = error if isinstance(error, SafeError) else _safe_error(error, http_status)
    locale = canonical_ui_language(language)
    message = _MESSAGES[safe.diagnostic][locale]
    diagnostic = (
        f"type={safe.error_type.value}; "
        f"diagnostic={safe.diagnostic.value}"
    )
    if safe.http_status is None:
        return f"{message} [{diagnostic}]"
    return f"{message} [{diagnostic}; HTTP {safe.http_status}]"


def _safe_error(error: BaseException | str, http_status: int | None) -> SafeError:
    if isinstance(error, str):
        decoded = _decode_safe_error(error)
        if decoded is not None:
            return decoded
    return sanitize_error(error, http_status=http_status)


def _decode_safe_error(value: str) -> SafeError | None:
    """Decode only the finite token emitted by ``str(SafeError)``."""

    fields: dict[str, str] = {}
    for item in value.split("; "):
        name, separator, field_value = item.partition("=")
        if not separator or name in fields:
            return None
        fields[name] = field_value
    if not {"type", "diagnostic"} <= fields.keys():
        return None
    if fields.keys() - {"type", "diagnostic", "http_status"}:
        return None
    try:
        status_text = fields.get("http_status")
        status = int(status_text) if status_text is not None else None
        if status is not None and not 100 <= status <= 599:
            return None
        return SafeError(
            SafeErrorType(fields["type"]),
            SafeDiagnostic(fields["diagnostic"]),
            status,
        )
    except (TypeError, ValueError):
        return None
