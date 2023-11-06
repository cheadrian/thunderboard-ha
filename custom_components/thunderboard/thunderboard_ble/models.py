from __future__ import annotations

import dataclasses
from typing import Optional


@dataclasses.dataclass
class ThunderboardDevice:
    """Response data with information about the Thunderboard device"""

    manufacturer: str = ""
    hw_version: str = ""
    sw_version: str = ""
    model: Optional[str] = None
    name: str = ""
    identifier: str = ""
    address: str = ""
    lights: ThunderboardLightsState = None
    sensors: dict[str, str | float | None] = dataclasses.field(
        default_factory=lambda: {}
    )
    digitals: dict[str, int | bool | list[int] | None] = dataclasses.field(
        default_factory=lambda: {}
    )
    rssi: int = None

    def friendly_name(self) -> str:
        """Generate a name for the device."""

        return f"Thunderboard {self.model}"

@dataclasses.dataclass
class ThunderboardLightsState:
    rgb: tuple[int, int, int] = (0, 0, 0)
    preset_pattern: int = 0
    mode: int = 0
    speed: int = 0
    brightness: int = 255

    @property
    def power(self) -> bool:
        return bool(self.mode & 1)