from __future__ import annotations

lazy import queue
lazy import re
lazy import threading
lazy import time
lazy from dataclasses import dataclass, field
lazy from xml.sax.saxutils import escape, quoteattr

lazy from azure.cognitiveservices import speech as speechsdk
lazy from PySide6.QtCore import QObject, Signal

lazy from azure_regions import azure_region_supports_hd_flash
lazy from azure_voice_catalog import AzureVoiceCatalog, AzureVoiceCatalogService
lazy from immutable_config import deep_freeze
lazy from speech import play_pcm16_stream_with_visemes

AZURE_FEMALE_VOICES: frozendict[str, tuple[str, ...]] = frozendict({
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
    "ja-JP": (
        "ja-JP-NanamiNeural",
        "ja-JP-AoiNeural",
        "ja-JP-MayuNeural",
        "ja-JP-ShioriNeural",
    ),
})
AZURE_HD_FEMALE_VOICES: frozendict[str, tuple[str, ...]] = frozendict({
    "zh-CN": (
        "zh-CN-Xiaochen:DragonHDLatestNeural",
        "zh-CN-Xiaoyue:DragonHDOmniLatestNeural",
        "zh-CN-Maroonallegro:DragonHDOmniLatestNeural",
        "zh-CN-Xiaoxiao:DragonHDFlashLatestNeural",
        "zh-CN-Xiaoxiao2:DragonHDFlashLatestNeural",
        "zh-CN-Xiaochen:DragonHDFlashLatestNeural",
        "zh-CN-Xiaoyi:DragonHDFlashLatestNeural",
        "zh-CN-Xiaoyu:DragonHDFlashLatestNeural",
        "zh-CN-Xiaohan:DragonHDFlashLatestNeural",
        "zh-CN-Xiaoshuang:DragonHDFlashLatestNeural",
        "zh-CN-Xiaoyou:DragonHDFlashLatestNeural",
    ),
    "en-US": (
        "en-US-Ava:DragonHDLatestNeural",
        "en-US-Aria:DragonHDLatestNeural",
        "en-US-Emma:DragonHDLatestNeural",
        "en-US-Emma2:DragonHDLatestNeural",
        "en-US-Jenny:DragonHDLatestNeural",
        "en-US-Nova:DragonHDLatestNeural",
        "en-US-Phoebe:DragonHDLatestNeural",
        "en-US-Serena:DragonHDLatestNeural",
    ),
    "ja-JP": ("ja-JP-Nanami:DragonHDLatestNeural",),
})


def _build_voice_locale_index() -> frozendict[str, str]:
    index: dict[str, str] = {}
    for catalog in (AZURE_FEMALE_VOICES, AZURE_HD_FEMALE_VOICES):
        for locale, voices in catalog.items():
            index.update(dict.fromkeys(voices, locale))
    return frozendict(index)


_VOICE_LOCALE = _build_voice_locale_index()
_REGION_PATTERN = re.compile(r"^[a-z0-9-]{2,32}$")
_VOICE_PATTERN = re.compile(
    r"^(zh-(?:TW|CN)|en-US|ja-JP)-[A-Za-z0-9]+"
    r"(?::DragonHD(?:Omni|Flash)?LatestNeural|Neural)$"
)
_MESSAGES = deep_freeze({
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
    "ja-JP": {
        "invalid_region": "Azure Speech のリージョン形式が正しくありません。",
        "unsupported_voice": "確認済みの女性音声だけを使用できます。",
        "missing_settings": "Azure Speech のキーとリージョンが未設定です。",
        "credentials": "Azure Speech のキー、リージョン、またはリソース権限が正しくありません。",
        "quota": "Azure Speech の無料枠またはレート上限に達しました。",
        "service": "Azure Speech は一時的に利用できません（HTTP {status}）。",
        "request": "Azure Speech に失敗しました（HTTP {status}）。",
        "network": "Azure Speech に接続できません：{error}",
    },
})


class _PushAudioReader:
    """Adapt Azure's push callback to the playback loop's bounded reads."""

    def __init__(self) -> None:
        self._chunks: queue.Queue[bytes | None] = queue.Queue()
        self._pending = bytearray()

    def write(self, audio_buffer: memoryview) -> int:
        chunk = bytes(audio_buffer)
        if chunk:
            self._chunks.put(chunk)
        return len(chunk)

    def close(self) -> None:
        self._chunks.put(None)

    def read(self, audio_buffer: bytearray) -> int:
        while not self._pending:
            try:
                chunk = self._chunks.get(timeout=60.0)
            except queue.Empty as exc:
                raise TimeoutError("Azure audio stream timed out") from exc
            if chunk is None:
                return 0
            self._pending.extend(chunk)
        bytes_read = min(len(audio_buffer), len(self._pending))
        audio_buffer[:bytes_read] = self._pending[:bytes_read]
        del self._pending[:bytes_read]
        return bytes_read


