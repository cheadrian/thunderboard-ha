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
import bleak_retry_connector

from .models import ThunderboardDevice

from sensor_state_data import SensorDeviceClass, Units
from sensor_state_data.enum import StrEnum

_LOGGER = logging.getLogger(__name__)

""" Import BLE UUIDs constants for the Thunderboard. """
from .const import (
    CHARACTERISTIC_TEMPERATURE,
    CHARACTERISTIC_HUMIDITY,
    CHARACTERISTIC_DEVICE_NAME,
    CHARACTERISTIC_MODEL_NUMBER,
    CHARACTERISTIC_HARDWARE_REV,
    CHARACTERISTIC_FIRMWARE_REV,
)

class ThunderboardSensor(StrEnum):
    # Environmental sensors
    TEMPERATURE_C       = "temperature"
    HUMIDITY_PERCENT    = "humidity"

class ThunderboardDeviceInfo(StrEnum):
    # Device information
    DEVICE_NAME         = "name"
    APPEARANCE          = "appearance"
    MANUFACTURER_NAME   = "manufacturer"
    MODEL_NUMBER        = "model"
    HARDWARE_REV        = "hw_version"
    FIRMWARE_REV        = "sw_version"

""" Manufacturer ID for checking if it's a Thunderboard, equivalent to decimal 71. """
THUNDERBOARD_MANUFACTURER = 0x0047

""" Characteristics for the Thunderboard, how to format the data and what divider to apply. """
THUNDERBOARD_GATT_SENSOR_CHARS = [
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

sensors_characteristics_uuid_str = [str(sensor_info["uuid"]) for sensor_info in THUNDERBOARD_GATT_SENSOR_CHARS]

class ThunderboardBluetoothDeviceData:
    """ Data for Thunderboard BLE sensors. """
    def __init__(
        self,
        logger: logging.Logger,
    ):
        super().__init__()
        self.logger = logger
        self._client = None
        self._device = None

    async def _read_device_characteristics(self) -> ThunderboardDevice:
        self._device.address = self._client.address
        try:
            """ Parse and set the identity of the Thunderboard. """
            for c in THUNDERBOARD_GATT_DEVICE_CHARS:
                payload = await self._client.read_gatt_char(c["uuid"])
                val = payload.decode('utf-8')
                setattr(self._device, str(c["sensor_key"]), val)                
        except BleakError as err:
            self.logger.debug("Get device characteristics exception: %s", err)
            return self._device

        """ In some cases the device name will be empty, for example when using a Mac. """
        if self._device.name == "":
            self._device.name = self._device.friendly_name()
        
        return self._device

    async def _read_gatt_sensor_char(self, uuid, format, divider) -> None:
        """ Get the payload value from the characteristic, processed. """
        char = self._client.services.get_characteristic(uuid)
        payload = await self._client.read_gatt_char(char)
        """ Unpack bytes data from the payload. """
        value = struct.unpack(format, payload)[0]
        if divider:
            return value / divider
        return value

    async def _read_service_characteristics(self) -> ThunderboardDevice:
        """ Read the service characteritics, sensors in this case, and set the values in the device. """
        sensors_values = {}
        for c in THUNDERBOARD_GATT_SENSOR_CHARS:
            val = await self._read_gatt_sensor_char(c["uuid"], c["format"], c["divider"])
            sensors_values[str(c["sensor_key"])] = val
        self._device.sensors.update(sensors_values)
        self.logger.debug("Successfully read active GATT characteristics")
        return self._device

    async def _get_client(self, ble_device: BLEDevice) -> BleakClient:
        """ Get the Bleak client knowing the BLEDevice. """
        try:
            client = await bleak_retry_connector.establish_connection(
                        client_class = BleakClient, 
                        device = ble_device, 
                        name = ble_device.address,
                    )
            return client
        except Exception as e:
            self.logger.error("Error when connecting to Thunderboard BLE device, address: %s\n%s", ble_device.address, str(e))

    async def update_device(
        self, 
        ble_device: BLEDevice, 
    ) -> ThunderboardDevice:
        """ Connects to the device through BLE and retrieves relevant device data. """
        self._device = ThunderboardDevice()
        self._client = await self._get_client(ble_device)

        try:
            tasks = [
                self._read_device_characteristics(),
                self._read_service_characteristics()
            ]
            await asyncio.gather(*tasks)
        except BleakError as error:
            self.logger.error("Error when getting data from Thunderboard BLE device, address: %s\n%s", ble_device.address, str(error))
            self._device.error = str(error)
        except Exception as error:
            self.logger.error("Other error when getting data from Thunderboard BLE device, address: %s\n%s", ble_device.address, str(error))
            self._device.error = str(error)
        finally:
            await self._client.disconnect()

        return self._device