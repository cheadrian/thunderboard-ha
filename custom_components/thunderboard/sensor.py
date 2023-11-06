"""Support for Thunderboard sensors."""
from __future__ import annotations
import logging

from .thunderboard_ble import (
    ThunderboardSensor, 
    ThunderboardBinarySensor, 
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
    UV_INDEX,
    LIGHT_LUX,
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    EntityCategory,
    UnitOfPressure,
    UnitOfSoundPressure,
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

from .const import DOMAIN, MAGNETIC_STRENGTH_UNIT

SENSOR_DESCRIPTIONS: dict[str, SensorEntityDescription] = {
    ThunderboardSensor.SIGNAL_STRENGTH: SensorEntityDescription(
        key=ThunderboardSensor.SIGNAL_STRENGTH,
        translation_key=None,
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    ThunderboardSensor.BATTERY_PERCENT: SensorEntityDescription(
        key=ThunderboardSensor.BATTERY_PERCENT,
        translation_key=None,
        device_class=SensorDeviceClass.BATTERY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    ThunderboardBinarySensor.POWER_SOURCE: SensorEntityDescription(
        key=ThunderboardBinarySensor.POWER_SOURCE,
        translation_key=str(ThunderboardBinarySensor.POWER_SOURCE),
        device_class=None,
        native_unit_of_measurement=None,
        state_class=None,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    ThunderboardSensor.TEMPERATURE_C: SensorEntityDescription(
        key=ThunderboardSensor.TEMPERATURE_C,
        translation_key=None,
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    ThunderboardSensor.HUMIDITY_PERCENT: SensorEntityDescription(
        key=ThunderboardSensor.HUMIDITY_PERCENT,
        translation_key=None,
        device_class=SensorDeviceClass.HUMIDITY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    ThunderboardSensor.PRESSURE_PA: SensorEntityDescription(
        key=ThunderboardSensor.PRESSURE_PA,
        translation_key=None,
        device_class=SensorDeviceClass.ATMOSPHERIC_PRESSURE,
        native_unit_of_measurement=UnitOfPressure.PA,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    ThunderboardSensor.UV_IDX: SensorEntityDescription(
        key=ThunderboardSensor.UV_IDX,
        translation_key=str(ThunderboardSensor.UV_IDX),
        device_class=None,
        native_unit_of_measurement=UV_INDEX,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    ThunderboardSensor.SOUND_LEVEL_DBA: SensorEntityDescription(
        key=ThunderboardSensor.SOUND_LEVEL_DBA,
        translation_key=None,
        device_class=SensorDeviceClass.SOUND_PRESSURE,
        native_unit_of_measurement=UnitOfSoundPressure.WEIGHTED_DECIBEL_A,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    ThunderboardSensor.AMBIENT_LIGHT_LX: SensorEntityDescription(
        key=ThunderboardSensor.AMBIENT_LIGHT_LX,
        translation_key=None,
        device_class=SensorDeviceClass.ILLUMINANCE,
        native_unit_of_measurement=LIGHT_LUX,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    ThunderboardSensor.HALL_FIELD_UT: SensorEntityDescription(
        key=ThunderboardSensor.HALL_FIELD_UT,
        translation_key=str(ThunderboardSensor.HALL_FIELD_UT),
        device_class=None,
        native_unit_of_measurement=MAGNETIC_STRENGTH_UNIT,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
}

DIGITALS_DESCRIPTIONS: dict[str, SensorEntityDescription] = {
    ThunderboardBinarySensor.BTN_0: SensorEntityDescription(
        key=ThunderboardBinarySensor.BTN_0,
        translation_key=str(ThunderboardBinarySensor.BTN_0),
        device_class=None,
        native_unit_of_measurement=None,
        state_class=None,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    ThunderboardBinarySensor.BTN_1: SensorEntityDescription(
        key=ThunderboardBinarySensor.BTN_1,
        translation_key=str(ThunderboardBinarySensor.BTN_1),
        device_class=None,
        native_unit_of_measurement=None,
        state_class=None,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    ThunderboardBinarySensor.DIGITAL_STATE_0: SensorEntityDescription(
        key=ThunderboardBinarySensor.DIGITAL_STATE_0,
        translation_key=str(ThunderboardBinarySensor.DIGITAL_STATE_0),
        device_class=None,
        native_unit_of_measurement=None,
        state_class=None,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    ThunderboardBinarySensor.DIGITAL_STATE_1: SensorEntityDescription(
        key=ThunderboardBinarySensor.DIGITAL_STATE_1,
        translation_key=str(ThunderboardBinarySensor.DIGITAL_STATE_1),
        device_class=None,
        native_unit_of_measurement=None,
        state_class=None,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
}

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Thunderboard BLE sensors."""
    coordinator: DataUpdateCoordinator[ThunderboardDevice] = hass.data[DOMAIN][entry.entry_id]

    entities = []
    _LOGGER.debug("Got sensors: %s", coordinator.data)
    for sensor_type in coordinator.data.sensors.keys():
        entities.append(
            ThunderboardSensorEntity(coordinator, coordinator.data, SENSOR_DESCRIPTIONS[sensor_type])
        )

    for sensor_type in coordinator.data.digitals.keys():
        entities.append(
            ThunderboardSensorEntity(coordinator, coordinator.data, DIGITALS_DESCRIPTIONS[sensor_type])
        )

    # Append signal strenght RSSI
    entities.append(
        ThunderboardSensorEntity(coordinator, coordinator.data, SENSOR_DESCRIPTIONS[ThunderboardSensor.SIGNAL_STRENGTH])
    )

    async_add_entities(entities)

class ThunderboardSensorEntity(
    CoordinatorEntity[DataUpdateCoordinator[ThunderboardDevice]], SensorEntity
):
    """Thunderboard BLE sensors for the device."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: DataUpdateCoordinator[ThunderboardDevice],
        thunderboard_device: ThunderboardDevice,
        entity_description: SensorEntityDescription,
    ) -> None:
        """Populate the Thunderboard entity with relevant data."""
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
    def translation_key(self):
        """Return the translation key to translate the entity's name and states."""
        return self.entity_description.translation_key

    @property
    def available(self) -> bool:
        """Check if device and sensor is available in data."""
        return (
            super().available
            and (
                self.entity_description.key in self.coordinator.data.sensors or
                self.entity_description.key is ThunderboardSensor.SIGNAL_STRENGTH or
                self.entity_description.key in self.coordinator.data.digitals
            )
        )

    @property
    def native_value(self) -> StateType:
        """Return the value reported by the sensor."""
        if self.entity_description.key == ThunderboardSensor.SIGNAL_STRENGTH:
            return self.coordinator.data.rssi
        if self.entity_description.key in self.coordinator.data.digitals:
            return self.coordinator.data.digitals[self.entity_description.key]
        return self.coordinator.data.sensors[self.entity_description.key]