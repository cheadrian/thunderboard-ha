"""Base entity of the Thunderboard integration."""
from __future__ import annotations

from homeassistant.helpers.device_registry import CONNECTION_BLUETOOTH, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import ThunderboardCoordinator


class ThunderboardEntity(CoordinatorEntity[ThunderboardCoordinator]):
    """Entity of a Thunderboard, all the entities of a board share its device."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: ThunderboardCoordinator, key: str) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.address}_{key}"
        device = coordinator.data
        self._attr_device_info = DeviceInfo(
            connections={(CONNECTION_BLUETOOTH, coordinator.address)},
            name=coordinator.config_entry.title,
            manufacturer=device.manufacturer,
            model=device.model or "Thunderboard",
            hw_version=device.hw_version,
            sw_version=device.sw_version,
        )
