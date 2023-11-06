"""
RGB lights controller for Thunderboard Sense 2 BLE advertisements.
"""
from __future__ import annotations

import logging
import struct
from typing import Tuple
from .models import ThunderboardLightsState
from bleak import BleakClient, BLEDevice
from bleak_retry_connector import establish_connection
from sensor_state_data.enum import StrEnum
import colorsys

_LOGGER = logging.getLogger(__name__)

from .const import CHARACTERISTIC_RGB_LEDS_1

class ThunderboardLights(StrEnum):
    RGB_LEDS_1          = "rgb_leds_1"

# Starting from right of USB port, led 1, top led 2, right of battery holder led 3, top led 4
THUNDERBOARD_GATT_LIGHTS_CHARS = [
    {
        "uuid": CHARACTERISTIC_RGB_LEDS_1,
        "light_key": ThunderboardLights.RGB_LEDS_1,
        "format": 'BBBB',
        "modes": {
            0: [],
            1: [1],
            2: [2],
            3: [1, 2],
            4: [4],
            5: [1, 4],
            6: [2, 4],
            7: [1, 2, 4],
            8: [3],
            9: [1, 3],
            10: [2, 3],
            11: [1, 2, 3],
            12: [3, 4],
            13: [1, 3, 4],
            14: [2, 3, 4],
            15: [1, 2, 3, 4],
        }
    }
]

class ThunderboardLightsController:
    def __init__(
        self,
        logger: logging.Logger,
        client: BleakClient,
    ):
        super().__init__()
        self.logger = logger
        self.client = client
        self._state = ThunderboardLightsState()
        
    @classmethod
    async def from_ble_device(cls, logger: logging.Logger, ble_device: BLEDevice):
        client = await establish_connection(BleakClient, ble_device, ble_device.address)
        return cls(logger, client)

    def get_mode(self, leds_to_turn_on: set[int]) -> int:
        modes = THUNDERBOARD_GATT_LIGHTS_CHARS[0]["modes"]
        for mode_val, leds in modes.items():
            if set(leds_to_turn_on).issubset(set(leds)):
                mode = mode_val
                return mode

    def _parse_ble_leds_state(self, data) -> ThunderboardLightsState:
        if len(data) != 4:
            return None

        mask, r, g, b = struct.unpack('BBBB', data)
        h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
        self._state.rgb = (r, g, b)
        self._state.mode = mask
        self._state.brightness = int(v * 255)
        return self._state

    async def get_rgb_leds_state(self) -> ThunderboardLightsState:            
        c = THUNDERBOARD_GATT_LIGHTS_CHARS[0]
        payload = await self.client.read_gatt_char(c["uuid"])
        state = self._parse_ble_leds_state(payload)
        self._state = state
        self.logger.debug("Successfully read lights GATT characteristics, controller")
        return state
    
    def _get_rgb_with_brightness(self, rgb, brightness) -> Tuple[int, int, int]:
        r, g, b = rgb
        h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
        v *= brightness / 255
        r, g, b = colorsys.hsv_to_rgb(h, s, v)
        return int(r * 255), int(g * 255), int(b * 255)

    async def _set_rgb_leds_state(self, state: ThunderboardLightsState) -> ThunderboardLightsState:
        c = THUNDERBOARD_GATT_LIGHTS_CHARS[0]
        r, g, b = self._get_rgb_with_brightness(state.rgb, state.brightness)
        payload = struct.pack(c["format"], state.mode, r, g, b)
        try:
            await self.client.write_gatt_char(c["uuid"], payload)
            self._state = state
            return state
        except Exception as e:
            self.logger.error(e)
    
    async def turn_all_on(self, rgb=(255,255,255), brightness=255)-> ThunderboardLightsState:
        mode = self.get_mode({1, 2, 3, 4})
        self._state.mode = mode
        self._state.rgb = rgb
        self._state.brightness = brightness
        self.logger.debug("Send RGB all ON state to device: %s", self._state)
        return await self._set_rgb_leds_state(self._state)

    async def turn_all_off(self)-> ThunderboardLightsState:
        mode = self.get_mode({})
        self._state.mode = mode
        self.logger.debug("Send RGB all OFF state to device: %s", self._state)
        return await self._set_rgb_leds_state(self._state)