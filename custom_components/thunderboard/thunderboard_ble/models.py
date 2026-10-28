"""Data models of the Thunderboard BLE library."""
from __future__ import annotations

import dataclasses
from datetime import datetime

from .const import RGB_LED_MASK_ALL


@dataclasses.dataclass
class ThunderboardConnectionStats:
    """How the connection to the board went, to find out why it drops."""

    connections: int = 0
    unexpected_disconnects: int = 0
    last_connected: datetime | None = None
    last_disconnected: datetime | None = None
    last_error: str | None = None
    last_error_at: datetime | None = None


@dataclasses.dataclass
class ThunderboardLightsState:
    """State of the RGB LEDs, which all show the same colour.

    ``rgb`` is the colour scaled so that its brightest channel is 255 and ``brightness``
    (0-255) is the brightest channel of what the board shows, as Home Assistant expects.
    """

    mask: int = 0
    rgb: tuple[int, int, int] = (255, 255, 255)
    brightness: int = 255

    @property
    def is_on(self) -> bool:
        return bool(self.mask & RGB_LED_MASK_ALL)


@dataclasses.dataclass
class ThunderboardDevice:
    """Latest values read from a Thunderboard.

    Only the characteristics found on the board have a key in ``sensors`` and ``digitals``.
    A value of None means that the board did not report a valid value.
    """

    address: str = ""
    manufacturer: str | None = None
    model: str | None = None
    hw_version: str | None = None
    sw_version: str | None = None
    sensors: dict[str, float | int | str | None] = dataclasses.field(
        default_factory=dict
    )
    digitals: dict[str, bool | None] = dataclasses.field(default_factory=dict)
    lights: ThunderboardLightsState | None = None
    rssi: int | None = None
