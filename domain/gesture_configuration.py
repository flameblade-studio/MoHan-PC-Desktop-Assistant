from __future__ import annotations

lazy import math
lazy import uuid
lazy from collections.abc import Mapping, Sequence
lazy from dataclasses import dataclass, replace
lazy from enum import StrEnum
lazy from typing import Final, Self

GESTURE_CONFIGURATION_FORMAT: Final = "mohan-gesture-configuration"
GESTURE_CONFIGURATION_VERSION: Final = 1
MAX_CUSTOM_GESTURES: Final = 32
MAX_SAMPLES_PER_GESTURE: Final = 20
LANDMARKS_PER_HAND: Final = 21


class GestureSource(StrEnum):
    BUILTIN = "builtin"
    CUSTOM = "custom"


class GestureAction(StrEnum):
    NONE = "none"
    SHOW_DASHBOARD = "show-dashboard"
    HIDE_DASHBOARD = "hide-dashboard"
    MUTE_AUDIO = "mute-audio"
    UNMUTE_AUDIO = "unmute-audio"
    STOP_SPEECH = "stop-speech"
    TOGGLE_LISTENING = "toggle-listening"
    START_REALTIME = "start-realtime"
    STOP_REALTIME = "stop-realtime"
    WORK_MODE = "work-mode"
    COMPANION_MODE = "companion-mode"
    DO_NOT_DISTURB_MODE = "do-not-disturb-mode"
    POSITIVE_ACKNOWLEDGEMENT = "positive-acknowledgement"
    CUSTOM_COMMAND = "custom-command"


@dataclass(frozen=True, slots=True)
class LocalizedLabel:
    traditional_chinese: str
    simplified_chinese: str
    english: str
    japanese: str

    def __post_init__(self) -> None:
        if not all(
            value.strip()
            for value in (
                self.traditional_chinese,
                self.simplified_chinese,
                self.english,
                self.japanese,
            )
        ):
            raise ValueError("Every localized label must be complete.")


BUILTIN_GESTURE_LABELS: Final = frozendict({
    "wave": LocalizedLabel("揮手", "挥手", "Wave", "手を振る"),
    "silence": LocalizedLabel("噓聲手勢", "嘘声手势", "Quiet gesture", "静かにの合図"),
    "open-palm": LocalizedLabel("張開手掌", "张开手掌", "Open palm", "開いた手のひら"),
    "closed-fist": LocalizedLabel("握拳", "握拳", "Closed fist", "握りこぶし"),
    "thumbs-up": LocalizedLabel("拇指向上", "拇指向上", "Thumbs up", "親指を立てる"),
    "thumbs-down": LocalizedLabel("拇指向下", "拇指向下", "Thumbs down", "親指を下げる"),
    "point-left": LocalizedLabel("指向左方", "指向左方", "Point left", "左を指す"),
    "point-right": LocalizedLabel("指向右方", "指向右方", "Point right", "右を指す"),
})

GESTURE_ACTION_LABELS: Final = frozendict({
    GestureAction.NONE: LocalizedLabel("不執行動作", "不执行动作", "No action", "何もしない"),
    GestureAction.SHOW_DASHBOARD: LocalizedLabel("顯示控制台", "显示控制台", "Show control center", "コントロールセンターを表示"),
    GestureAction.HIDE_DASHBOARD: LocalizedLabel("隱藏控制台", "隐藏控制台", "Hide control center", "コントロールセンターを隠す"),
    GestureAction.MUTE_AUDIO: LocalizedLabel("靜音", "静音", "Mute audio", "ミュート"),
    GestureAction.UNMUTE_AUDIO: LocalizedLabel("取消靜音", "取消静音", "Unmute audio", "ミュート解除"),
    GestureAction.STOP_SPEECH: LocalizedLabel("停止目前語音", "停止当前语音", "Stop current speech", "現在の発話を停止"),
    GestureAction.TOGGLE_LISTENING: LocalizedLabel("切換語音聆聽", "切换语音聆听", "Toggle listening", "音声入力を切り替え"),
    GestureAction.START_REALTIME: LocalizedLabel("啟動 Realtime 對話", "启动 Realtime 对话", "Start Realtime conversation", "Realtime 会話を開始"),
    GestureAction.STOP_REALTIME: LocalizedLabel("停止 Realtime 對話", "停止 Realtime 对话", "Stop Realtime conversation", "Realtime 会話を停止"),
    GestureAction.WORK_MODE: LocalizedLabel("切換工作模式", "切换工作模式", "Switch to work mode", "仕事モードへ切り替え"),
    GestureAction.COMPANION_MODE: LocalizedLabel("切換陪伴模式", "切换陪伴模式", "Switch to companion mode", "コンパニオンモードへ切り替え"),
    GestureAction.DO_NOT_DISTURB_MODE: LocalizedLabel("切換勿擾模式", "切换勿扰模式", "Switch to do-not-disturb mode", "おやすみモードへ切り替え"),
    GestureAction.POSITIVE_ACKNOWLEDGEMENT: LocalizedLabel("墨寒以正向表情回應", "墨寒以正向表情回应", "MoHan responds positively", "墨寒が肯定的に応える"),
    GestureAction.CUSTOM_COMMAND: LocalizedLabel("自訂墨寒文字指令", "自定义墨寒文字指令", "Custom MoHan text command", "墨寒のカスタム文字指示"),
})


