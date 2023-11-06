"""
Thunderboard lights integration.
Please note, this is experimental!
"""
from __future__ import annotations
import logging

from typing import Any

from .thunderboard_ble import (
    ThunderboardLights, 
    ThunderboardDevice, 
    ThunderboardLightsController
)

_LOGGER = logging.getLogger(__name__)

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_RGB_COLOR,
    ColorMode,
    LightEntity,
    LightEntityFeature,
    LightEntityDescription,
)

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.components.bluetooth import async_ble_device_from_address
from homeassistant.helpers.device_registry import (
    CONNECTION_BLUETOOTH,
    DeviceInfo,
)
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from bleak import BLEDevice

from .const import (
    DOMAIN, 
    KEEP_DEVICE_CONNECTED_KEY,
    KEEP_DEVICE_CONNECTED
)

LIGHTS_DESCRIPTIONS: dict[str, LightEntityDescription] = {
    ThunderboardLights.RGB_LEDS_1: LightEntityDescription(
        key=ThunderboardLights.RGB_LEDS_1,
        translation_key=None,
    ),
}

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Thunderboard BLE lights control."""
    address = entry.unique_id
    assert address is not None
    ble_device = async_ble_device_from_address(hass, address)
    keep_connect = entry.options.get(KEEP_DEVICE_CONNECTED_KEY, KEEP_DEVICE_CONNECTED)
    coordinator: DataUpdateCoordinator[ThunderboardDevice] = hass.data[DOMAIN][entry.entry_id]    
    entities = []
    _LOGGER.debug("Got led lights: %s", coordinator.data)

    entities.append(
        ThunderboardLightEntity(coordinator, coordinator.data, ble_device, keep_connect, LIGHTS_DESCRIPTIONS[ThunderboardLights.RGB_LEDS_1])
    )

    async_add_entities(entities)

class ThunderboardLightEntity(
    CoordinatorEntity[DataUpdateCoordinator[ThunderboardDevice]], LightEntity
    ):
    """Thunderboard BLE lights for the device."""

    _attr_supported_color_modes = {ColorMode.RGB, ColorMode.BRIGHTNESS}
    _attr_color_mode = ColorMode.RGB
    _attr_has_entity_name = True
    _attr_name = None
    _attr_supported_features = LightEntityFeature.EFFECT
    _attr_effect = None

    def __init__(
        self, 
        coordinator: DataUpdateCoordinator[ThunderboardDevice],
        thunderboard_device: ThunderboardDevice,
        ble_device: BLEDevice,
        keep_connect: bool,
        entity_description: LightEntityDescription
    ) -> None:
        """Initialize an Thunderboard lights."""
        super().__init__(coordinator)
        self.entity_description = entity_description
        self.ble_device = ble_device
        self.controller = None
        self.keep_connect = keep_connect
        self.required_rgb = (255, 255, 255)
        self.required_brightness = 255
        
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
        self._async_update_attrs()

    @callback
    def _async_update_attrs(self) -> None:
        """Handle updating _attr values."""
        # device = self._device
        self._attr_rgb_color = self.coordinator.data.lights.rgb
        self._attr_brightness = self.coordinator.data.lights.brightness
        self._attr_is_on = self.coordinator.data.lights.power
        _LOGGER.debug("RGB attr: %s, is on attr: %s", self._attr_rgb_color, self._attr_is_on)

    async def _get_controller(self):
        if self.controller is None:
            self.controller = await ThunderboardLightsController.from_ble_device(_LOGGER, self.ble_device)
        return self.controller
    
    def _update_coordinator_lights_state(self, state):
        data = self.coordinator.data
        data.lights = state
        self.coordinator.async_set_updated_data(data)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Instruct the light to turn on."""
        try:
            light_controller = await self._get_controller()
            self.required_rgb = kwargs.get(ATTR_RGB_COLOR, self.required_rgb)
            self.required_brightness = kwargs.get(ATTR_BRIGHTNESS, self.required_brightness)
            state = await light_controller.turn_all_on(rgb=self.required_rgb, brightness=self.required_brightness)
            self._update_coordinator_lights_state(state)
        except Exception as e:
            _LOGGER.error(e)
        
    async def async_turn_off(self, **kwargs: Any) -> None:
        """Instruct the light to turn off."""
        try:
            light_controller = await self._get_controller()
            state = await light_controller.turn_all_off()
            self._update_coordinator_lights_state(state)
        except Exception as e:
            _LOGGER.error(e)

    @callback
    def _handle_coordinator_update(self, *args: Any) -> None:
        """Handle data update."""
        self._async_update_attrs()
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        return await super().async_added_to_hass()

    @property
    def available(self) -> bool:
        """Check if device and sensor is available in data."""
        return (
            super().available
            and self.keep_connect
        )