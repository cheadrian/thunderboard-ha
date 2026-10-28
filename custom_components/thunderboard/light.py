"""
Thunderboard lights integration.

The four RGB LEDs share their red, green and blue lines (UG309 3.4.8), so the lit LEDs always
show one common colour. Each LED can still be switched on and off on its own, which is what
the lights "RGB LED 0" to "RGB LED 3" do. Changing the colour of one of them changes the
colour of every lit LED, and the all-LEDs light switches the four of them together.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_RGB_COLOR,
    ColorMode,
    LightEntity,
    LightEntityDescription,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import ThunderboardConfigEntry, ThunderboardCoordinator
from .entity import ThunderboardEntity
from .thunderboard_ble import (
    ThunderboardLights,
    normalize_rgb,
    rgb_led_bit,
    rgb_led_key,
)
from .thunderboard_ble.const import RGB_LED_COUNT, RGB_LED_MASK_ALL

LIGHT_DESCRIPTION = LightEntityDescription(key=ThunderboardLights.RGB_LEDS_1)

RGB_LED_DESCRIPTIONS: tuple[LightEntityDescription, ...] = tuple(
    LightEntityDescription(
        key=rgb_led_key(index),
        translation_key="rgb_led",
        translation_placeholders={"index": str(index)},
    )
    for index in range(RGB_LED_COUNT)
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ThunderboardConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the Thunderboard BLE lights control."""
    coordinator = entry.runtime_data
    if coordinator.data.lights is not None:
        async_add_entities(
            [
                ThunderboardLightEntity(coordinator),
                *(
                    ThunderboardRgbLedEntity(coordinator, index)
                    for index in range(RGB_LED_COUNT)
                ),
            ]
        )


class ThunderboardLightBase(ThunderboardEntity, LightEntity):
    """What the all-LEDs light and the light of one LED have in common: the colour."""

    _attr_supported_color_modes = {ColorMode.RGB}
    _attr_color_mode = ColorMode.RGB

    @property
    def available(self) -> bool:
        """The firmware turns the LEDs off when the connection is closed."""
        return (
            super().available
            and self.coordinator.keep_connect
            and self.coordinator.data.lights is not None
        )

    @property
    def brightness(self) -> int | None:
        """Return the brightness of the lit LEDs."""
        lights = self.coordinator.data.lights
        return None if lights is None else lights.brightness

    @property
    def rgb_color(self) -> tuple[int, int, int] | None:
        """Return the colour of the lit LEDs, at full brightness."""
        lights = self.coordinator.data.lights
        return None if lights is None else lights.rgb

    def _requested_colour(
        self, kwargs: Mapping[str, Any]
    ) -> tuple[tuple[int, int, int] | None, int | None]:
        """The colour and brightness of a turn on call, None for what stays as it is."""
        rgb = None
        if ATTR_RGB_COLOR in kwargs:
            lights = self.coordinator.data.lights
            fallback = (255, 255, 255) if lights is None else lights.rgb
            rgb = normalize_rgb(kwargs[ATTR_RGB_COLOR], fallback=fallback)
        return rgb, kwargs.get(ATTR_BRIGHTNESS)


class ThunderboardLightEntity(ThunderboardLightBase):
    """The four RGB LEDs of the board together."""

    _attr_name = None

    def __init__(self, coordinator: ThunderboardCoordinator) -> None:
        """Initialize the all-LEDs light."""
        super().__init__(coordinator, LIGHT_DESCRIPTION.key)
        self.entity_description = LIGHT_DESCRIPTION

    @property
    def is_on(self) -> bool | None:
        """Return true if any of the LEDs is on."""
        lights = self.coordinator.data.lights
        return None if lights is None else lights.is_on

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Instruct the light to turn all the LEDs on."""
        rgb, brightness = self._requested_colour(kwargs)
        await self.coordinator.async_update_lights(
            on=RGB_LED_MASK_ALL, rgb=rgb, brightness=brightness
        )

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Instruct the light to turn all the LEDs off."""
        await self.coordinator.async_update_lights(off=RGB_LED_MASK_ALL)


class ThunderboardRgbLedEntity(ThunderboardLightBase):
    """One of the four RGB LEDs, numbered as in the user guide of the board."""

    def __init__(self, coordinator: ThunderboardCoordinator, index: int) -> None:
        """Initialize the light of one RGB LED."""
        description = RGB_LED_DESCRIPTIONS[index]
        super().__init__(coordinator, description.key)
        self.entity_description = description
        self._bit = rgb_led_bit(index)

    @property
    def is_on(self) -> bool | None:
        """Return true if this LED is on."""
        lights = self.coordinator.data.lights
        return None if lights is None else bool(lights.mask & self._bit)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Instruct the light to turn this LED on, the colour is shared with the other LEDs."""
        rgb, brightness = self._requested_colour(kwargs)
        await self.coordinator.async_update_lights(
            on=self._bit, rgb=rgb, brightness=brightness
        )

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Instruct the light to turn this LED off."""
        await self.coordinator.async_update_lights(off=self._bit)
