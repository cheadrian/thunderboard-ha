""" Test for Thunderboard BLE parser and control, run it outside of Home Assistant from this folder """
import asyncio
import logging
import sys

from bleak import BleakScanner
from thunderboard_ble import ThunderboardBluetoothDeviceData

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
_LOGGER = logging.getLogger(__name__)
_LOGGER.setLevel(logging.DEBUG)

# Part of the name or the address of the board, for example Thunderboard #12345
DEVICE_NAME = sys.argv[1] if len(sys.argv) > 1 else "Thunderboard"


async def scan_for_device(device_name):
    while True:
        found = await BleakScanner.discover(return_adv=True)
        for device, advertisement in found.values():
            name = advertisement.local_name or device.name or ""
            if device_name in name or device_name.lower() in device.address.lower():
                return device, advertisement.rssi


if __name__ == "__main__":
    parser = ThunderboardBluetoothDeviceData(_LOGGER, keep_connect=False)

    async def test_data_update():
        print(f"Waiting for a device with {DEVICE_NAME} in name or address")
        device, rssi = await scan_for_device(DEVICE_NAME)
        print(f"Found device\n{device}")
        # Connect and get the data from the sensors.
        polled_device = await parser.update_device(device, rssi=rssi)
        print(f"---- Thunderboard Device Data ---- \n{polled_device}")
        await parser.async_disconnect()

    try:
        asyncio.run(test_data_update())
    except KeyboardInterrupt:
        print("Scan interrupted by user.")
