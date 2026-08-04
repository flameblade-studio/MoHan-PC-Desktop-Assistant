from __future__ import annotations

import re
import threading
import urllib.error
import urllib.request
from xml.sax.saxutils import escape, quoteattr

from PySide6.QtCore import QObject, Signal

from speech import play_wave_with_visemes


AZURE_FEMALE_VOICES: dict[str, tuple[str, ...]] = {
    "zh-TW": (
        "zh-TW-HsiaoChenNeural",
        "zh-TW-HsiaoYuNeural",
    ),
    "zh-CN": (
        "zh-CN-XiaoxiaoNeural",
        "zh-CN-XiaoyiNeural",
        "zh-CN-XiaochenNeural",
        "zh-CN-XiaohanNeural",
        "zh-CN-XiaomengNeural",
        "zh-CN-XiaomoNeural",
        "zh-CN-XiaoqiuNeural",
        "zh-CN-XiaorouNeural",
        "zh-CN-XiaoruiNeural",
    ),
    "en-US": (
        "en-US-AvaMultilingualNeural",
        "en-US-AmandaMultilingualNeural",
        "en-US-CoraMultilingualNeural",
        "en-US-JennyMultilingualNeural",
    ),
}
_VOICE_LOCALE = {
    voice: locale
    for locale, voices in AZURE_FEMALE_VOICES.items()
    for voice in voices
}
_REGION_PATTERN = re.compile(r"^[a-z0-9-]{2,32}$")
_MESSAGES = {
    "zh-TW": {
        "invalid_region": "Azure Speech 區域格式不正確。",
        "unsupported_voice": "Azure Speech 只允許已確認的女性聲線。",
        "missing_settings": "尚未設定 Azure Speech 金鑰與區域。",
        "credentials": "Azure Speech 金鑰、區域或資源權限不正確。",
        "quota": "Azure Speech 免費額度或速率限制已達上限。",
        "service": "Azure Speech 服務暫時異常（HTTP {status}）。",
        "request": "Azure Speech 失敗（HTTP {status}）。",
        "network": "無法連線到 Azure Speech：{error}",
    },
    "zh-CN": {
        "invalid_region": "Azure Speech 区域格式不正确。",
        "unsupported_voice": "Azure Speech 只允许已确认的女性声线。",
        "missing_settings": "尚未设置 Azure Speech 密钥与区域。",
        "credentials": "Azure Speech 密钥、区域或资源权限不正确。",
        "quota": "Azure Speech 免费额度或速率限制已达到上限。",
        "service": "Azure Speech 服务暂时异常（HTTP {status}）。",
        "request": "Azure Speech 失败（HTTP {status}）。",
        "network": "无法连接 Azure Speech：{error}",
    },
    "en-US": {
        "invalid_region": "The Azure Speech region is invalid.",
        "unsupported_voice": (
            "Azure Speech accepts only verified female voices."
        ),
        "missing_settings": (
            "The Azure Speech key and region have not been configured."
        ),
        "credentials": (
            "The Azure Speech key, region, or resource permission is invalid."
        ),
        "quota": "The Azure Speech quota or rate limit has been reached.",
        "service": (
            "Azure Speech is temporarily unavailable (HTTP {status})."
        ),
        "request": "Azure Speech failed (HTTP {status}).",
        "network": "Could not connect to Azure Speech: {error}",
    },
}


def _message(locale: str, key: str, **values: object) -> str:
    catalog = _MESSAGES.get(locale, _MESSAGES["zh-TW"])
    return catalog[key].format(**values)


def normalize_azure_region(region: str) -> str:
    normalized = str(region or "").strip().lower()
    if not _REGION_PATTERN.fullmatch(normalized):
        raise ValueError("invalid_region")
    return normalized


def azure_female_voices(language: str) -> tuple[str, ...]:
    normalized = str(language or "").strip().lower()
    if normalized == "zh-cn":
        return AZURE_FEMALE_VOICES["zh-CN"]
    if normalized in {"en", "en-us"}:
        return AZURE_FEMALE_VOICES["en-US"]
    return AZURE_FEMALE_VOICES["zh-TW"]


def build_azure_ssml(text: str, voice: str) -> bytes:
    locale = _VOICE_LOCALE.get(voice)
    if locale is None:
        raise ValueError("unsupported_voice")
    body = (
        f"<speak version='1.0' xml:lang={quoteattr(locale)}>"
        f"<voice xml:lang={quoteattr(locale)} xml:gender='Female' "
        f"name={quoteattr(voice)}>{escape(text)}</voice></speak>"
    )
    return body.encode("utf-8")


def azure_speech_error_message(
    status: int,
    detail: str,
    locale: str = "zh-TW",
) -> str:
    _ = detail  # Never echo a remote response that could contain user data.
    if status in {401, 403}:
        return _message(locale, "credentials")
    if status == 429:
        return _message(locale, "quota")
    if status >= 500:
        return _message(locale, "service", status=status)
    return _message(locale, "request", status=status)


class AzureSpeechTTS(QObject):
    failed = Signal(str)
    finished = Signal()
    viseme_cue = Signal(float, str)

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self.volume_percent = 125
        self.muted = False

    def set_volume(self, volume_percent: int, muted: bool = False) -> None:
        self.volume_percent = max(0, min(160, int(volume_percent)))
        self.muted = bool(muted)

    def speak(
        self,
        text: str,
        api_key: str,
        region: str,
        voice: str,
    ) -> None:
        if not text.strip():
            self.finished.emit()
            return
        locale = _VOICE_LOCALE.get(voice, "zh-TW")
        if not api_key.strip() or not region.strip():
            self.failed.emit(_message(locale, "missing_settings"))
            return
        try:
            normalized_region = normalize_azure_region(region)
            build_azure_ssml(text, voice)
        except ValueError as exc:
            self.failed.emit(_message(locale, str(exc)))
            return
        threading.Thread(
            target=self._run,
            args=(text, api_key, normalized_region, voice),
            daemon=True,
        ).start()

    def _run(
        self,
        text: str,
        api_key: str,
        region: str,
        voice: str,
    ) -> None:
        locale = _VOICE_LOCALE.get(voice, "zh-TW")
        request = urllib.request.Request(
            (
                f"https://{region}.tts.speech.microsoft.com/"
                "cognitiveservices/v1"
            ),
            data=build_azure_ssml(text, voice),
            headers={
                "Ocp-Apim-Subscription-Key": api_key,
                "Content-Type": "application/ssml+xml",
                "X-Microsoft-OutputFormat": "riff-24khz-16bit-mono-pcm",
                "User-Agent": "MoHan-Desktop-Assistant",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                audio = response.read()
            play_wave_with_visemes(
                audio,
                self.volume_percent,
                self.muted,
                self.viseme_cue.emit,
            )
            self.finished.emit()
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            self.failed.emit(
                azure_speech_error_message(exc.code, detail, locale)
            )
        except (urllib.error.URLError, OSError, RuntimeError, TimeoutError) as exc:
            self.failed.emit(_message(locale, "network", error=exc))
