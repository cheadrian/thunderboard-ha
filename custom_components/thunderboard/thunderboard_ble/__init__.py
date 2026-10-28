"""
Parser and connection manager for Thunderboard Sense 2 BLE devices.
"""
from __future__ import annotations

from .lights import (
    ThunderboardLights,
    decode_rgb_leds,
    encode_rgb_leds,
    normalize_rgb,
    rgb_led_bit,
    rgb_led_key,
)
from .models import (
    ThunderboardConnectionStats,
    ThunderboardDevice,
    ThunderboardLightsState,
)
from .parser import (
    POWER_SOURCE_OPTIONS,
    ThunderboardBinarySensor,
    ThunderboardBluetoothDeviceData,
    ThunderboardDeviceInfo,
    ThunderboardError,
    ThunderboardSensor,
)

__version__ = "0.3.0"

__all__ = [
    "POWER_SOURCE_OPTIONS",
    "ThunderboardBinarySensor",
    "ThunderboardBluetoothDeviceData",
    "ThunderboardConnectionStats",
    "ThunderboardDevice",
    "ThunderboardDeviceInfo",
    "ThunderboardError",
    "ThunderboardLights",
    "ThunderboardLightsState",
    "ThunderboardSensor",
    "decode_rgb_leds",
    "encode_rgb_leds",
    "normalize_rgb",
    "rgb_led_bit",
    "rgb_led_key",
]
