from __future__ import annotations

import dataclasses
from typing import Optional


@dataclasses.dataclass
class ThunderboardDevice:
    """ Response data with information about the Thunderboard device. """

    manufacturer: str = ""
    hw_version: str = ""
    sw_version: str = ""
    model: Optional[str] = None
    name: str = ""
    identifier: str = ""
    address: str = ""
    sensors: dict[str, str | float | None] = dataclasses.field(
        default_factory=lambda: {}
    )
    
    def friendly_name(self) -> str:
        """Generate a name for the device."""

        return f"Thunderboard {self.model}"
