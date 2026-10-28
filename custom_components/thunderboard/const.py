"""Constants for the Thunderboard integration."""

DOMAIN = "thunderboard"
# The boards advertise as "Thunderboard #12345"
NAME_PREFIX = "Thunderboard"

DEFAULT_SCAN_INTERVAL = 60
MFCT_ID = 71
MAGNETIC_STRENGTH_UNIT = "\u00b5T"
SCAN_INTERVAL_KEY = "scan_interval"
KEEP_DEVICE_CONNECTED_KEY = "keep_device_connected"
SCAN_TIMEOUT_KEY = "scan_timeout"
MAX_CONNECTION_ATTEMPTS_KEY = "max_connection_attempts"
ADD_BLE_CALLBACK_KEY = "add_ble_callback"
EVENT_DEBOUNCE_TIME_KEY = "event_debounce_time"
ADD_BLE_CALLBACK = True
KEEP_DEVICE_CONNECTED = True
SCAN_TIMEOUT = 30
MAX_CONNECTION_ATTEMPTS = 3
EVENT_DEBOUNCE_TIME = 10

SCAN_INTERVAL_RANGE = (5, 3600)
SCAN_TIMEOUT_RANGE = (5, 120)
CONNECTION_ATTEMPTS_RANGE = (1, 10)
EVENT_DEBOUNCE_TIME_RANGE = (0, 3600)
