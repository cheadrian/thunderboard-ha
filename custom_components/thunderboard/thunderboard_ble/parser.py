"""
Parser for Thunderboard Sense 2 BLE advertisements.
# Parsing demo: https://community.silabs.com/s/share/a5U1M000000kntwUAA/thunderboard-sense-with-raspberry-pi-and-python
"""
from __future__ import annotations

import logging
import struct
import asyncio
from typing import Callable

from bleak import BleakError, BLEDevice, BleakClient
from contextlib import contextmanager
import bleak_retry_connector

from .lights import ThunderboardLightsController
from .models import ThunderboardDevice

from sensor_state_data import SensorDeviceClass, Units
from sensor_state_data.enum import StrEnum

_LOGGER = logging.getLogger(__name__)

from .const import (
    CHARACTERISTIC_BATTERY,
    CHARACTERISTIC_POWER_SOURCE,
    CHARACTERISTIC_TEMPERATURE,
    CHARACTERISTIC_HUMIDITY,
    CHARACTERISTIC_PRESSURE,
    CHARACTERISTIC_UV_IDX,
    CHARACTERISTIC_SOUND_LEVEL,
    CHARACTERISTIC_AMBIENT_LIGHT,
    CHARACTERISTIC_HALL_FIELD,
    CHARACTERISTIC_DEVICE_NAME,
    CHARACTERISTIC_MODEL_NUMBER,
    CHARACTERISTIC_HARDWARE_REV,
    CHARACTERISTIC_FIRMWARE_REV,
    CHARACTERISTIC_HANDLE_DIGITAL_STATE_0,
    CHARACTERISTIC_HANDLE_DIGITAL_STATE_1,
)

class ThunderboardSensor(StrEnum):
    TIME                = "time"
    SIGNAL_STRENGTH     = "signal_strength"
    # Power and battery
    BATTERY_PERCENT     = "battery"
    # Environmental sensors
    TEMPERATURE_C       = "temperature"
    HUMIDITY_PERCENT    = "humidity"
    PRESSURE_PA         = "pressure"
    UV_IDX              = "uv_idx"
    SOUND_LEVEL_DBA     = "sound_level"
    AMBIENT_LIGHT_LX    = "ambient_light"
    HALL_FIELD_UT       = "hall_field_strenght"
    
class ThunderboardBinarySensor(StrEnum):
    # Power
    POWER_SOURCE        = "power_source"
    # Buttons
    DIGITAL_STATE_0     = "digital_state_0"
    DIGITAL_STATE_1     = "digital_state_1"
    BTN_0               = "btn_0"
    BTN_1               = "btn_1"
    
class ThunderboardDeviceInfo(StrEnum):
    # Device information
    DEVICE_NAME         = "name"
    APPEARANCE          = "appearance"
    MANUFACTURER_NAME   = "manufacturer"
    MODEL_NUMBER        = "model"
    SERIAL_NUMBER       = "serial_number"
    HARDWARE_REV        = "hw_version"
    FIRMWARE_REV        = "sw_version"
    SYSTEM_ID           = "system_id"

THUNDERBOARD_MANUFACTURER = 0x0047

THUNDERBOARD_GATT_SENSOR_CHARS = [
    {
        "uuid": CHARACTERISTIC_BATTERY,
        "sensor_key": ThunderboardSensor.BATTERY_PERCENT,
        "format": '<B',
        "divider": None,
        "sensor_unit": Units.PERCENTAGE,
        "sensor_class": SensorDeviceClass.BATTERY,
        "sensor_name": "Battery"
    },
    {
        "uuid": CHARACTERISTIC_POWER_SOURCE,
        "sensor_key": ThunderboardBinarySensor.POWER_SOURCE,
        "format": '<B',
        "divider": None,
        "sensor_unit": None,
        "sensor_class": None,
        "sensor_name": "Power source"
    },
    {
        "uuid": CHARACTERISTIC_TEMPERATURE,
        "sensor_key": ThunderboardSensor.TEMPERATURE_C,
        "format": '<h',
        "divider": 100,
        "sensor_unit": Units.TEMP_CELSIUS,
        "sensor_class": SensorDeviceClass.TEMPERATURE,
        "sensor_name": "Temperature"
    },
    {
        "uuid": CHARACTERISTIC_HUMIDITY,
        "sensor_key": ThunderboardSensor.HUMIDITY_PERCENT,
        "format": '<H',
        "divider": 100,
        "sensor_unit": Units.PERCENTAGE,
        "sensor_class": SensorDeviceClass.HUMIDITY,
        "sensor_name": "Humidity"
    },
    {
        "uuid": CHARACTERISTIC_PRESSURE,
        "sensor_key": ThunderboardSensor.PRESSURE_PA,
        "format": '<I',
        "divider": 10,
        "sensor_unit": Units.PRESSURE_PA,
        "sensor_class": SensorDeviceClass.PRESSURE,
        "sensor_name": "Pressure"
    },
    {
        "uuid": CHARACTERISTIC_UV_IDX,
        "sensor_key": ThunderboardSensor.UV_IDX,
        "format": 'B',
        "divider": None,
        "sensor_unit": Units.UV_INDEX,
        "sensor_class": SensorDeviceClass.UV_INDEX,
        "sensor_name": "UV Index"
    },
    {
        "uuid": CHARACTERISTIC_SOUND_LEVEL,
        "sensor_key": ThunderboardSensor.SOUND_LEVEL_DBA,
        "format": '<h',
        "divider": 100,
        "sensor_unit": Units.SOUND_PRESSURE_WEIGHTED_DBA,
        "sensor_class": SensorDeviceClass.PRESSURE,
        "sensor_name": "Sound level"
    },
    {
        "uuid": CHARACTERISTIC_AMBIENT_LIGHT,
        "sensor_key": ThunderboardSensor.AMBIENT_LIGHT_LX,
        "format": '<I',
        "divider": 100,
        "sensor_unit": Units.LIGHT_LUX,
        "sensor_class": SensorDeviceClass.ILLUMINANCE,
        "sensor_name": "Ambient Light"
    },
    {
        "uuid": CHARACTERISTIC_HALL_FIELD,
        "sensor_key": ThunderboardSensor.HALL_FIELD_UT,
        "format": '<i',
        "divider": None,
        "sensor_unit": None,
        "sensor_class": None,
        "sensor_name": "Hall Field Strenght"
    }
]

