""" Test for Thunderboard BLE parser and control """
import asyncio
import logging, sys

from bleak import BleakScanner, BLEDevice
from thunderboard_ble import ThunderboardBluetoothDeviceData

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
_LOGGER = logging.getLogger(__name__)
_LOGGER.setLevel(logging.DEBUG)

SCAN_FOR_DEVICE = True
DEVICE_NAME = "Thunderboard"
# Only if scan is False
DEVICE_ADDRESS = "00:0B:57:64:88:68"
DEVICE_PATH = "/org/bluez/hci0/dev_00_0B_57_64_88_68"

async def scan_for_device(device_name):
    while True:
        devices = await BleakScanner.discover()

        # Check if the desired device is in the list
        for device in devices:
            if device_name in device.name:
                return device

if __name__ == "__main__":
    parser = ThunderboardBluetoothDeviceData(_LOGGER)
    
    device_name_to_find = DEVICE_NAME

    async def test_data_update():
        # Devine an device to use in predefined mode
        device = BLEDevice(address=DEVICE_ADDRESS, name=DEVICE_NAME, details={"path": DEVICE_PATH}, rssi=-127)
        # Activate scan mode for the Bluetooth interface.
        if SCAN_FOR_DEVICE:
            print(f"Waiting for an device with {device_name_to_find} in name")
            device = await scan_for_device(device_name_to_find)
            print(f"Found device\n{device}")
        else:
            print(f"Using predefined device with MAC {device.address}")
        # Connect and get the data from the sensors.
        polled_device = await parser.update_device(device, False)
        print(f"---- Thunderboard Device Data ---- \n{polled_device}")
    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(test_data_update())
    except KeyboardInterrupt:
        print("Scan interrupted by user.")