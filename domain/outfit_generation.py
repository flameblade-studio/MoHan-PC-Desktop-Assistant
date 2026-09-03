"""服裝生成「過程」的領域訊號。

與 outfit_pack.py 分開：那裡描述服裝包的**格式**，這裡描述生成這件事的
**生命週期**。取消是生命週期事件，不是格式問題。

行數棘輪逼出了這個切分，而切分本身是對的——原本把它塞進 outfit_pack.py，
是因為那裡剛好有一個 RuntimeError 子類別可以作伴，不是因為它屬於那裡。
"""
from __future__ import annotations


class OutfitGenerationCancelled(RuntimeError):
    """使用者要求中止生成。

    這不是失敗，是使用者主動停手，所以與 OutfitPackError 分開：呼叫端要能
    分辨「這次沒做成」與「使用者按了緊急停止」。混在一起的後果是退避計時器
    把停手記成一次失敗嘗試，接著封鎖使用者下一次真正想要的生成。
    """


class OutfitImageGenerationError(RuntimeError):
    """A sanitized, user-displayable image-provider failure."""

    def __init__(
        self,
        message: str,
        *,
        code: str = "provider-error",
        http_status: int = 0,
        request_id: str = "",
        retryable: bool = False,
    ) -> None:
        super().__init__(message)
        self.code = str(code or "provider-error")
        self.http_status = int(http_status or 0)
        self.request_id = str(request_id or "")
        self.retryable = bool(retryable)

    @property
    def public_status(self) -> str:
        """Return a stable, secret-free status suitable for UI and audit."""

        return f"failed:{self.code}"