@dataclass(frozen=True, slots=True)
class GestureBinding:
    action: GestureAction = GestureAction.NONE
    custom_command: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.action, GestureAction):
            raise TypeError("Gesture action must be canonical.")
        command = self.custom_command.strip()
        if len(command) > 256 or any(character in command for character in "\r\n\0"):
            raise ValueError("Custom gesture commands must be one short text command.")
        if self.action is GestureAction.CUSTOM_COMMAND and not command:
            raise ValueError("A custom-command binding requires command text.")
        if self.action is not GestureAction.CUSTOM_COMMAND and command:
            raise ValueError("Only custom-command bindings may contain command text.")


@dataclass(frozen=True, slots=True)
class GestureLandmark:
    """One normalized hand point; no image or identifying pixels are retained."""

    x: float
    y: float
    z: float = 0.0

    def __post_init__(self) -> None:
        if not all(math.isfinite(value) and -8.0 <= value <= 8.0 for value in (self.x, self.y, self.z)):
            raise ValueError("Gesture landmark coordinates are invalid.")


@dataclass(frozen=True, slots=True)
class GestureSample:
    landmarks: tuple[GestureLandmark, ...]

    def __post_init__(self) -> None:
        if len(self.landmarks) != LANDMARKS_PER_HAND:
            raise ValueError("A gesture sample must contain exactly 21 hand landmarks.")


@dataclass(frozen=True, slots=True)
class GestureDefinition:
    gesture_id: str
    display_name: str
    source: GestureSource
    enabled: bool = True
    binding: GestureBinding = GestureBinding()
    samples: tuple[GestureSample, ...] = ()

    def __post_init__(self) -> None:
        identifier = self.gesture_id.strip()
        name = self.display_name.strip()
        if not identifier or len(identifier) > 80 or not name or len(name) > 80:
            raise ValueError("Gesture identity and display name must be short and explicit.")
        if any(character.isspace() for character in identifier):
            raise ValueError("Gesture identifiers cannot contain whitespace.")
        if not isinstance(self.source, GestureSource) or type(self.enabled) is not bool:
            raise TypeError("Gesture source and enabled state are invalid.")
        if self.source is GestureSource.BUILTIN:
            if identifier not in BUILTIN_GESTURE_LABELS or self.samples:
                raise ValueError("Built-in gestures use the audited detector catalog.")
        elif not identifier.startswith("custom:"):
            raise ValueError("Custom gesture identifiers must use the custom namespace.")
        if len(self.samples) > MAX_SAMPLES_PER_GESTURE:
            raise ValueError("A custom gesture has too many samples.")

    def with_binding(self, binding: GestureBinding) -> Self:
        return replace(self, binding=binding)


DEFAULT_GESTURE_BINDINGS: Final = frozendict({
    "wave": GestureBinding(GestureAction.SHOW_DASHBOARD),
    "silence": GestureBinding(GestureAction.MUTE_AUDIO),
    "open-palm": GestureBinding(GestureAction.STOP_SPEECH),
    "closed-fist": GestureBinding(),
    "thumbs-up": GestureBinding(GestureAction.POSITIVE_ACKNOWLEDGEMENT),
    "thumbs-down": GestureBinding(),
    "point-left": GestureBinding(),
    "point-right": GestureBinding(),
})


