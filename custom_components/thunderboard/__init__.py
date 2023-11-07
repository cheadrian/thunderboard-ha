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
    DOMAIN
    )

PLATFORMS: list[Platform] = [Platform.SENSOR]

_LOGGER = logging.getLogger(__name__)

last_event_time = time.time()

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """ Set up Thunderboard BLE device from a config entry. """
    hass.data.setdefault(DOMAIN, {})
    address = entry.unique_id
    assert address is not None

    _LOGGER.debug("Thunderboard device address %s", address)
    thunderboard = ThunderboardBluetoothDeviceData(_LOGGER)
    scan_interval = DEFAULT_SCAN_INTERVAL

    async def _async_update_method():
        """ Get data from Thunderboard BLE. """
        _LOGGER.debug("Thunderboard update method.")
        ble_device = async_ble_device_from_address(hass, address)
        if not ble_device:
            raise ConfigEntryNotReady(
                f"Could not find Thunderboard device with address {address}"
            )
        _LOGGER.debug("Thunderboard BLE device is %s", ble_device)
        
        try:
            data = await thunderboard.update_device(ble_device)
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

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """ Unload a config entry. """
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok

async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """ Handle removal of an entry. """
    address = entry.unique_id
    assert address is not None
    ble_device = async_ble_device_from_address(hass, address)
    client = await establish_connection(BleakClient, ble_device, ble_device.address)
    await client.disconnect()