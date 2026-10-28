"""
RGB LEDs of the Thunderboard Sense 2.
"""
from __future__ import annotations

from collections.abc import Sequence
from enum import StrEnum

from .const import RGB_LED_COUNT
from .models import ThunderboardLightsState


class ThunderboardLights(StrEnum):
    RGB_LEDS_1 = "rgb_leds_1"


def rgb_led_key(index: int) -> str:
    """Key of the light of RGB LED index, the numbering of the user guide (0-3)."""
    return f"rgb_led_{index}"


def rgb_led_bit(index: int) -> int:
    """Bit of RGB LED index in the LED mask."""
    if not 0 <= index < RGB_LED_COUNT:
        raise ValueError(f"The board has RGB LEDs 0 to {RGB_LED_COUNT - 1}, not {index}")
    return 1 << index


def _clamp(value: float) -> int:
    return max(0, min(255, round(value)))


def normalize_rgb(
    rgb: Sequence[int], fallback: tuple[int, int, int] = (255, 255, 255)
) -> tuple[int, int, int]:
    """Scale a colour so that its brightest channel is 255."""
    peak = max(rgb)
    if peak <= 0:
        return fallback
    r, g, b = (_clamp(channel * 255 / peak) for channel in rgb)
    return r, g, b


def encode_rgb_leds(mask: int, rgb: Sequence[int], brightness: int) -> bytes:
    """Build the LED mask, red, green and blue payload for a colour at a brightness (0-255)."""
    r, g, b = (_clamp(channel * brightness / 255) for channel in rgb)
    return bytes((mask & 0xFF, r, g, b))


def decode_rgb_leds(
    payload: bytes | bytearray, previous: ThunderboardLightsState | None = None
) -> ThunderboardLightsState | None:
    """Parse the payload of the RGB LEDs characteristic."""
    if len(payload) != 4:
        return None
    mask, r, g, b = payload
    brightness = max(r, g, b)
    if brightness == 0:
        # Black has no hue, keep the previous one so that the LEDs can be switched back on
        rgb = previous.rgb if previous is not None else (255, 255, 255)
    else:
        rgb = normalize_rgb((r, g, b))
    return ThunderboardLightsState(mask=mask, rgb=rgb, brightness=brightness)
