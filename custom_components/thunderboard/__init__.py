"""The Thunderboard integration."""
from __future__ import annotations

import asyncio
from datetime import timedelta
import time
import logging

from .thunderboard_ble import ThunderboardBluetoothDeviceData, ThunderboardDevice

from bleak import BleakClient
from bleak_retry_connector import establish_connection
from homeassistant.components.bluetooth import async_ble_device_from_address
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import (
    DEFAULT_SCAN_INTERVAL, 
    DOMAIN, 
    SCAN_INTERVAL_KEY, 
    KEEP_DEVICE_CONNECTED_KEY,
    KEEP_DEVICE_CONNECTED,
    SCAN_TIMEOUT_KEY,
    SCAN_TIMEOUT,
    MAX_CONNECTION_ATTEMPTS_KEY,
    MAX_CONNECTION_ATTEMPTS,
    ADD_BLE_CALLBACK_KEY,
    ADD_BLE_CALLBACK,
    ADD_BLE_CALLBACK_KEY,
    EVENT_DEBOUNCE_TIME_KEY,
    EVENT_DEBOUNCE_TIME
    )

from homeassistant.components.bluetooth.api import async_register_callback
from homeassistant.components.bluetooth.models import BluetoothScanningMode, BluetoothServiceInfoBleak, BluetoothChange
from homeassistant.components.bluetooth.match import BluetoothCallbackMatcher

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.LIGHT]

_LOGGER = logging.getLogger(__name__)

last_event_time = time.time()

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Thunderboard BLE device from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    address = entry.unique_id
    assert address is not None
    entry.async_on_unload(entry.add_update_listener(update_listener))

    _LOGGER.debug("Thunderboard device address %s", address)
    thunderboard = ThunderboardBluetoothDeviceData(_LOGGER)
    scan_interval = entry.options.get(SCAN_INTERVAL_KEY, DEFAULT_SCAN_INTERVAL)
    scan_timeout = entry.options.get(SCAN_TIMEOUT_KEY, SCAN_TIMEOUT)
    max_attempts = entry.options.get(MAX_CONNECTION_ATTEMPTS_KEY, MAX_CONNECTION_ATTEMPTS)
    event_debounce_time = entry.options.get(EVENT_DEBOUNCE_TIME_KEY, EVENT_DEBOUNCE_TIME)
    keep_connect = entry.options.get(KEEP_DEVICE_CONNECTED_KEY, KEEP_DEVICE_CONNECTED)

    async def _async_update_method():
        """Get data from Thunderboard BLE."""
        _LOGGER.debug("Thunderboard update method.")
        ble_device = async_ble_device_from_address(hass, address)
        if not ble_device:
            raise ConfigEntryNotReady(
                f"Could not find Thunderboard device with address {address}"
            )
        _LOGGER.debug("Thunderboard BLE device is %s", ble_device)
        
        try:
            data = await thunderboard.update_device(ble_device, keep_connect, scan_timeout, max_attempts)
        except Exception as err:
            raise UpdateFailed(f"Unable to fetch data: {err}") from err

        return data


    _LOGGER.debug("Polling interval is set to: %s seconds", scan_interval)

    coordinator = hass.data.setdefault(DOMAIN, {})[
        entry.entry_id
    ] = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=DOMAIN,
        update_method=_async_update_method,
        update_interval=timedelta(seconds=scan_interval),
    )

    await coordinator.async_config_entry_first_refresh()

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Define and register an Bluetooth event callback to update the data when device start to advertise again
    def async_handle_bluetooth_event(service_info: BluetoothServiceInfoBleak, change: BluetoothChange) -> None:
        """Handle a Bluetooth event."""
        global last_event_time
        _LOGGER.debug("BLE event received: %s, change %s", service_info, change)
        time_difference = time.time() - last_event_time
        # Do not require data update if is faster than defined event debounce time
        if time_difference > event_debounce_time:
            # Refresh data when device advertising is detected
            _LOGGER.debug("Require coordinator to update the data")
            loop = asyncio.get_running_loop()
            loop.create_task(coordinator.async_request_refresh())
            last_event_time = time.time()
        else:
            _LOGGER.debug("Don't request data due to time difference: %d < %d", time_difference, event_debounce_time)

    # Check if user don't want to register an callback
    if entry.options.get(ADD_BLE_CALLBACK_KEY, ADD_BLE_CALLBACK):
        _LOGGER.debug("Registering BLE callback")
        async_register_callback(
            hass,
            async_handle_bluetooth_event,
            BluetoothCallbackMatcher(address=address),
            BluetoothScanningMode.PASSIVE,
        )

    def notification_callback(sender: int, payload: bytearray):
        """Handle notification data from the device."""
        data = thunderboard.get_updated_buttons_state(payload)
        coordinator.async_set_updated_data(data)
        _LOGGER.debug(f"Received notification from {sender}: {data}")

    if keep_connect:
        _LOGGER.debug(f"Enable notification on buttons press")
        await thunderboard.notification_on_buttons_press(notification_callback)

    return True

# Reload entry when options are updated
async def update_listener(hass: HomeAssistant, entry: ConfigEntry)-> None:
    """Handle options update."""
    _LOGGER.debug("Updated options %s", entry.options)
    await hass.config_entries.async_reload(entry.entry_id)

# Unload entry when removed
async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok

# Remove entry and assure the device will be disconnected
async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle removal of an entry."""
    address = entry.unique_id
    assert address is not None
    ble_device = async_ble_device_from_address(hass, address)
    client = await establish_connection(BleakClient, ble_device, ble_device.address)
    await client.disconnect()