@dataclass(slots=True)
class _SynthesisOutcome:
    result: object | None = None
    failure: Exception | None = None
    done: threading.Event = field(default_factory=threading.Event)


def _await_synthesis(
    synthesis: object,
    audio_reader: _PushAudioReader,
    outcome: _SynthesisOutcome,
) -> None:
    try:
        outcome.result = synthesis.get()
    except (OSError, RuntimeError, TimeoutError) as exc:
        outcome.failure = exc
    finally:
        audio_reader.close()
        outcome.done.set()


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
        return (
            *AZURE_FEMALE_VOICES["zh-CN"],
            *AZURE_FEMALE_VOICES["zh-TW"],
        )
    if normalized in {"en", "en-us"}:
        return AZURE_FEMALE_VOICES["en-US"]
    if normalized in {"ja", "ja-jp"}:
        return AZURE_FEMALE_VOICES["ja-JP"]
    return (
        *AZURE_FEMALE_VOICES["zh-TW"],
        *AZURE_FEMALE_VOICES["zh-CN"],
    )


def azure_hd_female_voices(
    language: str,
    *,
    include_flash: bool = True,
) -> tuple[str, ...]:
    normalized = str(language or "").strip().lower()
    if normalized in {"en", "en-us"}:
        voices = AZURE_HD_FEMALE_VOICES["en-US"]
    elif normalized in {"ja", "ja-jp"}:
        voices = AZURE_HD_FEMALE_VOICES["ja-JP"]
    else:
        voices = AZURE_HD_FEMALE_VOICES["zh-CN"]
    if include_flash:
        return voices
    return tuple(voice for voice in voices if not azure_hd_voice_uses_flash(voice))


def azure_hd_voice_uses_flash(voice: str) -> bool:
    return ":DragonHDFlash" in str(voice)


def is_azure_hd_voice(voice: str) -> bool:
    return ":DragonHD" in str(voice)


def build_azure_ssml(
    text: str,
    voice: str,
    verified_voices: tuple[str, ...] = (),
) -> bytes:
    is_verified = voice in _VOICE_LOCALE or voice in verified_voices
    if not is_verified or not _VOICE_PATTERN.fullmatch(voice):
        raise ValueError("unsupported_voice")
    locale = _VOICE_LOCALE.get(voice, voice[:5])
    parameters = (
        " parameters='temperature=0.8'"
        if is_azure_hd_voice(voice)
        else ""
    )
    body = (
        f"<speak version='1.0' xml:lang={quoteattr(locale)}>"
        f"<voice xml:lang={quoteattr(locale)} xml:gender='Female' "
        f"name={quoteattr(voice)}{parameters}>{escape(text)}</voice></speak>"
    )
    return body.encode("utf-8")


