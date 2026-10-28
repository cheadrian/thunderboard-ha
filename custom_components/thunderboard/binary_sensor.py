"""Support for the buttons, the LED state and the connection of the Thunderboard."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import ThunderboardConfigEntry, ThunderboardCoordinator
from .entity import ThunderboardEntity
from .thunderboard_ble import ThunderboardBinarySensor

CONNECTION_DESCRIPTION = BinarySensorEntityDescription(
    key="connection",
    translation_key="connection",
    device_class=BinarySensorDeviceClass.CONNECTIVITY,
    entity_category=EntityCategory.DIAGNOSTIC,
)

BINARY_SENSOR_DESCRIPTIONS: tuple[BinarySensorEntityDescription, ...] = (
    BinarySensorEntityDescription(
        key=ThunderboardBinarySensor.BTN_0,
        translation_key=ThunderboardBinarySensor.BTN_0,
    ),
    BinarySensorEntityDescription(
        key=ThunderboardBinarySensor.BTN_1,
        translation_key=ThunderboardBinarySensor.BTN_1,
    ),
    # The two LEDs next to the buttons, the firmware turns them off while connected
    BinarySensorEntityDescription(
        key=ThunderboardBinarySensor.LED_0,
        translation_key=ThunderboardBinarySensor.LED_0,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    BinarySensorEntityDescription(
        key=ThunderboardBinarySensor.LED_1,
        translation_key=ThunderboardBinarySensor.LED_1,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ThunderboardConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the Thunderboard BLE binary sensors."""
    coordinator = entry.runtime_data
    found = coordinator.data.digitals
    async_add_entities(
        [
            ThunderboardConnectionEntity(coordinator),
            *(
                ThunderboardBinarySensorEntity(coordinator, description)
                for description in BINARY_SENSOR_DESCRIPTIONS
                if description.key in found
            ),
        ]
    )


class ThunderboardBinarySensorEntity(ThunderboardEntity, BinarySensorEntity):
    """Thunderboard BLE binary sensors for the device."""

    def __init__(
        self,
        coordinator: ThunderboardCoordinator,
        entity_description: BinarySensorEntityDescription,
    ) -> None:
        """Populate the Thunderboard entity with relevant data."""
        super().__init__(coordinator, entity_description.key)
        self.entity_description = entity_description

    @property
    def is_on(self) -> bool | None:
        """Return true if the button is pressed or the LED is on."""
        return self.coordinator.data.digitals.get(self.entity_description.key)


class ThunderboardConnectionEntity(ThunderboardEntity, BinarySensorEntity):
    """Whether Home Assistant holds the connection of the board, and how it went so far.

    The board advertises, and blinks its small LED, only while nothing is connected to it.
    """

    entity_description = CONNECTION_DESCRIPTION

    def __init__(self, coordinator: ThunderboardCoordinator) -> None:
        """Initialize the connection sensor."""
        super().__init__(coordinator, CONNECTION_DESCRIPTION.key)

    @property
    def available(self) -> bool:
        """Being disconnected is a state of this sensor, not a reason to be unavailable."""
        return True

    @property
    def is_on(self) -> bool:
        """Return true while the board is connected."""
        return self.coordinator.device_data.is_connected

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return how many times the board connected and dropped the connection."""
        stats = self.coordinator.device_data.stats
        return {
            "connections": stats.connections,
            "unexpected_disconnects": stats.unexpected_disconnects,
            "last_connected": _isoformat(stats.last_connected),
            "last_disconnected": _isoformat(stats.last_disconnected),
            "last_error": stats.last_error,
            "last_error_at": _isoformat(stats.last_error_at),
        }


def _isoformat(moment: datetime | None) -> str | None:
    return None if moment is None else moment.isoformat()