def default_gesture_definitions() -> tuple[GestureDefinition, ...]:
    return tuple(
        GestureDefinition(
            gesture_id,
            labels.traditional_chinese,
            GestureSource.BUILTIN,
            binding=DEFAULT_GESTURE_BINDINGS[gesture_id],
        )
        for gesture_id, labels in BUILTIN_GESTURE_LABELS.items()
    )


@dataclass(frozen=True, slots=True)
class GestureConfiguration:
    enabled: bool = False
    definitions: tuple[GestureDefinition, ...] = default_gesture_definitions()

    def __post_init__(self) -> None:
        if type(self.enabled) is not bool:
            raise TypeError("Gesture recognition enabled state must be boolean.")
        identifiers = tuple(definition.gesture_id for definition in self.definitions)
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("Gesture identifiers must be unique.")
        custom_count = sum(
            definition.source is GestureSource.CUSTOM
            for definition in self.definitions
        )
        if custom_count > MAX_CUSTOM_GESTURES:
            raise ValueError("Too many custom gestures are configured.")
        missing = set(BUILTIN_GESTURE_LABELS) - set(identifiers)
        if missing:
            raise ValueError("The built-in gesture catalog must remain recoverable.")

    def add_custom(
        self,
        display_name: str,
        samples: Sequence[GestureSample] = (),
        *,
        binding: GestureBinding | None = None,
        gesture_id: str | None = None,
    ) -> Self:
        identifier = gesture_id or f"custom:{uuid.uuid4()}"
        definition = GestureDefinition(
            identifier,
            display_name,
            GestureSource.CUSTOM,
            binding=binding or GestureBinding(),
            samples=tuple(samples),
        )
        return replace(self, definitions=(*self.definitions, definition))

    def remove_custom(self, gesture_id: str) -> Self:
        target = self.definition(gesture_id)
        if target.source is GestureSource.BUILTIN:
            raise ValueError("Built-in gestures can be disabled or reset, not deleted.")
        return replace(
            self,
            definitions=tuple(
                definition
                for definition in self.definitions
                if definition.gesture_id != gesture_id
            ),
        )

    def replace_definition(self, updated: GestureDefinition) -> Self:
        current = self.definition(updated.gesture_id)
        if current.source is not updated.source:
            raise ValueError("Gesture source cannot change during an edit.")
        return replace(
            self,
            definitions=tuple(
                updated if definition.gesture_id == updated.gesture_id else definition
                for definition in self.definitions
            ),
        )

    def reset_builtin(self, gesture_id: str) -> Self:
        current = self.definition(gesture_id)
        if current.source is not GestureSource.BUILTIN:
            raise ValueError("Only built-in gestures have audited defaults.")
        labels = BUILTIN_GESTURE_LABELS[gesture_id]
        return self.replace_definition(
            GestureDefinition(
                gesture_id,
                labels.traditional_chinese,
                GestureSource.BUILTIN,
                binding=DEFAULT_GESTURE_BINDINGS[gesture_id],
            )
        )

    def definition(self, gesture_id: str) -> GestureDefinition:
        match = next(
            (
                definition
                for definition in self.definitions
                if definition.gesture_id == gesture_id
            ),
            None,
        )
        if match is None:
            raise KeyError("Unknown gesture identifier.")
        return match


def export_gesture_configuration(
    configuration: GestureConfiguration,
    *,
    include_samples: bool = False,
) -> dict[str, object]:
    if not isinstance(configuration, GestureConfiguration):
        raise TypeError("Gesture configuration is invalid.")
    if type(include_samples) is not bool:
        raise TypeError("Gesture sample export policy must be boolean.")
    return {
        "format": GESTURE_CONFIGURATION_FORMAT,
        "version": GESTURE_CONFIGURATION_VERSION,
        "enabled": configuration.enabled,
        "definitions": [
            _definition_payload(item, include_samples=include_samples)
            for item in configuration.definitions
        ],
    }


