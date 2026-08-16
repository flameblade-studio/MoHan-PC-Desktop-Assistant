"""Optional bit-exact native acceleration for RGBA rendering hot paths."""

from __future__ import annotations

lazy import importlib
lazy import logging
lazy import sys
lazy import threading
lazy from collections.abc import Callable, Sequence
lazy from dataclasses import dataclass
lazy from types import ModuleType

LOGGER = logging.getLogger(__name__)
NATIVE_RGBA_MODULE_NAME = "_mohan_accel"
RGBA_CHANNELS = 4
ALPHA_MAX = 255
CROSSFADE_MAX = 65_535


class RgbaAccelerationError(ValueError):
    """The RGBA operation violates the renderer's public data contract."""


@dataclass(frozen=True, slots=True)
class NativeRgbaAccelerationStatus:
    """Observable native state that never contains image data."""

    available: bool
    module_name: str
    version: str | None
    load_error: str | None
    verified_operations: tuple[str, ...]
    disabled_operations: tuple[str, ...]
    operation_failures: tuple[tuple[str, int], ...]


def alpha_over_rgba_python(target: bytes, source: bytes) -> bytes:
    """Return source-over-target RGBA using the established integer formula."""
    _validate_equal_rgba(target, source)
    output = bytearray(target)
    for index in range(0, len(source), RGBA_CHANNELS):
        _blend_pixel(output, index, source, index)
    return bytes(output)