THUNDERBOARD_GATT_DIGITAL_STATE_CHARS = [
    {
        "handle": CHARACTERISTIC_HANDLE_DIGITAL_STATE_0,
        "sensor_key": ThunderboardBinarySensor.DIGITAL_STATE_0,
    },
    {
        "handle": CHARACTERISTIC_HANDLE_DIGITAL_STATE_1,
        "sensor_key": ThunderboardBinarySensor.DIGITAL_STATE_1,
    }
]

THUNDERBOARD_GATT_DEVICE_CHARS = [
    {
        "uuid": CHARACTERISTIC_DEVICE_NAME,
        "sensor_key": ThunderboardDeviceInfo.DEVICE_NAME,
    },
    {
        "uuid": CHARACTERISTIC_MODEL_NUMBER,
        "sensor_key": ThunderboardDeviceInfo.MODEL_NUMBER,
    },
    {
        "uuid": CHARACTERISTIC_HARDWARE_REV,
        "sensor_key": ThunderboardDeviceInfo.HARDWARE_REV,
    },
    {   
        "uuid": CHARACTERISTIC_FIRMWARE_REV,
        "sensor_key": ThunderboardDeviceInfo.FIRMWARE_REV,
    }
]

POWER_SOURCE_MAP = {
    1: "USB",
    4: "Battery"
}

# BTN0 and BTN1
DIGITAL_STATE_0_MAP = {
    0: [],
    1: [0],
    4: [1],
    5: [0,1]
}

sensors_characteristics_uuid_str = [str(sensor_info["uuid"]) for sensor_info in THUNDERBOARD_GATT_SENSOR_CHARS]

@contextmanager
def override_bleak_retry_constants(bleak_timeout: float, bleak_safety_timeout: float):
    original_bleak_timeout = bleak_retry_connector.BLEAK_TIMEOUT
    original_bleak_safety_timeout = bleak_retry_connector.BLEAK_SAFETY_TIMEOUT
    bleak_retry_connector.BLEAK_TIMEOUT = bleak_timeout
    bleak_retry_connector.BLEAK_SAFETY_TIMEOUT = bleak_safety_timeout

    try:
        yield
    finally:
        bleak_retry_connector.BLEAK_TIMEOUT = original_bleak_timeout
        bleak_retry_connector.BLEAK_SAFETY_TIMEOUT = original_bleak_safety_timeout