def import_gesture_configuration(
    payload: object,
    *,
    include_samples: bool = False,
) -> GestureConfiguration:
    if type(include_samples) is not bool:
        raise TypeError("Gesture sample import policy must be boolean.")
    if not isinstance(payload, Mapping):
        return GestureConfiguration()
    if payload.get("format") != GESTURE_CONFIGURATION_FORMAT:
        return GestureConfiguration()
    if payload.get("version") != GESTURE_CONFIGURATION_VERSION:
        raise ValueError("Gesture configuration version is unsupported.")
    try:
        enabled = payload.get("enabled", False)
        if type(enabled) is not bool:
            raise TypeError("Gesture enabled state is invalid.")
        raw_definitions = payload.get("definitions", ())
        if not isinstance(raw_definitions, Sequence) or isinstance(raw_definitions, (str, bytes)):
            raise TypeError("Gesture definitions must be a sequence.")
        parsed = tuple(
            _definition_from_payload(item, include_samples=include_samples)
            for item in raw_definitions
        )
        return GestureConfiguration(enabled, _restore_missing_builtins(parsed))
    except (KeyError, TypeError, ValueError):
        return GestureConfiguration()


def _restore_missing_builtins(
    definitions: tuple[GestureDefinition, ...],
) -> tuple[GestureDefinition, ...]:
    by_identifier = {definition.gesture_id: definition for definition in definitions}
    builtins = tuple(
        by_identifier.get(default.gesture_id, default)
        for default in default_gesture_definitions()
    )
    custom = tuple(
        definition
        for definition in definitions
        if definition.source is GestureSource.CUSTOM
    )
    return (*builtins, *custom)


def _definition_payload(
    definition: GestureDefinition,
    *,
    include_samples: bool,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "gesture_id": definition.gesture_id,
        "display_name": definition.display_name,
        "source": definition.source.value,
        "enabled": definition.enabled,
        "binding": {
            "action": definition.binding.action.value,
            "custom_command": definition.binding.custom_command,
        },
    }
    if include_samples:
        payload["samples"] = [
            [[point.x, point.y, point.z] for point in sample.landmarks]
            for sample in definition.samples
        ]
    return payload


def _definition_from_payload(
    payload: object,
    *,
    include_samples: bool,
) -> GestureDefinition:
    if not isinstance(payload, Mapping):
        raise TypeError("Gesture definition must be an object.")
    binding_payload = payload.get("binding", {})
    if not isinstance(binding_payload, Mapping):
        raise TypeError("Gesture binding must be an object.")
    samples_payload: object = payload.get("samples", ()) if include_samples else ()
    if not isinstance(samples_payload, Sequence) or isinstance(
        samples_payload,
        (str, bytes),
    ):
        raise TypeError("Gesture samples must be a sequence.")
    return GestureDefinition(
        str(payload["gesture_id"]),
        str(payload["display_name"]),
        GestureSource(payload["source"]),
        _strict_bool(payload.get("enabled", True)),
        GestureBinding(
            GestureAction(binding_payload.get("action", GestureAction.NONE.value)),
            str(binding_payload.get("custom_command", "")),
        ),
        tuple(_sample_from_payload(sample) for sample in samples_payload),
    )


def _sample_from_payload(payload: object) -> GestureSample:
    if not isinstance(payload, Sequence) or isinstance(payload, (str, bytes)):
        raise TypeError("Gesture sample landmarks must be a sequence.")
    landmarks: list[GestureLandmark] = []
    for coordinates in payload:
        if not isinstance(coordinates, Sequence) or isinstance(coordinates, (str, bytes)):
            raise TypeError("Gesture landmark coordinates must be a sequence.")
        if len(coordinates) != 3:
            raise ValueError("Gesture landmark coordinates must contain x, y and z.")
        x, y, z = coordinates
        if not all(type(value) in {int, float} for value in (x, y, z)):
            raise TypeError("Gesture landmark coordinates must be numeric.")
        landmarks.append(GestureLandmark(float(x), float(y), float(z)))
    return GestureSample(tuple(landmarks))


def _strict_bool(value: object) -> bool:
    if type(value) is not bool:
        raise TypeError("Gesture flag must be boolean.")
    return value
