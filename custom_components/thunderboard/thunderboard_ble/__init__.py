"""
Parser for Thunderboard BLE advertisements.
"""
from __future__ import annotations

from sensor_state_data import (
    DeviceKey,
    SensorDescription,
    SensorDeviceClass,
    SensorDeviceInfo,
    SensorUpdate,
    SensorValue,
    Units,
)

from .parser import (
    ThunderboardBluetoothDeviceData, 
    ThunderboardSensor, 
    ThunderboardDeviceInfo,
)

from .models import ThunderboardDevice

__version__ = "0.1.0"

__all__ = [
    "ThunderboardDevice",
    "ThunderboardSensor",
    "ThunderboardBluetoothDeviceData",
    "ThunderboardDeviceInfo",
    "SensorDescription",
    "SensorDeviceInfo",
    "DeviceKey",
    "SensorUpdate",
    "SensorDeviceClass",
    "SensorValue",
    "Units",
]