class ThunderboardBluetoothDeviceData:
    """Data for Thunderboard BLE sensors."""

    def __init__(
        self,
        logger: logging.Logger,
    ):
        super().__init__()
        self.logger = logger
        self._event = None
        self._client = None
        self._device = None

    async def _read_device_characteristics(self) -> ThunderboardDevice:
        self._device.address = self._client.address

        # We need to fetch model to determ what to fetch.
        try:
            # Parse and set the identity of the Thunderboard
            for c in THUNDERBOARD_GATT_DEVICE_CHARS:
                payload = await self._client.read_gatt_char(c["uuid"])
                val = payload.decode('utf-8')
                setattr(self._device, str(c["sensor_key"]), val)                
        except BleakError as err:
            self.logger.debug("Get device characteristics exception: %s", err)
            return self._device

        # In some cases the device name will be empty, for example when using a Mac.
        if self._device.name == "":
            self._device.name = self._device.friendly_name()
        
        return self._device

    async def _read_gatt_sensor_char(self, uuid, format, divider) -> None:
        """ Get the payload value from the characteristic, processed """
        char = self._client.services.get_characteristic(uuid)
        payload = await self._client.read_gatt_char(char)
        value = struct.unpack(format, payload)[0]
        if uuid == CHARACTERISTIC_POWER_SOURCE:
            value = POWER_SOURCE_MAP[value]
        if divider:
            return value / divider
        return value

    async def _read_service_characteristics(self) -> ThunderboardDevice:
        sensors_values = {}
        for c in THUNDERBOARD_GATT_SENSOR_CHARS:
            val = await self._read_gatt_sensor_char(c["uuid"], c["format"], c["divider"])
            sensors_values[str(c["sensor_key"])] = val
        self._device.sensors.update(sensors_values)
        self.logger.debug("Successfully read active GATT characteristics")
        return self._device
    
    def get_updated_buttons_state(self, payload) -> ThunderboardDevice:
        return self._get_updated_digital_state(payload, ThunderboardBinarySensor.DIGITAL_STATE_0)
    
    def _get_updated_digital_state(self, payload, key) -> ThunderboardDevice:
        digital_values = {}
        val = struct.unpack("B", payload)[0]
        if key == ThunderboardBinarySensor.DIGITAL_STATE_0:
            val = DIGITAL_STATE_0_MAP[val]
            if 0 in val:
                digital_values[str(ThunderboardBinarySensor.BTN_0)] = True
            else:
                digital_values[str(ThunderboardBinarySensor.BTN_0)] = False
            if 1 in val:
                digital_values[str(ThunderboardBinarySensor.BTN_1)] = True
            else:
                digital_values[str(ThunderboardBinarySensor.BTN_1)] = False
        digital_values[str(key)] = val
        self._device.digitals.update(digital_values)
        return self._device


    async def _read_device_digital_state(self) -> ThunderboardDevice:
        for c in THUNDERBOARD_GATT_DIGITAL_STATE_CHARS:
            char = self._client.services.get_characteristic(c["handle"])
            payload = await self._client.read_gatt_char(char)
            self._device = self._get_updated_digital_state(payload, c["sensor_key"])
        self.logger.debug("Successfully read digital states GATT characteristics")
        return self._device

    async def _read_device_lights_state(self) -> ThunderboardDevice:
        light_controller = ThunderboardLightsController(self.logger, self._client)
        light_state = await light_controller.get_rgb_leds_state()
        self.logger.debug("Successfully read lights GATT characteristics")
        self._device.lights = light_state
        return self._device

    async def notification_on_buttons_press(self, button_state_callback: Callable) -> None:
        c = THUNDERBOARD_GATT_DIGITAL_STATE_CHARS[0]
        char = self._client.services.get_characteristic(c["handle"])
        await self._client.start_notify(char, button_state_callback)

    async def _get_client(self, ble_device: BLEDevice, scan_timeout: float = 30.0, max_attempts: int = 3) -> BleakClient:
        with override_bleak_retry_constants(bleak_timeout = scan_timeout, bleak_safety_timeout = scan_timeout * max_attempts):
            try:
                client = await bleak_retry_connector.establish_connection(
                            client_class = BleakClient, 
                            device = ble_device, 
                            name = ble_device.address,
                            max_attempts = max_attempts
                        )
                return client
            except Exception as e:
                self.logger.error("Error when connecting to Thunderboard BLE device, address: %s\n%s", ble_device.address, str(e))

    async def update_device(
        self, 
        ble_device: BLEDevice, 
        keep_connect: bool = False, 
        scan_timeout: float = 30.0,
        max_attempts: int = 3,
    ) -> ThunderboardDevice:
        """Connects to the device through BLE and retrieves relevant data"""
        self._device = ThunderboardDevice()
        # Deprecated Blake RSSI from BLEDevice, get it from AdvertisementData instead
        self._device.rssi = ble_device._rssi or -255

        self._client = await self._get_client(ble_device, scan_timeout, max_attempts)

        try:
            tasks = [
                self._read_device_characteristics(),
                self._read_service_characteristics(),
                self._read_device_lights_state(),
                self._read_device_digital_state()
            ]
            await asyncio.gather(*tasks)
        except BleakError as error:
            self.logger.error("Error when getting data from Thunderboard BLE device, address: %s\n%s", ble_device.address, str(error))
            self._device.error = str(error)
        except Exception as error:
            self.logger.error("Other error when getting data from Thunderboard BLE device, address: %s\n%s", ble_device.address, str(error))
            self._device.error = str(error)
        finally:
            if not keep_connect:
                await self._client.disconnect()

        return self._device