def _voice_locale(voice: str) -> str:
    return _VOICE_LOCALE.get(voice, voice[:5] if len(voice) >= 5 else "zh-TW")


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
    synthesis_latency_measured = Signal(float)
    viseme_cue = Signal(float, str)
    voice_catalog_ready = Signal(object)
    voice_catalog_failed = Signal(str, str, bool)

    def __init__(
        self,
        parent: QObject | None = None,
        catalog_service: AzureVoiceCatalogService | None = None,
    ):
        super().__init__(parent)
        self.volume_percent = 125
        self.muted = False
        self.last_synthesis_latency_ms: float | None = None
        self._catalog_service = catalog_service or AzureVoiceCatalogService()
        self._verified_dynamic_voices: set[str] = set()

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
        locale = _voice_locale(voice)
        if not api_key.strip() or not region.strip():
            self.failed.emit(_message(locale, "missing_settings"))
            return
        try:
            normalized_region = normalize_azure_region(region)
            build_azure_ssml(
                text,
                voice,
                tuple(self._verified_dynamic_voices),
            )
        except ValueError as exc:
            self.failed.emit(_message(locale, str(exc)))
            return
        threading.Thread(
            target=self._run,
            args=(text, api_key, normalized_region, voice),
            daemon=True,
        ).start()

    def invalidate_voice_catalog(self, region: str | None = None) -> None:
        self._catalog_service.invalidate(region)

    def refresh_voice_catalog(
        self,
        api_key: str,
        region: str,
        language: str,
        *,
        hd_only: bool,
    ) -> None:
        try:
            normalized_region = normalize_azure_region(region)
        except ValueError:
            self.voice_catalog_failed.emit(region, language, hd_only)
            return
        if not api_key.strip():
            self._emit_fallback_catalog(
                normalized_region,
                language,
                hd_only,
            )
            return
        threading.Thread(
            target=self._query_voice_catalog,
            args=(api_key, normalized_region, language, hd_only),
            daemon=True,
        ).start()

    def _query_voice_catalog(
        self,
        api_key: str,
        region: str,
        language: str,
        hd_only: bool,
    ) -> None:
        try:
            catalog = self._catalog_service.query(
                api_key,
                region,
                language,
                hd_only=hd_only,
            )
        except (OSError, RuntimeError, TimeoutError, ValueError):
            self._emit_fallback_catalog(region, language, hd_only)
            return
        self._verified_dynamic_voices.update(catalog.voices)
        self.voice_catalog_ready.emit(catalog)

    def _emit_fallback_catalog(
        self,
        region: str,
        language: str,
        hd_only: bool,
    ) -> None:
        if hd_only:
            voices = azure_hd_female_voices(
                language,
                include_flash=azure_region_supports_hd_flash(region),
            )
        else:
            voices = azure_female_voices(language)
        self.voice_catalog_ready.emit(
            AzureVoiceCatalog(
                region=region,
                language=language,
                hd_only=hd_only,
                voices=voices,
                source="fallback",
            )
        )

    def _run(
        self,
        text: str,
        api_key: str,
        region: str,
        voice: str,
    ) -> None:
        locale = _voice_locale(voice)
        try:
            request_started = time.perf_counter()
            speech_config = speechsdk.SpeechConfig(
                subscription=api_key,
                region=region,
            )
            speech_config.set_speech_synthesis_output_format(
                speechsdk.SpeechSynthesisOutputFormat.Raw24Khz16BitMonoPcm
            )
            audio_reader = _PushAudioReader()

            class StreamCallback(
                speechsdk.audio.PushAudioOutputStreamCallback
            ):
                def __init__(self) -> None:
                    super().__init__()

                def write(self, audio_buffer: memoryview) -> int:
                    return audio_reader.write(audio_buffer)

                def close(self) -> None:
                    audio_reader.close()

            stream_callback = StreamCallback()
            push_stream = speechsdk.audio.PushAudioOutputStream(
                stream_callback
            )
            audio_config = speechsdk.audio.AudioOutputConfig(
                stream=push_stream,
            )
            synthesizer = speechsdk.SpeechSynthesizer(
                speech_config=speech_config,
                audio_config=audio_config,
            )
            synthesis = synthesizer.speak_ssml_async(
                build_azure_ssml(
                    text,
                    voice,
                    tuple(self._verified_dynamic_voices),
                ).decode("utf-8")
            )
            outcome = _SynthesisOutcome()
            result_thread = threading.Thread(
                target=_await_synthesis,
                args=(synthesis, audio_reader, outcome),
                daemon=True,
            )
            result_thread.start()

            def record_first_audio() -> None:
                self.last_synthesis_latency_ms = max(
                    0.0,
                    (time.perf_counter() - request_started) * 1_000.0,
                )
                self.synthesis_latency_measured.emit(
                    self.last_synthesis_latency_ms
                )

            play_pcm16_stream_with_visemes(
                audio_reader.read,
                volume_percent=self.volume_percent,
                muted=self.muted,
                emit_cue=self.viseme_cue.emit,
                on_first_audio=record_first_audio,
            )
            if not outcome.done.wait(timeout=60.0):
                raise TimeoutError("Azure synthesis did not finish")
            if outcome.failure is not None:
                raise outcome.failure
            if outcome.result is None:
                raise RuntimeError("Azure synthesis returned no result")
            result = outcome.result
            if result.reason == speechsdk.ResultReason.Canceled:
                self.failed.emit(_message(locale, "service", status=503))
                return
            self.finished.emit()
        except (OSError, RuntimeError, TimeoutError, ValueError) as exc:
            self.failed.emit(
                _message(locale, "network", error=type(exc).__name__)
            )
