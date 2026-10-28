"""Coordinator of the Thunderboard integration."""
from __future__ import annotations

from datetime import timedelta
import logging

from bleak import BleakError

from homeassistant.components.bluetooth import (
    async_ble_device_from_address,
    async_last_service_info,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    KEEP_DEVICE_CONNECTED,
    KEEP_DEVICE_CONNECTED_KEY,
    MAX_CONNECTION_ATTEMPTS,
    MAX_CONNECTION_ATTEMPTS_KEY,
    SCAN_INTERVAL_KEY,
    SCAN_TIMEOUT,
    SCAN_TIMEOUT_KEY,
)
from .thunderboard_ble import (
    ThunderboardBluetoothDeviceData,
    ThunderboardDevice,
    ThunderboardError,
)

_LOGGER = logging.getLogger(__name__)

# What a board that cannot be reached right now raises
_CONNECTION_ERRORS = (BleakError, ThunderboardError, EOFError, OSError)

type ThunderboardConfigEntry = ConfigEntry[ThunderboardCoordinator]


class ThunderboardCoordinator(DataUpdateCoordinator[ThunderboardDevice]):
    """Poll a Thunderboard over a BLE connection that is shared with the LEDs and buttons."""

    config_entry: ThunderboardConfigEntry

    def __init__(self, hass: HomeAssistant, entry: ThunderboardConfigEntry) -> None:
        assert entry.unique_id is not None
        options = entry.options
        scan_interval = options.get(SCAN_INTERVAL_KEY, DEFAULT_SCAN_INTERVAL)
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=f"{DOMAIN} {entry.title}",
            update_interval=timedelta(seconds=scan_interval),
        )
        _LOGGER.debug("Polling interval is set to: %s seconds", scan_interval)
        self.address: str = entry.unique_id
        self.keep_connect: bool = options.get(
            KEEP_DEVICE_CONNECTED_KEY, KEEP_DEVICE_CONNECTED
        )
        self.device_data = ThunderboardBluetoothDeviceData(
            _LOGGER,
            keep_connect=self.keep_connect,
            scan_timeout=options.get(SCAN_TIMEOUT_KEY, SCAN_TIMEOUT),
            max_attempts=options.get(
                MAX_CONNECTION_ATTEMPTS_KEY, MAX_CONNECTION_ATTEMPTS
            ),
        )
        self.device_data.set_button_callback(self._handle_buttons)
        self.device_data.set_connection_callback(self._handle_connection_change)

    async def _async_update_data(self) -> ThunderboardDevice:
        """Get data from the Thunderboard."""
        # The board stops advertising while connected, so there may be no BLEDevice
        # for a while. It is only needed to open a connection.
        ble_device = async_ble_device_from_address(self.hass, self.address)
        service_info = async_last_service_info(self.hass, self.address)
        rssi = service_info.rssi if service_info is not None else None
        try:
            return await self.device_data.update_device(ble_device, rssi=rssi)
        except _CONNECTION_ERRORS as err:
            raise UpdateFailed(
                f"Unable to fetch data from {self.address}: {err}"
            ) from err

    async def async_update_lights(
        self,
        *,
        on: int = 0,
        off: int = 0,
        rgb: tuple[int, int, int] | None = None,
        brightness: int | None = None,
    ) -> None:
        """Switch RGB LEDs on and off, and optionally change the colour they all share."""
        ble_device = async_ble_device_from_address(self.hass, self.address)
        try:
            await self.device_data.async_update_lights(
                ble_device, on=on, off=off, rgb=rgb, brightness=brightness
            )
        except _CONNECTION_ERRORS as err:
            raise HomeAssistantError(
                f"Unable to set the LEDs of {self.config_entry.title}: {err}"
            ) from err
        self.async_update_listeners()

    async def async_shutdown(self) -> None:
        """Stop polling and release the single connection the board accepts."""
        await super().async_shutdown()
        await self.device_data.async_disconnect()

    async def async_disconnect_on_stop(self, event: Event) -> None:
        """Let go of the board when Home Assistant stops, a connected board does not advertise."""
        await self.device_data.async_disconnect()

    @callback
    def _handle_buttons(self, device: ThunderboardDevice) -> None:
        # The device is the coordinator data, updated in place. Notifying the listeners
        # directly keeps the polling schedule, unlike async_set_updated_data.
        self.async_update_listeners()

    @callback
    def _handle_connection_change(self, connected: bool, unexpected: bool) -> None:
        """Show the connection state at once, and reconnect right away after a drop.

        Without this a dropped board would stay disconnected, and its LEDs dark, until the
        next poll. The refresh debouncer allows one attempt every 10 seconds.
        """
        self.async_update_listeners()
        if unexpected:
            self.config_entry.async_create_background_task(
                self.hass,
                self.async_request_refresh(),
                name=f"{DOMAIN} {self.address} reconnect",
            )
