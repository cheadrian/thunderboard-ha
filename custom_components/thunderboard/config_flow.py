"""Config flow for Thunderboard ble integration."""
from __future__ import annotations

import dataclasses
import logging
from typing import Any, Mapping

from .thunderboard_ble import ThunderboardBluetoothDeviceData, ThunderboardDevice
from bleak import BleakError
import voluptuous as vol

from homeassistant.components import bluetooth
from homeassistant.components.bluetooth import (
    BluetoothServiceInfo,
    async_discovered_service_info,
)
from homeassistant.config_entries import ConfigFlow
from homeassistant import config_entries
from homeassistant.const import CONF_ADDRESS
from homeassistant.data_entry_flow import FlowResult

from .const import (
    DOMAIN, 
    MFCT_ID, 
    DEFAULT_SCAN_INTERVAL, 
    SCAN_INTERVAL_KEY, 
    KEEP_DEVICE_CONNECTED_KEY,
    KEEP_DEVICE_CONNECTED,
    SCAN_TIMEOUT_KEY,
    SCAN_TIMEOUT,
    MAX_CONNECTION_ATTEMPTS_KEY,
    MAX_CONNECTION_ATTEMPTS,
    ADD_BLE_CALLBACK_KEY,
    ADD_BLE_CALLBACK,
    EVENT_DEBOUNCE_TIME_KEY,
    EVENT_DEBOUNCE_TIME
    )

_LOGGER = logging.getLogger(__name__)


@dataclasses.dataclass
class Discovery:
    """A discovered bluetooth device."""

    name: str
    discovery_info: BluetoothServiceInfo
    device: ThunderboardDevice


def get_name(device: ThunderboardDevice) -> str:
    """Generate name with model and identifier for device."""

    name = device.friendly_name()
    if identifier := device.identifier:
        name += f" ({identifier})"
    return name

class ThunderboardDeviceUpdateError(Exception):
    """Custom error class for device updates."""

class ThunderboardConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Thunderboard."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._discovered_device: Discovery | None = None
        self._discovered_devices: dict[str, Discovery] = {}

    async def _get_device_data(
        self, discovery_info: BluetoothServiceInfo
    ) -> ThunderboardDevice:
        ble_device = bluetooth.async_ble_device_from_address(
            self.hass, discovery_info.address
        )
        if ble_device is None:
            _LOGGER.debug("no ble_device in _get_device_data")
            raise ThunderboardDeviceUpdateError("No ble_device")

        thunderboard = ThunderboardBluetoothDeviceData(_LOGGER)

        try:
            data = await thunderboard.update_device(ble_device)
        except BleakError as err:
            _LOGGER.error(
                "Error connecting to and getting data from %s: %s",
                discovery_info.address,
                err,
            )
            raise ThunderboardDeviceUpdateError("Failed getting device data") from err
        except Exception as err:
            _LOGGER.error(
                "Unknown error occurred from %s: %s", discovery_info.address, err
            )
            raise err
        return data

    async def async_step_bluetooth(
        self, discovery_info: BluetoothServiceInfo
    ) -> FlowResult:
        """Handle the bluetooth discovery step."""
        _LOGGER.debug("Discovered BT device: %s", discovery_info.address)
        await self.async_set_unique_id(discovery_info.address)
        self._abort_if_unique_id_configured()

        try:
            device = await self._get_device_data(discovery_info)
        except ThunderboardDeviceUpdateError:
            return self.async_abort(reason="cannot_connect")
        except Exception:  # pylint: disable=broad-except
            return self.async_abort(reason="unknown")

        name = get_name(device)
        self.context["title_placeholders"] = {"name": name}
        self._discovered_device = Discovery(name, discovery_info, device)

        return await self.async_step_bluetooth_confirm()

    async def async_step_bluetooth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Confirm discovery."""
        if user_input is not None:
            return self.async_create_entry(
                title=self.context["title_placeholders"]["name"], data={}
            )

        self._set_confirm_only()
        return self.async_show_form(
            step_id="bluetooth_confirm",
            description_placeholders=self.context["title_placeholders"],
        )

    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Create the options flow."""
        return OptionsFlowHandler(config_entry)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the user step to pick discovered device."""
        if user_input is not None:
            address = user_input[CONF_ADDRESS]
            await self.async_set_unique_id(address, raise_on_progress=False)
            self._abort_if_unique_id_configured()
            discovery = self._discovered_devices[address]

            self.context["title_placeholders"] = {
                "name": discovery.name,
            }

            self._discovered_device = discovery

            return self.async_create_entry(title=discovery.name, data={})

        current_addresses = self._async_current_ids()
        for discovery_info in async_discovered_service_info(self.hass):
            address = discovery_info.address
            if address in current_addresses or address in self._discovered_devices:
                continue
            if MFCT_ID not in discovery_info.manufacturer_data:
                continue
            try:
                device = await self._get_device_data(discovery_info)
            except ThunderboardDeviceUpdateError:
                return self.async_abort(reason="cannot_connect")
            except Exception:  # pylint: disable=broad-except
                return self.async_abort(reason="unknown")
            name = get_name(device)
            self._discovered_devices[address] = Discovery(name, discovery_info, device)

        if not self._discovered_devices:
            return self.async_abort(reason="no_devices_found")

        titles = {
            address: discovery.device.name
            for (address, discovery) in self._discovered_devices.items()
        }
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_ADDRESS): vol.In(titles),
                },
            ),
        )

def options_schema(
    options: Mapping[str, Any] | None = None
) -> dict[vol.Optional, type[str]]:
    """Return options schema."""
    options = options or {}
    return {
        vol.Required(
            SCAN_INTERVAL_KEY,
            default=options.get(SCAN_INTERVAL_KEY, DEFAULT_SCAN_INTERVAL),
        ): int,
        vol.Required(
            KEEP_DEVICE_CONNECTED_KEY,
            default=options.get(KEEP_DEVICE_CONNECTED_KEY, KEEP_DEVICE_CONNECTED),
        ): bool,
        vol.Required(
            SCAN_TIMEOUT_KEY,
            default=options.get(SCAN_TIMEOUT_KEY, SCAN_TIMEOUT),
        ): int,
        vol.Required(
            MAX_CONNECTION_ATTEMPTS_KEY,
            default=options.get(MAX_CONNECTION_ATTEMPTS_KEY, MAX_CONNECTION_ATTEMPTS),
        ): int,
        vol.Required(
            ADD_BLE_CALLBACK_KEY,
            default=options.get(ADD_BLE_CALLBACK_KEY, ADD_BLE_CALLBACK),
        ): bool,
        vol.Required(
            EVENT_DEBOUNCE_TIME_KEY,
            default=options.get(EVENT_DEBOUNCE_TIME_KEY, EVENT_DEBOUNCE_TIME),
        ): int
    }

def new_options(
    custom_polling_interval: int, 
    keep_connect: bool, 
    scan_timeout: int, 
    max_connection_attempts: int,
    add_ble_callback: bool,
    event_debounce_time: int
) -> dict[str, list[int]]:
    """Create a standard options object."""
    return {
        SCAN_INTERVAL_KEY: custom_polling_interval, 
        KEEP_DEVICE_CONNECTED_KEY: keep_connect,
        SCAN_TIMEOUT_KEY: scan_timeout,
        MAX_CONNECTION_ATTEMPTS_KEY: max_connection_attempts,
        ADD_BLE_CALLBACK_KEY: add_ble_callback,
        EVENT_DEBOUNCE_TIME_KEY: event_debounce_time
    }

def options_data(user_input: dict[str, str]) -> dict[str, list[int]]:
    """Return options dict."""
    return new_options(
        user_input.get(SCAN_INTERVAL_KEY), 
        user_input.get(KEEP_DEVICE_CONNECTED_KEY),
        user_input.get(SCAN_TIMEOUT_KEY),
        user_input.get(MAX_CONNECTION_ATTEMPTS_KEY),
        user_input.get(ADD_BLE_CALLBACK_KEY),
        user_input.get(EVENT_DEBOUNCE_TIME_KEY)
    )

class OptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(
                title="", 
                data=options_data(user_input)
        )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(options_schema(self.config_entry.options)),
        )