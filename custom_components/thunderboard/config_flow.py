"""Config flow for Thunderboard ble integration."""
from __future__ import annotations

from collections.abc import Mapping
import logging
from typing import Any

import probatio

from homeassistant.components.bluetooth import (
    BluetoothServiceInfoBleak,
    async_discovered_service_info,
)
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_ADDRESS, UnitOfTime
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
)

from .const import (
    ADD_BLE_CALLBACK,
    ADD_BLE_CALLBACK_KEY,
    CONNECTION_ATTEMPTS_RANGE,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    EVENT_DEBOUNCE_TIME,
    EVENT_DEBOUNCE_TIME_KEY,
    EVENT_DEBOUNCE_TIME_RANGE,
    KEEP_DEVICE_CONNECTED,
    KEEP_DEVICE_CONNECTED_KEY,
    MAX_CONNECTION_ATTEMPTS,
    MAX_CONNECTION_ATTEMPTS_KEY,
    MFCT_ID,
    NAME_PREFIX,
    SCAN_INTERVAL_KEY,
    SCAN_INTERVAL_RANGE,
    SCAN_TIMEOUT,
    SCAN_TIMEOUT_KEY,
    SCAN_TIMEOUT_RANGE,
)

_LOGGER = logging.getLogger(__name__)

# The options that are whole numbers
INTEGER_OPTIONS = (
    SCAN_INTERVAL_KEY,
    SCAN_TIMEOUT_KEY,
    MAX_CONNECTION_ATTEMPTS_KEY,
    EVENT_DEBOUNCE_TIME_KEY,
)


def _is_thunderboard(discovery_info: BluetoothServiceInfoBleak) -> bool:
    """The firmware advertises the Silicon Labs company ID and a name like Thunderboard #12345."""
    return MFCT_ID in discovery_info.manufacturer_data and (
        discovery_info.name or ""
    ).startswith(NAME_PREFIX)


class ThunderboardConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Thunderboard."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._discovery_info: BluetoothServiceInfoBleak | None = None
        self._discovered_devices: dict[str, BluetoothServiceInfoBleak] = {}

    async def async_step_bluetooth(
        self, discovery_info: BluetoothServiceInfoBleak
    ) -> ConfigFlowResult:
        """Handle the bluetooth discovery step."""
        _LOGGER.debug("Discovered BT device: %s", discovery_info.address)
        await self.async_set_unique_id(discovery_info.address)
        self._abort_if_unique_id_configured()
        if not _is_thunderboard(discovery_info):
            return self.async_abort(reason="not_supported")

        self._discovery_info = discovery_info
        self.context["title_placeholders"] = {"name": discovery_info.name}
        return await self.async_step_bluetooth_confirm()

    async def async_step_bluetooth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm discovery."""
        assert self._discovery_info is not None
        if user_input is not None:
            return self.async_create_entry(title=self._discovery_info.name, data={})

        self._set_confirm_only()
        return self.async_show_form(
            step_id="bluetooth_confirm",
            description_placeholders=self.context["title_placeholders"],
        )

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the user step to pick discovered device."""
        if user_input is not None:
            address = user_input[CONF_ADDRESS]
            await self.async_set_unique_id(address, raise_on_progress=False)
            self._abort_if_unique_id_configured()
            discovery_info = self._discovered_devices[address]
            self.context["title_placeholders"] = {"name": discovery_info.name}
            return self.async_create_entry(title=discovery_info.name, data={})

        current_addresses = self._async_current_ids()
        for discovery_info in async_discovered_service_info(self.hass):
            address = discovery_info.address
            if address in current_addresses or address in self._discovered_devices:
                continue
            if _is_thunderboard(discovery_info):
                self._discovered_devices[address] = discovery_info

        if not self._discovered_devices:
            return self.async_abort(reason="no_devices_found")

        titles = {
            address: f"{discovery_info.name} ({address})"
            for address, discovery_info in self._discovered_devices.items()
        }
        return self.async_show_form(
            step_id="user",
            data_schema=probatio.Schema(
                {
                    probatio.Required(CONF_ADDRESS): probatio.In(titles),
                },
            ),
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Create the options flow."""
        return OptionsFlowHandler()


def _number_box(bounds: tuple[int, int], unit: str | None = None) -> NumberSelector:
    """A number box with the limits of the option, it always shows its value unlike a slider."""
    config = NumberSelectorConfig(
        min=bounds[0], max=bounds[1], step=1, mode=NumberSelectorMode.BOX
    )
    if unit is not None:
        config["unit_of_measurement"] = unit
    return NumberSelector(config)


def options_schema(options: Mapping[str, Any]) -> probatio.Schema:
    """Return options schema."""
    return probatio.Schema(
        {
            probatio.Required(
                SCAN_INTERVAL_KEY,
                default=options.get(SCAN_INTERVAL_KEY, DEFAULT_SCAN_INTERVAL),
            ): _number_box(SCAN_INTERVAL_RANGE, UnitOfTime.SECONDS),
            probatio.Required(
                KEEP_DEVICE_CONNECTED_KEY,
                default=options.get(KEEP_DEVICE_CONNECTED_KEY, KEEP_DEVICE_CONNECTED),
            ): bool,
            probatio.Required(
                SCAN_TIMEOUT_KEY,
                default=options.get(SCAN_TIMEOUT_KEY, SCAN_TIMEOUT),
            ): _number_box(SCAN_TIMEOUT_RANGE, UnitOfTime.SECONDS),
            probatio.Required(
                MAX_CONNECTION_ATTEMPTS_KEY,
                default=options.get(
                    MAX_CONNECTION_ATTEMPTS_KEY, MAX_CONNECTION_ATTEMPTS
                ),
            ): _number_box(CONNECTION_ATTEMPTS_RANGE),
            probatio.Required(
                ADD_BLE_CALLBACK_KEY,
                default=options.get(ADD_BLE_CALLBACK_KEY, ADD_BLE_CALLBACK),
            ): bool,
            probatio.Required(
                EVENT_DEBOUNCE_TIME_KEY,
                default=options.get(EVENT_DEBOUNCE_TIME_KEY, EVENT_DEBOUNCE_TIME),
            ): _number_box(EVENT_DEBOUNCE_TIME_RANGE, UnitOfTime.SECONDS),
        }
    )


class OptionsFlowHandler(OptionsFlow):
    """Handle the options of a Thunderboard, the entry reloads when they change."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            # The number boxes hand over floats
            data = {
                key: round(value) if key in INTEGER_OPTIONS else value
                for key, value in user_input.items()
            }
            return self.async_create_entry(title="", data=data)

        return self.async_show_form(
            step_id="init",
            data_schema=options_schema(self.config_entry.options),
        )
