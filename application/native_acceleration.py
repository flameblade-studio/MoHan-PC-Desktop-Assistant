"""Optional native acceleration with an observable Python fallback."""

from __future__ import annotations

lazy import importlib
lazy import logging
lazy import math
lazy import threading
lazy from collections.abc import Callable
lazy from dataclasses import dataclass
lazy from types import ModuleType
lazy from typing import TypeVar, cast

lazy from domain import lip_sync as python_lip_sync
lazy from domain import pcm_audio as python_pcm_audio

# Re-exported from the centralized constants module for a single source of truth.
lazy from domain.constants import PCM16_MAX_SAMPLE as MAX_PCM16_SAMPLE, PCM16_MIN_SAMPLE as MIN_PCM16_SAMPLE

LOGGER = logging.getLogger(__name__)
NATIVE_MODULE_NAME = "_mohan_accel"
PAIR_LENGTH = 2
_Result = TypeVar("_Result")


@dataclass(frozen=True, slots=True)
class NativeAccelerationStatus:
    """Current optional-accelerator state without exposing audio data."""

    available: bool
    module_name: str
    version: str | None
    load_error: str | None
    verified_operations: tuple[str, ...]
    disabled_operations: tuple[str, ...]
    operation_failures: tuple[tuple[str, int], ...]


