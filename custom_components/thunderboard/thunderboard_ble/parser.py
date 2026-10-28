"""
Parser and connection manager for the Thunderboard Sense 2 BLE GATT server.
# Parsing demo: https://community.silabs.com/s/share/a5U1M000000kntwUAA/thunderboard-sense-with-raspberry-pi-and-python
"""
from __future__ import annotations

import asyncio
from collections.abc import Callable, Mapping
import dataclasses
from datetime import UTC, datetime
from enum import StrEnum
import logging
import struct
from typing import TYPE_CHECKING

from bleak import BleakError
from bleak_retry_connector import BleakClientWithServiceCache, establish_connection

from .const import (
    CHARACTERISTIC_AMBIENT_LIGHT,
    CHARACTERISTIC_BATTERY,
    CHARACTERISTIC_DIGITAL,
    CHARACTERISTIC_ECO2,
    CHARACTERISTIC_FIRMWARE_REV,
    CHARACTERISTIC_HALL_FIELD,
    CHARACTERISTIC_HARDWARE_REV,
    CHARACTERISTIC_HUMIDITY,
    CHARACTERISTIC_MANUFACTURER_NAME,
    CHARACTERISTIC_MODEL_NUMBER,
    CHARACTERISTIC_POWER_SOURCE,
    CHARACTERISTIC_PRESSURE,
    CHARACTERISTIC_RGB_LEDS_1,
    CHARACTERISTIC_SOUND_LEVEL,
    CHARACTERISTIC_TEMPERATURE,
    CHARACTERISTIC_TVOC,
    CHARACTERISTIC_UV_IDX,
    RGB_LED_MASK_ALL,
)
from .lights import decode_rgb_leds, encode_rgb_leds
from .models import (
    ThunderboardConnectionStats,
    ThunderboardDevice,
    ThunderboardLightsState,
)

if TYPE_CHECKING:
    from bleak import BLEDevice
    from bleak.backends.characteristic import BleakGATTCharacteristic

_LOGGER = logging.getLogger(__name__)

# Errors raised by bleak when a read, write or disconnect does not go through
_BLE_ERRORS = (BleakError, EOFError, BrokenPipeError)

READ_TIMEOUT = 10.0
DISCONNECT_TIMEOUT = 10.0


class ThunderboardError(Exception):
    """The Thunderboard cannot be reached or does not answer."""


class ThunderboardSensor(StrEnum):
    SIGNAL_STRENGTH     = "signal_strength"
    # Power and battery
    BATTERY_PERCENT     = "battery"
    POWER_SOURCE        = "power_source"
    # Environmental sensors
    TEMPERATURE_C       = "temperature"
    HUMIDITY_PERCENT    = "humidity"
    PRESSURE_PA         = "pressure"
    UV_IDX              = "uv_idx"
    SOUND_LEVEL_DB      = "sound_level"
    AMBIENT_LIGHT_LX    = "ambient_light"
    HALL_FIELD_UT       = "hall_field_strength"
    # Indoor air quality
    ECO2_PPM            = "eco2"
    TVOC_PPB            = "tvoc"


class ThunderboardBinarySensor(StrEnum):
    # Buttons
    BTN_0               = "btn_0"
    BTN_1               = "btn_1"
    # LED state, 2 bits per LED in the digital output characteristic
    LED_0               = "led_0"
    LED_1               = "led_1"


class ThunderboardDeviceInfo(StrEnum):
    # Device information, the values are the attribute names of ThunderboardDevice
    MANUFACTURER_NAME   = "manufacturer"
    MODEL_NUMBER        = "model"
    HARDWARE_REV        = "hw_version"
    FIRMWARE_REV        = "sw_version"


THUNDERBOARD_MANUFACTURER = 0x0047

POWER_SOURCE_MAP = {
    0: "unknown",
    1: "usb",
    2: "aa",
    3: "aaa",
    4: "cr2032",
}
POWER_SOURCE_OPTIONS = list(POWER_SOURCE_MAP.values())

BUTTON_KEYS = (ThunderboardBinarySensor.BTN_0, ThunderboardBinarySensor.BTN_1)
LED_KEYS = (ThunderboardBinarySensor.LED_0, ThunderboardBinarySensor.LED_1)


@dataclasses.dataclass(frozen=True, slots=True)
class _SensorCharacteristic:
    """How to decode a sensor characteristic."""

    key: ThunderboardSensor
    uuid: str
    format: str
    divider: int | None = None
    # Raw values sent by the firmware while the sensor is not initialised
    invalid: frozenset[int] = frozenset()
    mapping: Mapping[int, str] | None = None

    def decode(self, payload: bytes | bytearray) -> float | int | str | None:
        (raw,) = struct.unpack_from(self.format, payload)
        if raw in self.invalid:
            return None
        if self.mapping is not None:
            return self.mapping.get(raw, "unknown")
        if self.divider:
            return raw / self.divider
        return raw


