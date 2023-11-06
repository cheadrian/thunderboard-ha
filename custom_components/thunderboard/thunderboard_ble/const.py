"""
From Simplicity Studio Thunderboard Sense 2 Demo project GATT definition: Bluetooth - SoC Thunderboard Sense 2
Also https://github.com/SiliconLabs/EFRConnect-android/blob/master/mobile/src/main/java/com/siliconlabs/bledemo/Bluetooth/BLE/GattCharacteristic.kt
"""

# Power and battery
CHARACTERISTIC_BATTERY          = "00002a19-0000-1000-8000-00805f9b34fb"
CHARACTERISTIC_POWER_SOURCE     = "ec61a454-ed01-a5e8-b8f9-de9ec026ec51"

# Environmental sensors
CHARACTERISTIC_TEMPERATURE      = "00002a6e-0000-1000-8000-00805f9b34fb"
CHARACTERISTIC_HUMIDITY         = "00002a6f-0000-1000-8000-00805f9b34fb"
CHARACTERISTIC_PRESSURE         = "00002a6d-0000-1000-8000-00805f9b34fb"
CHARACTERISTIC_UV_IDX           = "00002a76-0000-1000-8000-00805f9b34fb"
CHARACTERISTIC_SOUND_LEVEL      = "c8546913-bf02-45eb-8dde-9f8754f4a32e"
CHARACTERISTIC_AMBIENT_LIGHT    = "c8546913-bfd9-45eb-8dde-9f8754f4a32e"
CHARACTERISTIC_HALL_FIELD       = "f598dbc5-2f02-4ec5-9936-b3d1aa4f957f"

# Device information
CHARACTERISTIC_DEVICE_NAME      = "00002a00-0000-1000-8000-00805f9b34fb"
CHARACTERISTIC_APPEARANCE       = "00002a01-0000-1000-8000-00805f9b34fb"
CHARACTERISTIC_MANUFACTURER_NAME = "00002a29-0000-1000-8000-00805f9b34fb"
CHARACTERISTIC_MODEL_NUMBER     = "00002a24-0000-1000-8000-00805f9b34fb"
CHARACTERISTIC_SERIAL_NUMBER    = "00002a25-0000-1000-8000-00805f9b34fb"
CHARACTERISTIC_HARDWARE_REV     = "00002a27-0000-1000-8000-00805f9b34fb"
CHARACTERISTIC_FIRMWARE_REV     = "00002a26-0000-1000-8000-00805f9b34fb"
CHARACTERISTIC_SYSTEM_ID        = "00002a23-0000-1000-8000-00805f9b34fb"

# RGB LEGS
CHARACTERISTIC_RGB_LEDS_1       = "fcb89c40-c603-59f3-7dc3-5ece444a401b"

# AIO DIGITAL
CHARACTERISTIC_DIGITAL_STATE_0 = "00002a56-0000-1000-8000-00805f9b34fb"
CHARACTERISTIC_HANDLE_DIGITAL_STATE_0 = 28
CHARACTERISTIC_HANDLE_DIGITAL_STATE_1 = 33

# Details
# Power source
# Read
# Power source - Read - ec61a454-ed01-a5e8-b8f9-de9ec026ec51

# Indoor Air Quality, only when connected to external PS
# ECO2 - Read - efd658ae-c401-ef33-76e7-91b00019103b
# TVOC - Read - efd658ae-c402-ef33-76e7-91b00019103b

# Hall Effect
# State - Read, Notify - f598dbc5-2f01-4ec5-9936-b3d1aa4f957f
# Field Strenght - Read, Notify - f598dbc5-2f02-4ec5-9936-b3d1aa4f957f
# Control Point - Write - f598dbc5-2f03-4ec5-9936-b3d1aa4f957f

# IMU
# Acceleration - Notify - 6 bytes - c4c1f6e2-4be5-11e5-885d-feff819cdc9f
# Orientation - Notify - 6 bytes - b7c4b694-bee3-45dd-ba9f-f3b5e994f49a
# Control Point - Write, Indicate - 71e30b8c-4131-4703-b0a0-b0bbba75856b

# UI
# RGB Leds - Read, Write - fcb89c40-c603-59f3-7dc3-5ece444a401b
# RGB Leds Mask - Read - 1c694489-8825-45cc-8720-28b54b1fbf00

# Generic Access
# Device Name - Read, Write - 19 bytes - 2A00
# Appearance - Read - 2A01

# Device Information
# All Read
# Manufacturer Name String - 20 bytes - 2A29
# Model Number String - 8 bytes - 2A24
# Serial Number String - 4 bytes - 2A25
# Hardware Revision String - 3 bytes - 2A27
# Firmware Revision String - 5 bytes - 2A26
# System ID - 8 byte - 2A23

# Silicon Labs OTA
# Silicon Labs OTA Control - Write - F7BF3564-FB6D-4E53-88A4-5E37E0326063

# Automation IO
# Digital - aio_digital_in - Read, Notify - 2A56
# Digital - aio_digital_out - Read, Write - 2A56