"""Support for Thunderboard sensors."""
from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    LIGHT_LUX,
    PERCENTAGE,
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    UV_INDEX,
    EntityCategory,
    UnitOfPressure,
    UnitOfRatio,
    UnitOfSoundPressure,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.typing import StateType

from .const import MAGNETIC_STRENGTH_UNIT
from .coordinator import ThunderboardConfigEntry, ThunderboardCoordinator
from .entity import ThunderboardEntity
from .thunderboard_ble import POWER_SOURCE_OPTIONS, ThunderboardSensor

SENSOR_DESCRIPTIONS: tuple[SensorEntityDescription, ...] = (
    SensorEntityDescription(
        key=ThunderboardSensor.TEMPERATURE_C,
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
    ),
    SensorEntityDescription(
        key=ThunderboardSensor.HUMIDITY_PERCENT,
        device_class=SensorDeviceClass.HUMIDITY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
    ),
    SensorEntityDescription(
        key=ThunderboardSensor.PRESSURE_PA,
        device_class=SensorDeviceClass.ATMOSPHERIC_PRESSURE,
        native_unit_of_measurement=UnitOfPressure.PA,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
    ),
    SensorEntityDescription(
        key=ThunderboardSensor.AMBIENT_LIGHT_LX,
        device_class=SensorDeviceClass.ILLUMINANCE,
        native_unit_of_measurement=LIGHT_LUX,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
    ),
    SensorEntityDescription(
        key=ThunderboardSensor.UV_IDX,
        translation_key=ThunderboardSensor.UV_IDX,
        native_unit_of_measurement=UV_INDEX,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key=ThunderboardSensor.SOUND_LEVEL_DB,
        device_class=SensorDeviceClass.SOUND_PRESSURE,
        native_unit_of_measurement=UnitOfSoundPressure.DECIBEL,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
    ),
    SensorEntityDescription(
        key=ThunderboardSensor.HALL_FIELD_UT,
        translation_key=ThunderboardSensor.HALL_FIELD_UT,
        native_unit_of_measurement=MAGNETIC_STRENGTH_UNIT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key=ThunderboardSensor.ECO2_PPM,
        translation_key=ThunderboardSensor.ECO2_PPM,
        device_class=SensorDeviceClass.CO2,
        native_unit_of_measurement=UnitOfRatio.PARTS_PER_MILLION,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key=ThunderboardSensor.TVOC_PPB,
        translation_key=ThunderboardSensor.TVOC_PPB,
        device_class=SensorDeviceClass.VOLATILE_ORGANIC_COMPOUNDS_PARTS,
        native_unit_of_measurement=UnitOfRatio.PARTS_PER_BILLION,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key=ThunderboardSensor.BATTERY_PERCENT,
        device_class=SensorDeviceClass.BATTERY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SensorEntityDescription(
        key=ThunderboardSensor.POWER_SOURCE,
        translation_key=ThunderboardSensor.POWER_SOURCE,
        device_class=SensorDeviceClass.ENUM,
        options=POWER_SOURCE_OPTIONS,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
)

# Not read from the board, it is the signal strength of its last advertisement
SIGNAL_STRENGTH_DESCRIPTION = SensorEntityDescription(
    key=ThunderboardSensor.SIGNAL_STRENGTH,
    device_class=SensorDeviceClass.SIGNAL_STRENGTH,
    native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    state_class=SensorStateClass.MEASUREMENT,
    entity_category=EntityCategory.DIAGNOSTIC,
    entity_registry_enabled_default=False,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ThunderboardConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the Thunderboard BLE sensors."""
    coordinator = entry.runtime_data
    found = coordinator.data.sensors
    async_add_entities(
        [
            ThunderboardSensorEntity(coordinator, description)
            for description in SENSOR_DESCRIPTIONS
            if description.key in found
        ]
        + [ThunderboardSensorEntity(coordinator, SIGNAL_STRENGTH_DESCRIPTION)]
    )


class ThunderboardSensorEntity(ThunderboardEntity, SensorEntity):
    """Thunderboard BLE sensors for the device."""

    def __init__(
        self,
        coordinator: ThunderboardCoordinator,
        entity_description: SensorEntityDescription,
    ) -> None:
        """Populate the Thunderboard entity with relevant data."""
        super().__init__(coordinator, entity_description.key)
        self.entity_description = entity_description

    @property
    def native_value(self) -> StateType:
        """Return the value reported by the sensor."""
        if self.entity_description.key == ThunderboardSensor.SIGNAL_STRENGTH:
            return self.coordinator.data.rssi
        return self.coordinator.data.sensors.get(self.entity_description.key)
