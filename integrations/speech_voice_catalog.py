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
    """Allow only voices Windows identifies as female.

    Yating and Hanhan remain compatibility fallbacks for older Windows voice
    registrations that omit Gender. Unknown voices are deliberately excluded:
    silently falling back to a possibly male system voice would violate the
    character contract.
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


def _registry_voices(
    registry_path: str,
    prefix: str,
) -> list[WindowsVoiceInfo]:
    voices: list[WindowsVoiceInfo] = []
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
                    continue
                if voice is not None:
                    voices.append(voice)
    except OSError:
        return []
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
    return [
        *_registry_voices(registry_path, prefix) for registry_path, prefix in locations
    ]


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
