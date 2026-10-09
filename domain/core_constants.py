"""Character-neutral protocol, media, audio, time, and numeric constants."""

from __future__ import annotations

lazy from typing import Final

HTTP_MIN_STATUS: Final = 100
HTTP_MAX_STATUS: Final = 599
HTTP_CLIENT_ERROR_BOUNDARY: Final = 400
HTTP_SERVER_ERROR_BOUNDARY: Final = 500
HTTP_SERVER_ERROR_MAX: Final = 600

HTTP_OK: Final = 200
HTTP_UNAUTHORIZED: Final = 401
HTTP_FORBIDDEN: Final = 403
HTTP_NOT_FOUND: Final = 404
HTTP_TOO_MANY_REQUESTS: Final = 429
HTTP_BAD_GATEWAY: Final = 502
HTTP_SERVICE_UNAVAILABLE: Final = 503
HTTP_GATEWAY_TIMEOUT: Final = 504

SHA256_HEX_LENGTH: Final = 64
SHA256_RAW_LENGTH: Final = 32

PNG_SIGNATURE: Final = b"\x89PNG\r\n\x1a\n"
PNG_BIT_DEPTH: Final = 8
PNG_COLOR_TYPE_RGBA: Final = 6
PNG_MIN_HEADER_LENGTH: Final = 33

BYTES_PER_PIXEL: Final = 4
RGB_CHANNELS: Final = 3
BYTE_MAX: Final = 255
RGB_MAX: Final = 255
SYMLINK_FILE_TYPE: Final = 0o120000

PCM16_MIN_SAMPLE: Final = -32_768
PCM16_MAX_SAMPLE: Final = 32_767
PCM16_SAMPLE_WIDTH: Final = 2

SECONDS_PER_MINUTE: Final = 60
MINUTES_PER_HOUR: Final = 60
SECONDS_PER_HOUR: Final = 3_600
HOURS_PER_DAY: Final = 24
SECONDS_PER_DAY: Final = 86_400

FLOAT_COMPARISON_EPSILON: Final = 1e-9

DEFAULT_TEXT_MODEL: Final = "gpt-5.6-luna"
DEFAULT_TRANSCRIPTION_MODEL: Final = "gpt-4o-mini-transcribe"

# Character-neutral observation fallbacks used before any weather source has
# supplied a reading. Product shells may persist different observed values.
DEFAULT_WEATHER_TEMPERATURE_C: Final = 24.0
DEFAULT_WEATHER_CONDITION: Final = "indoor"