THUNDERBOARD_GATT_SENSOR_CHARS = (
    _SensorCharacteristic(
        ThunderboardSensor.BATTERY_PERCENT, CHARACTERISTIC_BATTERY, "<B"
    ),
    _SensorCharacteristic(
        ThunderboardSensor.POWER_SOURCE,
        CHARACTERISTIC_POWER_SOURCE,
        "<B",
        mapping=POWER_SOURCE_MAP,
    ),
    _SensorCharacteristic(
        ThunderboardSensor.TEMPERATURE_C,
        CHARACTERISTIC_TEMPERATURE,
        "<h",
        divider=100,
        invalid=frozenset({0x7FFF}),
    ),
    _SensorCharacteristic(
        ThunderboardSensor.HUMIDITY_PERCENT,
        CHARACTERISTIC_HUMIDITY,
        "<H",
        divider=100,
        invalid=frozenset({0xFFFF}),
    ),
    _SensorCharacteristic(
        ThunderboardSensor.PRESSURE_PA,
        CHARACTERISTIC_PRESSURE,
        "<I",
        divider=10,
        invalid=frozenset({0xFFFFFFFF}),
    ),
    _SensorCharacteristic(
        ThunderboardSensor.UV_IDX,
        CHARACTERISTIC_UV_IDX,
        "<B",
        invalid=frozenset({0xFF}),
    ),
    _SensorCharacteristic(
        ThunderboardSensor.SOUND_LEVEL_DB,
        CHARACTERISTIC_SOUND_LEVEL,
        "<h",
        divider=100,
        invalid=frozenset({0x7FFF}),
    ),
    _SensorCharacteristic(
        ThunderboardSensor.AMBIENT_LIGHT_LX,
        CHARACTERISTIC_AMBIENT_LIGHT,
        "<I",
        divider=100,
        invalid=frozenset({0xFFFFFFFF}),
    ),
    _SensorCharacteristic(
        ThunderboardSensor.HALL_FIELD_UT,
        CHARACTERISTIC_HALL_FIELD,
        "<i",
        invalid=frozenset({0x7FFFFFFF}),
    ),
    # The CCS811 never reports less than 400 ppm, the firmware starts from 0 before the first measurement
    _SensorCharacteristic(
        ThunderboardSensor.ECO2_PPM,
        CHARACTERISTIC_ECO2,
        "<H",
        invalid=frozenset({0, 0xFFFF}),
    ),
    _SensorCharacteristic(
        ThunderboardSensor.TVOC_PPB,
        CHARACTERISTIC_TVOC,
        "<H",
        invalid=frozenset({0xFFFF}),
    ),
)

THUNDERBOARD_GATT_DEVICE_CHARS = (
    (CHARACTERISTIC_MANUFACTURER_NAME, ThunderboardDeviceInfo.MANUFACTURER_NAME),
    (CHARACTERISTIC_MODEL_NUMBER, ThunderboardDeviceInfo.MODEL_NUMBER),
    (CHARACTERISTIC_HARDWARE_REV, ThunderboardDeviceInfo.HARDWARE_REV),
    (CHARACTERISTIC_FIRMWARE_REV, ThunderboardDeviceInfo.FIRMWARE_REV),
)


def _clean_identity(value: str) -> str | None:
    """Return a device information string, or None for the placeholders of the firmware."""
    value = value.strip("\x00 \r\n\t")
    if not value or set(value) <= set("0."):
        return None
    return value


@dataclasses.dataclass(slots=True)
class _Characteristics:
    """The GATT characteristics found on the connected board."""

    sensors: dict[ThunderboardSensor, BleakGATTCharacteristic] = dataclasses.field(
        default_factory=dict
    )
    identity: dict[ThunderboardDeviceInfo, BleakGATTCharacteristic] = (
        dataclasses.field(default_factory=dict)
    )
    digital_in: BleakGATTCharacteristic | None = None
    digital_out: BleakGATTCharacteristic | None = None
    rgb_leds: BleakGATTCharacteristic | None = None

    @property
    def found(self) -> bool:
        return bool(self.sensors) or any(
            char is not None for char in (self.digital_in, self.digital_out, self.rgb_leds)
        )