class NativeAcceleration:
    """Dispatch supported pure-numeric operations to Rust when available."""

    def __init__(
        self,
        module_loader: Callable[[str], ModuleType] | None = None,
    ) -> None:
        self._module_loader = module_loader or importlib.import_module
        self._module: ModuleType | None = None
        self._load_attempted = False
        self._load_error: str | None = None
        self._verified_operations: set[str] = set()
        self._disabled_operations: set[str] = set()
        self._operation_failures: dict[str, int] = {}
        self._lock = threading.Lock()

    def status(self) -> NativeAccelerationStatus:
        """Return diagnostics after attempting the optional import at most once."""
        module = self._load_module()
        version = (
            None if module is None else str(getattr(module, "__version__", "unknown"))
        )
        with self._lock:
            verified = tuple(sorted(self._verified_operations))
            disabled = tuple(sorted(self._disabled_operations))
            failures = tuple(sorted(self._operation_failures.items()))
            load_error = self._load_error
        return NativeAccelerationStatus(
            available=module is not None,
            module_name=NATIVE_MODULE_NAME,
            version=version,
            load_error=load_error,
            verified_operations=verified,
            disabled_operations=disabled,
            operation_failures=failures,
        )

    def analyze_pcm16(
        self,
        pcm: python_pcm_audio.Pcm16Buffer,
    ) -> tuple[float, float]:
        pcm = python_lip_sync.validate_pcm16_analysis_request(pcm)
        return self._call(
            "analyze_pcm16",
            (pcm,),
            lambda: python_lip_sync.analyze_pcm16(pcm),
            normalize=_normalize_analysis_result,
        )

    def infer_vowel_pcm16(
        self,
        pcm: python_pcm_audio.Pcm16Buffer,
        sample_rate: int = 24_000,
    ) -> tuple[float, str]:
        pcm, sample_rate = python_lip_sync.validate_vowel_inference_request(
            pcm,
            sample_rate,
        )
        return self._call(
            "infer_vowel_pcm16",
            (pcm, sample_rate),
            lambda: python_lip_sync.infer_vowel_pcm16(pcm, sample_rate),
            normalize=_normalize_vowel_result,
        )

    def scale_pcm16(
        self,
        data: python_pcm_audio.Pcm16Buffer,
        factor: float,
    ) -> bytes:
        data, factor = python_pcm_audio.validate_scale_pcm16_request(
            data,
            factor,
        )
        return self._call(
            "scale_pcm16",
            (data, factor),
            lambda: python_pcm_audio.scale_pcm16(data, factor),
            normalize=_normalize_bytes_result,
        )

    def stereo_to_mono_pcm16(
        self,
        data: python_pcm_audio.Pcm16Buffer,
        left_factor: float = 0.5,
        right_factor: float = 0.5,
    ) -> bytes:
        data, left_factor, right_factor = (
            python_pcm_audio.validate_stereo_to_mono_pcm16_request(
                data,
                left_factor,
                right_factor,
            )
        )
        return self._call(
            "stereo_to_mono_pcm16",
            (data, left_factor, right_factor),
            lambda: python_pcm_audio.stereo_to_mono_pcm16(
                data,
                left_factor,
                right_factor,
            ),
            normalize=_normalize_bytes_result,
        )

    def rate_convert_pcm16(
        self,
        data: python_pcm_audio.Pcm16Buffer,
        channels: int,
        input_rate: int,
        output_rate: int,
        state: python_pcm_audio.Pcm16RateState | None = None,
    ) -> tuple[bytes, python_pcm_audio.Pcm16RateState | None]:
        data = python_pcm_audio.validate_rate_conversion_request(
            data,
            channels,
            input_rate,
            output_rate,
            state,
        )
        payload = None if state is None else (state.tail_frame, state.phase)

        def fallback() -> tuple[bytes, python_pcm_audio.Pcm16RateState | None]:
            return python_pcm_audio.rate_convert_pcm16(
                data,
                channels,
                input_rate,
                output_rate,
                state,
            )

        return self._call(
            "rate_convert_pcm16",
            (data, channels, input_rate, output_rate, payload),
            fallback,
            normalize=lambda result: _normalize_rate_result(
                result,
                channels=channels,
            ),
        )

    def _call(
        self,
        operation: str,
        arguments: tuple[object, ...],
        fallback: Callable[[], _Result],
        *,
        normalize: Callable[[object], _Result] | None = None,
    ) -> _Result:
        module = self._load_module()
        if module is None or self._operation_is_disabled(operation):
            return fallback()
        try:
            native_operation = getattr(module, operation)
            result = native_operation(*arguments)
            native_result = cast(_Result, result) if normalize is None else normalize(result)
        except Exception as error:
            expected = fallback()
            self._observe_operation_failure(operation, error)
            return expected
        if not self._operation_is_verified(operation):
            try:
                expected = fallback()
            except Exception:
                self._disable_operation(
                    operation,
                    RuntimeError(
                        "native PCM operation accepted input rejected by "
                        "the Python contract"
                    ),
                )
                raise
            if not _results_are_equivalent(operation, native_result, expected):
                self._disable_operation(
                    operation,
                    RuntimeError("native PCM result failed reference verification"),
                )
                return expected
            self._mark_verified(operation)
        return native_result

    def _load_module(self) -> ModuleType | None:
        if self._load_attempted:
            return self._module
        with self._lock:
            if self._load_attempted:
                return self._module
            try:
                self._module = self._module_loader(NATIVE_MODULE_NAME)
            except Exception as error:
                self._load_error = _error_summary(error)
                LOGGER.info(
                    "MoHan native acceleration is unavailable; using Python: %s",
                    self._load_error,
                )
            finally:
                self._load_attempted = True
        return self._module

    def _observe_operation_failure(self, operation: str, error: Exception) -> None:
        self._disable_operation(operation, error)

    def _disable_operation(self, operation: str, error: Exception) -> None:
        with self._lock:
            self._disabled_operations.add(operation)
            self._verified_operations.discard(operation)
            count = self._operation_failures.get(operation, 0) + 1
            self._operation_failures[operation] = count
        LOGGER.warning(
            "MoHan native operation %s failed; using Python fallback (failure %d): %s",
            operation,
            count,
            type(error).__name__,
        )

    def _operation_is_disabled(self, operation: str) -> bool:
        with self._lock:
            return operation in self._disabled_operations

    def _operation_is_verified(self, operation: str) -> bool:
        with self._lock:
            return operation in self._verified_operations

    def _mark_verified(self, operation: str) -> None:
        with self._lock:
            if operation not in self._disabled_operations:
                self._verified_operations.add(operation)


def _error_summary(error: Exception) -> str:
    message = str(error).strip()
    return type(error).__name__ if not message else f"{type(error).__name__}: {message}"


