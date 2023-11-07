"""
Parser for Thunderboard BLE advertisements.
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
    "ThunderboardDevice",
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