class ThunderboardBluetoothDeviceData:
    """Connection and data parser for one Thunderboard.

    A single BLE connection is shared by the reads, the button notifications and the
    LED writes. The board accepts one connection only, so it is kept open by default.
    """

    def __init__(
        self,
        logger: logging.Logger,
        keep_connect: bool = True,
        scan_timeout: float = 30.0,
        max_attempts: int = 3,
    ) -> None:
        super().__init__()
        self.logger = logger
        self._keep_connect = keep_connect
        self._scan_timeout = scan_timeout
        self._max_attempts = max_attempts
        self._lock = asyncio.Lock()
        self._client: BleakClientWithServiceCache | None = None
        self._chars: _Characteristics | None = None
        self._device = ThunderboardDevice()
        self._identity_read = False
        self._button_callback: Callable[[ThunderboardDevice], None] | None = None
        self._connection_callback: Callable[[bool, bool], None] | None = None
        self._reported_connected = False
        self._stats = ThunderboardConnectionStats()
        self._closed = False

    @property
    def device(self) -> ThunderboardDevice:
        return self._device

    @property
    def stats(self) -> ThunderboardConnectionStats:
        """How the connection went since this object exists."""
        return self._stats

    @property
    def is_connected(self) -> bool:
        """True while the board is connected and its characteristics are known."""
        return (
            self._client is not None
            and self._chars is not None
            and self._client.is_connected
        )

    def set_button_callback(
        self, callback: Callable[[ThunderboardDevice], None] | None
    ) -> None:
        """Call back with the device each time a notification updates the buttons."""
        self._button_callback = callback

    def set_connection_callback(
        self, callback: Callable[[bool, bool], None] | None
    ) -> None:
        """Call back with (connected, unexpected) each time the connection state changes.

        unexpected is True when the board or the Bluetooth stack closed the connection,
        and False when this object did.
        """
        self._connection_callback = callback

    async def update_device(
        self,
        ble_device: BLEDevice | None,
        keep_connect: bool | None = None,
        scan_timeout: float | None = None,
        max_attempts: int | None = None,
        rssi: int | None = None,
    ) -> ThunderboardDevice:
        """Connect when needed and read every characteristic of the board.

        ble_device is only used to open a connection, it may be None while connected.
        """
        if keep_connect is None:
            keep_connect = self._keep_connect
        async with self._lock:
            try:
                client, chars = await self._async_connect(
                    ble_device, keep_connect, scan_timeout, max_attempts
                )
                self._device.rssi = rssi
                await self._async_read_all(client, chars)
            except Exception as err:
                self._record_error(err)
                await self._async_drop_client()
                raise
            if not keep_connect:
                await self._async_drop_client()
        return self._device

    async def async_set_lights(
        self,
        ble_device: BLEDevice | None,
        mask: int,
        rgb: tuple[int, int, int],
        brightness: int,
    ) -> ThunderboardLightsState:
        """Show a colour (brightest channel at 255) on exactly the LEDs of the mask."""
        return await self.async_update_lights(
            ble_device,
            on=mask,
            off=RGB_LED_MASK_ALL & ~mask,
            rgb=rgb,
            brightness=brightness,
        )

    async def async_update_lights(
        self,
        ble_device: BLEDevice | None,
        *,
        on: int = 0,
        off: int = 0,
        rgb: tuple[int, int, int] | None = None,
        brightness: int | None = None,
    ) -> ThunderboardLightsState:
        """Switch LEDs on and off, and optionally change the colour they all share.

        on and off are LED mask bits. The new mask is computed from the state of the board
        while holding the lock, so commands for different LEDs that arrive together add up
        instead of overwriting each other. The colour is common to the four LEDs.
        """
        async with self._lock:
            try:
                client, chars = await self._async_connect(
                    ble_device, self._keep_connect, None, None
                )
                if chars.rgb_leds is None:
                    raise ThunderboardError("This board has no RGB LEDs")
                current = self._device.lights or ThunderboardLightsState()
                new_rgb = current.rgb if rgb is None else rgb
                new_brightness = current.brightness if brightness is None else brightness
                if on and not new_brightness:
                    # Black is no colour to switch an LED on with
                    new_brightness = 255
                state = ThunderboardLightsState(
                    mask=(current.mask | on) & ~off & RGB_LED_MASK_ALL,
                    rgb=new_rgb,
                    brightness=new_brightness,
                )
                async with asyncio.timeout(READ_TIMEOUT):
                    await client.write_gatt_char(
                        chars.rgb_leds,
                        encode_rgb_leds(state.mask, state.rgb, state.brightness),
                        response=True,
                    )
            except Exception as err:
                self._record_error(err)
                await self._async_drop_client()
                raise
            self._device.lights = state
            if not self._keep_connect:
                await self._async_drop_client()
        return state

    async def async_disconnect(self) -> None:
        """Close the connection for good, the object cannot connect again."""
        self._closed = True
        await self._async_drop_client()

    def _record_error(self, err: Exception) -> None:
        self._stats.last_error = f"{type(err).__name__}: {err}"
        self._stats.last_error_at = datetime.now(UTC)

    def _set_connection_state(self, connected: bool, *, unexpected: bool = False) -> None:
        """Keep the statistics and tell the listener when the connection state changes.

        An unexpected drop is always reported, also when it happens while the connection
        is still being set up and was never reported as connected.
        """
        if connected == self._reported_connected and not unexpected:
            return
        self._reported_connected = connected
        now = datetime.now(UTC)
        if connected:
            self._stats.connections += 1
            self._stats.last_connected = now
        else:
            self._stats.last_disconnected = now
            if unexpected:
                self._stats.unexpected_disconnects += 1
            # The firmware switches the RGB LEDs off when the connection closes
            if (lights := self._device.lights) is not None:
                self._device.lights = dataclasses.replace(lights, mask=0)
        if self._connection_callback is not None:
            try:
                self._connection_callback(connected, unexpected)
            except Exception:
                self.logger.exception("Error in the Thunderboard connection callback")

    def _on_disconnected(self, client: BleakClientWithServiceCache) -> None:
        if client is not self._client:
            # A connection this object closed itself, or an old one
            return
        self._client = None
        self._chars = None
        self._set_connection_state(False, unexpected=True)
        self.logger.info(
            "Thunderboard %s disconnected unexpectedly (%s so far)",
            client.address,
            self._stats.unexpected_disconnects,
        )

    async def _async_drop_client(self) -> None:
        client, self._client, self._chars = self._client, None, None
        self._set_connection_state(False)
        if client is None:
            return
        try:
            async with asyncio.timeout(DISCONNECT_TIMEOUT):
                await client.disconnect()
        except (*_BLE_ERRORS, TimeoutError) as err:
            self.logger.debug("Error while disconnecting from the Thunderboard: %s", err)

    async def _async_connect(
        self,
        ble_device: BLEDevice | None,
        keep_connect: bool,
        scan_timeout: float | None,
        max_attempts: int | None,
    ) -> tuple[BleakClientWithServiceCache, _Characteristics]:
        client, chars = self._client, self._chars
        if client is not None and chars is not None and client.is_connected:
            return client, chars

        await self._async_drop_client()
        if self._closed:
            raise ThunderboardError("The connection to the Thunderboard was closed")
        if ble_device is None:
            raise ThunderboardError(
                "The Thunderboard is not in range of a Bluetooth adapter or proxy"
            )
        self._device.address = ble_device.address
        timeout = self._scan_timeout if scan_timeout is None else scan_timeout
        attempts = self._max_attempts if max_attempts is None else max_attempts
        try:
            async with asyncio.timeout(timeout):
                client = await establish_connection(
                    BleakClientWithServiceCache,
                    ble_device,
                    ble_device.name or ble_device.address,
                    disconnected_callback=self._on_disconnected,
                    max_attempts=attempts,
                )
        except TimeoutError as err:
            raise ThunderboardError(
                f"Timed out connecting to the Thunderboard {ble_device.address}"
            ) from err
        self._client = client
        if self._closed:
            raise ThunderboardError("The connection to the Thunderboard was closed")

        chars = await self._async_discover(client)
        self._chars = chars
        await self._async_read_identity(client, chars)
        if (
            keep_connect
            and chars.digital_in is not None
            and self._button_callback is not None
        ):
            try:
                await client.start_notify(
                    chars.digital_in, self._on_buttons_notification
                )
            except _BLE_ERRORS as err:
                self.logger.debug("Could not subscribe to the buttons: %s", err)
        if self._client is not client or not client.is_connected:
            # The reads above report a lost connection as a failed read, not as an error
            raise ThunderboardError("The Thunderboard disconnected while connecting")
        self._set_connection_state(True)
        return client, chars

    async def _async_discover(
        self, client: BleakClientWithServiceCache
    ) -> _Characteristics:
        """Find the characteristics by UUID and properties, the handles depend on the backend."""
        index: dict[str, list[BleakGATTCharacteristic]] = {}
        for service in client.services:
            for char in service.characteristics:
                index.setdefault(char.uuid.lower(), []).append(char)

        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug(
                "Thunderboard GATT characteristics: %s",
                ", ".join(
                    f"{char.uuid} (handle {char.handle}, {'/'.join(char.properties)})"
                    for chars in index.values()
                    for char in chars
                ),
            )

        found = _Characteristics()
        for spec in THUNDERBOARD_GATT_SENSOR_CHARS:
            if chars := index.get(spec.uuid):
                found.sensors[spec.key] = chars[0]
        for uuid, key in THUNDERBOARD_GATT_DEVICE_CHARS:
            if chars := index.get(uuid):
                found.identity[key] = chars[0]
        for char in index.get(CHARACTERISTIC_DIGITAL, []):
            if "notify" in char.properties and found.digital_in is None:
                found.digital_in = char
            elif "write" in char.properties and found.digital_out is None:
                found.digital_out = char
        if chars := index.get(CHARACTERISTIC_RGB_LEDS_1):
            found.rgb_leds = chars[0]

        if not found.found:
            # A stale service cache, for example after flashing another firmware, hides the real services
            try:
                await client.clear_cache()
            except _BLE_ERRORS as err:
                self.logger.debug("Could not clear the service cache: %s", err)
            raise ThunderboardError(
                "No Thunderboard characteristic found, is the demo firmware flashed?"
            )

        device = self._device
        device.sensors = {str(key): None for key in found.sensors}
        device.digitals = {}
        if found.digital_in is not None:
            device.digitals.update({str(key): None for key in BUTTON_KEYS})
        if found.digital_out is not None:
            device.digitals.update({str(key): None for key in LED_KEYS})
        if found.rgb_leds is None:
            device.lights = None
        elif device.lights is None:
            device.lights = ThunderboardLightsState()
        return found

    async def _async_read(
        self, client: BleakClientWithServiceCache, char: BleakGATTCharacteristic
    ) -> bytearray | None:
        """Read a characteristic, None when the board refuses, TimeoutError when it hangs."""
        try:
            async with asyncio.timeout(READ_TIMEOUT):
                return await client.read_gatt_char(char)
        except _BLE_ERRORS as err:
            self.logger.debug("Could not read %s: %s", char.uuid, err)
            return None

    async def _async_read_identity(
        self, client: BleakClientWithServiceCache, chars: _Characteristics
    ) -> None:
        if self._identity_read:
            return
        complete = True
        for key, char in chars.identity.items():
            payload = await self._async_read(client, char)
            if payload is None:
                complete = False
                continue
            text = bytes(payload).decode("utf-8", errors="replace")
            setattr(self._device, str(key), _clean_identity(text))
        self._identity_read = complete

    async def _async_read_all(
        self, client: BleakClientWithServiceCache, chars: _Characteristics
    ) -> None:
        """Read every characteristic, one failing read does not discard the others."""
        device = self._device
        reads = 0

        for spec in THUNDERBOARD_GATT_SENSOR_CHARS:
            if (char := chars.sensors.get(spec.key)) is None:
                continue
            value = None
            if (payload := await self._async_read(client, char)) is not None:
                reads += 1
                try:
                    value = spec.decode(payload)
                except struct.error as err:
                    self.logger.debug("Unexpected %s payload %s: %s", spec.key, payload, err)
            device.sensors[str(spec.key)] = value

        for char, keys in ((chars.digital_in, BUTTON_KEYS), (chars.digital_out, LED_KEYS)):
            if char is None:
                continue
            if (payload := await self._async_read(client, char)) is not None:
                reads += 1
                self._apply_digital(payload, keys)

        if chars.rgb_leds is not None:
            if (payload := await self._async_read(client, chars.rgb_leds)) is not None:
                reads += 1
                if state := decode_rgb_leds(payload, device.lights):
                    device.lights = state

        if not reads:
            raise ThunderboardError("Could not read any value from the Thunderboard")
        self.logger.debug("Successfully read %s Thunderboard characteristics", reads)

    def _apply_digital(
        self,
        payload: bytes | bytearray,
        keys: tuple[ThunderboardBinarySensor, ...],
    ) -> None:
        """Each signal takes 2 bits of the payload, the value 1 meaning active."""
        if not payload:
            return
        for index, key in enumerate(keys):
            self._device.digitals[str(key)] = (payload[0] >> (2 * index)) & 0b11 == 1

    def _on_buttons_notification(
        self, _char: BleakGATTCharacteristic, payload: bytearray
    ) -> None:
        self._apply_digital(payload, BUTTON_KEYS)
        self.logger.debug("Received buttons notification: %s", payload)
        if self._button_callback is not None:
            self._button_callback(self._device)
