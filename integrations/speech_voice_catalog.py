from __future__ import annotations

lazy import locale
lazy import os
lazy import winreg
lazy from dataclasses import dataclass


@dataclass(frozen=True)
class WindowsVoiceInfo:
    """One installed Windows speech voice with trustworthy metadata."""

    name: str
    culture: str
    gender: str


_KNOWN_FEMALE_VOICE_MARKERS = ("yating", "hanhan")

_KNOWN_MALE_VOICE_MARKERS = ("zhiwei",)


def is_known_male_windows_voice(name: str) -> bool:
    lowered_name = str(name or "").lower()
    return any(marker in lowered_name for marker in _KNOWN_MALE_VOICE_MARKERS)


def _normalized_voice_gender(value: str, name: str) -> str:
    normalized = str(value or "").strip().lower()
    if normalized in {"female", "feminine", "woman"}:
        return "female"
    if normalized in {"male", "masculine", "man"}:
        return "male"
    lowered_name = name.lower()
    if any(marker in lowered_name for marker in _KNOWN_FEMALE_VOICE_MARKERS):
        return "female"
    if is_known_male_windows_voice(lowered_name):
        return "male"
    return "unknown"


def _is_allowed_companion_voice(name: str, gender: str = "") -> bool:
    """Select voices Windows identifies as female.

    Yating and Hanhan remain compatibility fallbacks for older Windows voice
    registrations that omit Gender. Voice entries with unknown gender remain
    outside the selection so the character contract stays consistent.
    """

    lowered_name = name.lower()
    if is_known_male_windows_voice(lowered_name):
        return False
    return _normalized_voice_gender(gender, name) == "female"


def _registry_string(
    attributes,
    value_name: str,
    fallback: str = "",
) -> str:
    try:
        return str(winreg.QueryValueEx(attributes, value_name)[0])
    except OSError:
        return fallback


def _registry_culture(attributes) -> str:
    language = _registry_string(attributes, "Language")
    try:
        locale_id = int(language.split(";", 1)[0], 16)
    except ValueError:
        return ""
    return locale.windows_locale.get(locale_id, "").replace("_", "-")


def _registry_voice(
    root,
    token: str,
    prefix: str,
) -> WindowsVoiceInfo | None:
    with winreg.OpenKey(root, token + r"\Attributes") as attributes:
        name = _registry_string(attributes, "Name", token)
        culture = _registry_culture(attributes)
        full_name = prefix + name
        gender = _normalized_voice_gender(
            _registry_string(attributes, "Gender"),
            full_name,
        )
    if not _is_allowed_companion_voice(full_name, gender):
        return None
    return WindowsVoiceInfo(full_name, culture, gender)


class WindowsVoiceCatalogError(RuntimeError):
    """Windows 語音登錄檔需要重新查詢；它與已安裝語音數量分開表示。"""


def _registry_voices(
    registry_path: str,
    prefix: str,
) -> list[WindowsVoiceInfo]:
    voices: list[WindowsVoiceInfo] = []
    _registry_voices.last_skipped = 0
    try:
        with winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            registry_path,
        ) as root:
            for index in range(winreg.QueryInfoKey(root)[0]):
                token = winreg.EnumKey(root, index)
                try:
                    voice = _registry_voice(root, token, prefix)
                except OSError:
                    # 單一項目讀取問題先保留計數，讓最後結果清楚區分
                    # 部分項目需要查詢與系統確實沒有語音的狀態。
                    _registry_voices.last_skipped += 1
                    continue
                if voice is not None:
                    voices.append(voice)
    except FileNotFoundError:
        # 舊版 Windows 可能沒有 Speech_OneCore 登錄檔；此位置的語音清單為空。
        return []
    except OSError as error:
        # 其餘的 OSError（ACL、登錄檔損毀、暫時性 I/O）代表查詢需要權限或重試；
        # 與「系統沒有安裝任何語音」分開回報，讓使用者看見真正的狀態。
        raise WindowsVoiceCatalogError(
            f"Windows 語音登錄檔讀取需要權限或重試：{registry_path}"
        ) from error
    return voices


def windows_voice_catalog() -> list[WindowsVoiceInfo]:
    """Return installed female OneCore and Desktop SAPI voices."""

    if os.name != "nt":
        return []
    locations = (
        (
            r"SOFTWARE\Microsoft\Speech_OneCore\Voices\Tokens",
            "OneCore::",
        ),
        (r"SOFTWARE\Microsoft\Speech\Voices\Tokens", ""),
    )
    voices: list[WindowsVoiceInfo] = []
    skipped = 0
    for registry_path, prefix in locations:
        voices.extend(_registry_voices(registry_path, prefix))
        skipped += int(getattr(_registry_voices, "last_skipped", 0))
    if not voices and skipped:
        # last_skipped 讓 ACL 讀取問題保留在結果中，避免上層將查詢狀態
        # 與已安裝語音數量混為一談。
        raise WindowsVoiceCatalogError(
            f"Windows 語音登錄檔有 {skipped} 個項目需要權限或重試，尚未取得可用語音"
        )
    return voices


def windows_voices() -> list[tuple[str, str]]:
    return [(voice.name, voice.culture) for voice in windows_voice_catalog()]


def female_windows_voices_for_language(
    voices: list[tuple[str, str]],
    target_language: str,
) -> list[tuple[str, str]]:
    target = str(target_language or "").strip().lower()
    family = target.split("-", 1)[0]
    return [
        (name, culture)
        for name, culture in voices
        if not is_known_male_windows_voice(name)
        and culture.lower().split("-", 1)[0] == family
    ]


def preferred_windows_voice(
    voices: list[tuple[str, str]],
    saved: str = "",
    target_language: str = "zh-TW",
) -> str:
    voices = [
        (name, culture)
        for name, culture in voices
        if not is_known_male_windows_voice(name)
    ]
    installed = dict(voices)
    if saved in installed:
        return saved
    target = str(target_language or "").strip().lower()
    family = target.split("-", 1)[0]
    if target in {"zh", "zh-tw"}:
        for keyword in ("Yating", "Hanhan"):
            for name, culture in voices:
                if keyword.lower() in name.lower() and culture.lower() == "zh-tw":
                    return name
    for name, culture in voices:
        if target and culture.lower() == target:
            return name
    for name, culture in voices:
        if family and culture.lower().split("-", 1)[0] == family:
            return name
    return voices[0][0] if voices else ""
