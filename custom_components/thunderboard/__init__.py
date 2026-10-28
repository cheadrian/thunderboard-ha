"""The Thunderboard integration."""
from __future__ import annotations

import logging
from time import monotonic

from homeassistant.components.bluetooth import (
    BluetoothCallbackMatcher,
    BluetoothChange,
    BluetoothScanningMode,
    BluetoothServiceInfoBleak,
    async_register_callback,
)
from homeassistant.const import EVENT_HOMEASSISTANT_STOP, Platform
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryError

from .const import (
    ADD_BLE_CALLBACK,
    ADD_BLE_CALLBACK_KEY,
    DOMAIN,
    EVENT_DEBOUNCE_TIME,
    EVENT_DEBOUNCE_TIME_KEY,
)
from .coordinator import ThunderboardConfigEntry, ThunderboardCoordinator

PLATFORMS: list[Platform] = [Platform.BINARY_SENSOR, Platform.LIGHT, Platform.SENSOR]

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ThunderboardConfigEntry
) -> bool:
    """Set up Thunderboard BLE device from a config entry."""
    if entry.unique_id is None:
        raise ConfigEntryError("The config entry has no Bluetooth address")
    _LOGGER.debug("Thunderboard device address %s", entry.unique_id)

    coordinator = ThunderboardCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    entry.async_on_unload(
        hass.bus.async_listen_once(
            EVENT_HOMEASSISTANT_STOP, coordinator.async_disconnect_on_stop
        )
    )
    # Check if the user wants to refresh the data when the device advertises again
    if entry.options.get(ADD_BLE_CALLBACK_KEY, ADD_BLE_CALLBACK):
        _LOGGER.debug("Registering BLE callback")
        entry.async_on_unload(
            _async_register_advertisement_refresh(hass, entry, coordinator)
        )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


@callback
def _async_register_advertisement_refresh(
    hass: HomeAssistant,
    entry: ThunderboardConfigEntry,
    coordinator: ThunderboardCoordinator,
) -> CALLBACK_TYPE:
    """Refresh the data when the device starts to advertise again, for example after a reboot."""
    event_debounce_time = entry.options.get(
        EVENT_DEBOUNCE_TIME_KEY, EVENT_DEBOUNCE_TIME
    )
    last_refresh = monotonic()

    @callback
    def _async_handle_bluetooth_event(
        service_info: BluetoothServiceInfoBleak, change: BluetoothChange
    ) -> None:
        nonlocal last_refresh
        time_difference = monotonic() - last_refresh
        # Do not require data update if is faster than defined event debounce time
        if time_difference < event_debounce_time:
            return
        _LOGGER.debug(
            "BLE event received: %s, require coordinator to update the data",
            service_info,
        )
        last_refresh = monotonic()
        entry.async_create_background_task(
            hass,
            coordinator.async_request_refresh(),
            name=f"{DOMAIN} {coordinator.address} refresh on advertisement",
        )

    return async_register_callback(
        hass,
        _async_handle_bluetooth_event,
        BluetoothCallbackMatcher(address=coordinator.address),
        BluetoothScanningMode.PASSIVE,
    )


async def _async_update_listener(
    hass: HomeAssistant, entry: ThunderboardConfigEntry
) -> None:
    """Reload the entry when the options are updated."""
    _LOGGER.debug("Updated options %s", entry.options)
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(
    hass: HomeAssistant, entry: ThunderboardConfigEntry
) -> bool:
    """Unload a config entry, the coordinator disconnects the board when it shuts down."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