def _results_are_equivalent(
    operation: str,
    native_result: object,
    python_result: object,
) -> bool:
    if operation == "analyze_pcm16":
        return _float_pair_is_close(native_result, python_result)
    if operation == "infer_vowel_pcm16":
        if not isinstance(native_result, tuple) or not isinstance(python_result, tuple):
            return False
        return (
            len(native_result) == PAIR_LENGTH
            and len(python_result) == PAIR_LENGTH
            and native_result[1] == python_result[1]
            and math.isclose(
                float(native_result[0]),
                float(python_result[0]),
                rel_tol=1e-12,
                abs_tol=1e-12,
            )
        )
    return native_result == python_result


def _float_pair_is_close(left: object, right: object) -> bool:
    if not isinstance(left, tuple) or not isinstance(right, tuple):
        return False
    if len(left) != PAIR_LENGTH or len(right) != PAIR_LENGTH:
        return False
    return all(
        math.isclose(
            float(actual),
            float(expected),
            rel_tol=1e-12,
            abs_tol=1e-12,
        )
        for actual, expected in zip(left, right, strict=True)
    )


def _normalize_analysis_result(result: object) -> tuple[float, float]:
    if not isinstance(result, tuple) or len(result) != PAIR_LENGTH:
        raise TypeError("native analysis returned an invalid result")
    loudness, articulation = result
    if not isinstance(loudness, float) or not isinstance(articulation, float):
        raise TypeError("native analysis returned non-floating-point values")
    if not math.isfinite(loudness) or not math.isfinite(articulation):
        raise ValueError("native analysis returned non-finite values")
    if not 0.0 <= loudness <= 1.0 or not 0.0 <= articulation <= 1.0:
        raise ValueError("native analysis returned values outside the normalized range")
    return loudness, articulation


def _normalize_vowel_result(result: object) -> tuple[float, str]:
    if not isinstance(result, tuple) or len(result) != PAIR_LENGTH:
        raise TypeError("native vowel inference returned an invalid result")
    level, vowel = result
    if not isinstance(level, float) or not math.isfinite(level):
        raise TypeError("native vowel inference returned an invalid level")
    if not 0.0 <= level <= 1.0:
        raise ValueError(
            "native vowel inference returned a level outside the normalized range"
        )
    if not isinstance(vowel, str) or vowel not in python_lip_sync.VALID_VISEMES:
        raise ValueError("native vowel inference returned an invalid viseme")
    return level, vowel


def _normalize_bytes_result(result: object) -> bytes:
    if not isinstance(result, bytes):
        raise TypeError("native PCM16 operation did not return bytes")
    return result


def _normalize_rate_result(
    result: object,
    *,
    channels: int,
) -> tuple[bytes, python_pcm_audio.Pcm16RateState | None]:
    if not isinstance(result, tuple) or len(result) != PAIR_LENGTH:
        raise TypeError("native rate conversion returned an invalid result")
    converted, native_state = result
    if not isinstance(converted, bytes):
        raise TypeError("native rate conversion did not return bytes")
    if native_state is None:
        return converted, None
    if not isinstance(native_state, tuple) or len(native_state) != PAIR_LENGTH:
        raise TypeError("native rate conversion returned an invalid state")
    tail_frame, phase = native_state
    if not isinstance(tail_frame, (list, tuple)) or not isinstance(phase, int):
        raise TypeError("native rate conversion returned an invalid state")
    if any(not isinstance(sample, int) for sample in tail_frame):
        raise TypeError("native rate conversion returned invalid PCM16 samples")
    if len(tail_frame) != channels:
        raise ValueError("native rate conversion returned a mismatched channel state")
    if any(not MIN_PCM16_SAMPLE <= sample <= MAX_PCM16_SAMPLE for sample in tail_frame):
        raise ValueError("native rate conversion returned out-of-range PCM16 samples")
    if phase < 0:
        raise ValueError("native rate conversion returned a negative phase")
    return converted, python_pcm_audio.Pcm16RateState(
        tail_frame=tuple(tail_frame),
        phase=phase,
    )
