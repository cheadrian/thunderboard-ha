"""Support for Thunderboard sensors."""
from __future__ import annotations
import logging

from .thunderboard_ble import (
    ThunderboardSensor, 
    ThunderboardDevice
)

_LOGGER = logging.getLogger(__name__)

from homeassistant.config_entries import ConfigEntry

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)

from homeassistant.const import (
    PERCENTAGE,
    EntityCategory,
    UnitOfTemperature,
)

from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import (
    CONNECTION_BLUETOOTH,
    DeviceInfo,
)

from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from .const import DOMAIN

""" Describes what type of data the sensors have. """
SENSOR_DESCRIPTIONS: dict[str, SensorEntityDescription] = {
    ThunderboardSensor.TEMPERATURE_C: SensorEntityDescription(
        key=ThunderboardSensor.TEMPERATURE_C,
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    ThunderboardSensor.HUMIDITY_PERCENT: SensorEntityDescription(
        key=ThunderboardSensor.HUMIDITY_PERCENT,
        device_class=SensorDeviceClass.HUMIDITY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    )
}

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """ Set up the Thunderboard BLE sensors. """
    coordinator: DataUpdateCoordinator[ThunderboardDevice] = hass.data[DOMAIN][entry.entry_id]

    entities = []
    _LOGGER.debug("Got sensors: %s", coordinator.data)
    """ Add sensors entities to the coordinator. """
    for sensor_type in coordinator.data.sensors.keys():
        entities.append(
            ThunderboardSensorEntity(coordinator, coordinator.data, SENSOR_DESCRIPTIONS[sensor_type])
        )

    async_add_entities(entities)

class ThunderboardSensorEntity(
    CoordinatorEntity[DataUpdateCoordinator[ThunderboardDevice]], SensorEntity
):
    """ Thunderboard BLE sensors for the device. """
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: DataUpdateCoordinator[ThunderboardDevice],
        thunderboard_device: ThunderboardDevice,
        entity_description: SensorEntityDescription,
    ) -> None:
        """ Populate the Thunderboard entity with relevant device data. """
        super().__init__(coordinator)
        self.entity_description = entity_description

        name = thunderboard_device.name
        if identifier := thunderboard_device.identifier:
            name += f" ({identifier})"

        self._attr_unique_id = f"{thunderboard_device.address}_{entity_description.key}"
        self._attr_device_info = DeviceInfo(
            connections={
                (
                    CONNECTION_BLUETOOTH,
                    thunderboard_device.address,
                )
            },
            name=name,
            manufacturer=thunderboard_device.manufacturer,
            hw_version=thunderboard_device.hw_version,
            sw_version=thunderboard_device.sw_version,
            model=thunderboard_device.model,
        )

    @property
    def available(self) -> bool:
        """ Check if device and sensor is available in data. """
        return (
            super().available
            and (
                self.entity_description.key in self.coordinator.data.sensors
            )
        )

    @property
    def native_value(self) -> StateType:
        """ Return the value reported by the sensor. """
        return self.coordinator.data.sensors[self.entity_description.key]