def crossfade_rgba_python(
    first: bytes,
    second: bytes,
    second_weight: int,
) -> bytes:
    """Crossfade two same-sized frames with a 16-bit integer weight."""
    _validate_equal_rgba(first, second)
    _validate_crossfade_weight(second_weight)
    first_weight = CROSSFADE_MAX - second_weight
    return bytes(
        (left * first_weight + right * second_weight + CROSSFADE_MAX // 2)
        // CROSSFADE_MAX
        for left, right in zip(first, second, strict=True)
    )


def composite_region_rgba_python(  # noqa: PLR0913, PLR0917 -- typed pixel contract
    target: bytes,
    target_width: int,
    target_height: int,
    source: bytes,
    source_width: int,
    source_height: int,
    anchor_x: int,
    anchor_y: int,
    approved_region: bytes,
    immutable_identity: bytes,
    occlusion_masks: Sequence[bytes] = (),
) -> bytes:
    """Composite one anchored layer while enforcing masks and canvas bounds."""
    masks = tuple(occlusion_masks)
    _validate_region_inputs(
        target,
        target_width,
        target_height,
        source,
        source_width,
        source_height,
        anchor_x,
        anchor_y,
        approved_region,
        immutable_identity,
        masks,
    )

    output = bytearray(target)
    for source_y in range(source_height):
        for source_x in range(source_width):
            source_pixel = source_y * source_width + source_x
            source_index = source_pixel * RGBA_CHANNELS
            if source[source_index + 3] == 0:
                continue
            target_x = anchor_x + source_x
            target_y = anchor_y + source_y
            if not (0 <= target_x < target_width and 0 <= target_y < target_height):
                raise RgbaAccelerationError(
                    "Visible source pixel leaves the target canvas."
                )
            target_pixel = target_y * target_width + target_x
            if any(mask[target_pixel] for mask in masks):
                continue
            if immutable_identity[target_pixel] or not approved_region[target_pixel]:
                raise RgbaAccelerationError(
                    "Visible source pixel leaves its approved target region."
                )
            _blend_pixel(
                output,
                target_pixel * RGBA_CHANNELS,
                source,
                source_index,
            )
    return bytes(output)


class NativeRgbaAcceleration:
    """Use Rust when available and transparently preserve Python semantics."""

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

    def status(self) -> NativeRgbaAccelerationStatus:
        """Return deterministic diagnostics without exposing pixel buffers."""
        module = self._load_module()
        version = (
            None if module is None else str(getattr(module, "__version__", "unknown"))
        )
        with self._lock:
            return NativeRgbaAccelerationStatus(
                available=module is not None,
                module_name=NATIVE_RGBA_MODULE_NAME,
                version=version,
                load_error=self._load_error,
                verified_operations=tuple(sorted(self._verified_operations)),
                disabled_operations=tuple(sorted(self._disabled_operations)),
                operation_failures=tuple(sorted(self._operation_failures.items())),
            )

    def alpha_over_rgba(self, target: bytes, source: bytes) -> bytes:
        _validate_equal_rgba(target, source)
        return self._call_bytes(
            "alpha_over_rgba",
            (target, source),
            lambda: alpha_over_rgba_python(target, source),
            expected_length=len(target),
        )

    def crossfade_rgba(
        self,
        first: bytes,
        second: bytes,
        second_weight: int,
    ) -> bytes:
        _validate_equal_rgba(first, second)
        _validate_crossfade_weight(second_weight)
        return self._call_bytes(
            "crossfade_rgba",
            (first, second, second_weight),
            lambda: crossfade_rgba_python(first, second, second_weight),
            expected_length=len(first),
        )

    def composite_region_rgba(  # noqa: PLR0913, PLR0917 -- typed pixel contract
        self,
        target: bytes,
        target_width: int,
        target_height: int,
        source: bytes,
        source_width: int,
        source_height: int,
        anchor_x: int,
        anchor_y: int,
        approved_region: bytes,
        immutable_identity: bytes,
        occlusion_masks: Sequence[bytes] = (),
    ) -> bytes:
        masks = tuple(occlusion_masks)
        _validate_region_inputs(
            target,
            target_width,
            target_height,
            source,
            source_width,
            source_height,
            anchor_x,
            anchor_y,
            approved_region,
            immutable_identity,
            masks,
        )
        return self._call_bytes(
            "composite_region_rgba",
            (
                target,
                target_width,
                target_height,
                source,
                source_width,
                source_height,
                anchor_x,
                anchor_y,
                approved_region,
                immutable_identity,
                masks,
            ),
            lambda: composite_region_rgba_python(
                target,
                target_width,
                target_height,
                source,
                source_width,
                source_height,
                anchor_x,
                anchor_y,
                approved_region,
                immutable_identity,
                masks,
            ),
            expected_length=len(target),
        )

    def _call_bytes(
        self,
        operation: str,
        arguments: tuple[object, ...],
        fallback: Callable[[], bytes],
        *,
        expected_length: int,
    ) -> bytes:
        module = self._load_module()
        if module is None or self._operation_is_disabled(operation):
            return fallback()
        try:
            native_operation = getattr(module, operation)
            native_result = native_operation(*arguments)
        except Exception as native_error:  # noqa: BLE001 -- isolated native boundary
            return self._fallback_after_native_failure(
                operation,
                native_error,
                fallback,
            )
        if (
            not isinstance(native_result, bytes)
            or len(native_result) != expected_length
        ):
            expected = fallback()
            self._disable_operation(
                operation,
                TypeError("native RGBA operation returned an invalid buffer"),
            )
            return expected
        if not self._operation_is_verified(operation):
            try:
                expected = fallback()
            except Exception:
                self._disable_operation(
                    operation,
                    RuntimeError(
                        "native RGBA operation accepted input rejected by "
                        "the Python contract"
                    ),
                )
                raise
            if native_result != expected:
                self._disable_operation(
                    operation,
                    RuntimeError("native RGBA result failed bit-exact verification"),
                )
                return expected
            self._mark_verified(operation)
        return native_result

    def _fallback_after_native_failure(
        self,
        operation: str,
        native_error: Exception,
        fallback: Callable[[], bytes],
    ) -> bytes:
        self._disable_operation(operation, native_error)
        return fallback()

    def _load_module(self) -> ModuleType | None:
        if self._load_attempted:
            return self._module
        with self._lock:
            if self._load_attempted:
                return self._module
            try:
                self._module = self._module_loader(NATIVE_RGBA_MODULE_NAME)
            except Exception as error:  # noqa: BLE001 -- import-time native fault
                self._load_error = _error_summary(error)
                LOGGER.info(
                    "MoHan native RGBA acceleration is unavailable; using Python: %s",
                    self._load_error,
                )
            finally:
                self._load_attempted = True
        return self._module

    def _operation_is_verified(self, operation: str) -> bool:
        with self._lock:
            return operation in self._verified_operations

    def _operation_is_disabled(self, operation: str) -> bool:
        with self._lock:
            return operation in self._disabled_operations

    def _mark_verified(self, operation: str) -> None:
        with self._lock:
            if operation not in self._disabled_operations:
                self._verified_operations.add(operation)

    def _disable_operation(self, operation: str, error: Exception) -> None:
        with self._lock:
            self._disabled_operations.add(operation)
            self._verified_operations.discard(operation)
            count = self._operation_failures.get(operation, 0) + 1
            self._operation_failures[operation] = count
        LOGGER.warning(
            "MoHan native RGBA operation %s failed; using Python fallback "
            "(failure %d): %s",
            operation,
            count,
            type(error).__name__,
        )


def _validate_equal_rgba(first: bytes, second: bytes) -> None:
    _validate_bytes(first)
    _validate_bytes(second)
    if len(first) != len(second):
        raise RgbaAccelerationError("RGBA frame sizes must match.")
    if len(first) % RGBA_CHANNELS:
        raise RgbaAccelerationError("RGBA data length must be divisible by four.")


def _validate_crossfade_weight(second_weight: int) -> None:
    if (
        not isinstance(second_weight, int)
        or isinstance(second_weight, bool)
        or not 0 <= second_weight <= CROSSFADE_MAX
    ):
        raise RgbaAccelerationError(
            "Crossfade weight must be an integer between 0 and 65535."
        )


def _validate_region_inputs(  # noqa: PLR0913, PLR0917 -- typed pixel contract
    target: bytes,
    target_width: int,
    target_height: int,
    source: bytes,
    source_width: int,
    source_height: int,
    anchor_x: int,
    anchor_y: int,
    approved_region: bytes,
    immutable_identity: bytes,
    occlusion_masks: Sequence[bytes],
) -> None:
    target_pixels = _pixel_count(target_width, target_height)
    source_pixels = _pixel_count(source_width, source_height)
    _validate_rgba_size(target, target_pixels)
    _validate_rgba_size(source, source_pixels)
    _validate_coordinate(anchor_x)
    _validate_coordinate(anchor_y)
    _validate_mask(approved_region, target_pixels)
    _validate_mask(immutable_identity, target_pixels)
    for mask in occlusion_masks:
        _validate_mask(mask, target_pixels)


def _pixel_count(width: int, height: int) -> int:
    if (
        not isinstance(width, int)
        or isinstance(width, bool)
        or not isinstance(height, int)
        or isinstance(height, bool)
        or width <= 0
        or height <= 0
    ):
        raise RgbaAccelerationError("RGBA canvas dimensions must be positive integers.")
    return width * height


def _validate_rgba_size(data: bytes, pixels: int) -> None:
    _validate_bytes(data)
    if len(data) != pixels * RGBA_CHANNELS:
        raise RgbaAccelerationError("RGBA data size does not match its dimensions.")


def _validate_coordinate(value: int) -> None:
    if not isinstance(value, int) or isinstance(value, bool):
        raise RgbaAccelerationError("RGBA anchors must be integers.")
    if not -sys.maxsize - 1 <= value <= sys.maxsize:
        raise RgbaAccelerationError("RGBA anchor exceeds the supported range.")


def _validate_mask(mask: bytes, pixels: int) -> None:
    _validate_bytes(mask)
    if len(mask) != pixels or any(value not in (0, 1) for value in mask):
        raise RgbaAccelerationError(
            "RGBA masks must be binary and match the target canvas."
        )


def _validate_bytes(data: object) -> None:
    if not isinstance(data, bytes):
        raise RgbaAccelerationError("RGBA buffers must be immutable bytes.")


def _blend_pixel(
    target: bytearray,
    target_index: int,
    source: bytes,
    source_index: int,
) -> None:
    source_alpha = source[source_index + 3]
    if source_alpha == 0:
        return
    inverse = ALPHA_MAX - source_alpha
    target_alpha = target[target_index + 3]
    for channel in range(3):
        target[target_index + channel] = (
            source[source_index + channel] * source_alpha
            + target[target_index + channel] * inverse
        ) // ALPHA_MAX
    target[target_index + 3] = min(
        ALPHA_MAX,
        source_alpha + (target_alpha * inverse) // ALPHA_MAX,
    )


def _error_summary(error: Exception) -> str:
    message = str(error).strip()
    return type(error).__name__ if not message else f"{type(error).__name__}: {message}"
