"""
Parser for Thunderboard BLE advertisements.

This file is shamelessly copied from the following repository:
https://github.com/Ernst79/bleparser/blob/c42ae922e1abed2720c7fac993777e1bd59c0c93/package/bleparser/oral_b.py
"""
from __future__ import annotations

from sensor_state_data import (
    BinarySensorDeviceClass,
    BinarySensorValue,
    DeviceKey,
    SensorDescription,
    SensorDeviceClass,
    SensorDeviceInfo,
    SensorUpdate,
    SensorValue,
    Units,
)

from .parser import (
    ThunderboardBinarySensor, 
    ThunderboardBluetoothDeviceData, 
    ThunderboardSensor, 
    ThunderboardDeviceInfo,
)

from .models import (
    ThunderboardDevice,
    ThunderboardLightsState,
)

from .lights import (
    ThunderboardLights,
    ThunderboardLightsController
)

__version__ = "0.1.0"

__all__ = [
    "ThunderboardDevice"
    "ThunderboardSensor",
    "ThunderboardBinarySensor",
    "ThunderboardBluetoothDeviceData",
    "ThunderboardDeviceInfo",
    "ThunderboardLights",
    "ThunderboardLightsController",
    "ThunderboardLightsState",
    "BinarySensorDeviceClass",
    "BinarySensorValue",
    "SensorDescription",
    "SensorDeviceInfo",
    "DeviceKey",
    "SensorUpdate",
    "SensorDeviceClass",
    "SensorValue",
    "Units",
]
