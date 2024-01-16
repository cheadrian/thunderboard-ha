# Description
Custom component that integrates Silicon Labs Thunderboard Sense 2 with the Home Assistant. This is a demonstration of how you can integrate the device, and it's tested in practice.

This integration is compatible with the board demo software that you can update using Simplicity Studio - *Bluetooth — SoC Thunderboard Sense 2*.

Check out the alternative [Thunderboard Sense v2 BTHome v2 protocol integration](https://github.com/cheadrian/thunderboard_bthome_v2).

You can read the Medium article about how I've brought this integration up [here (no paywall link)](https://che-adrian.medium.com/bringing-a-new-ble-device-to-the-home-assistant-silabs-thunderboard-example-1f0d6094c84b?sk=cdbbac98afde4fe459c585f03fc132c1).

If you plan to optimize the demo software in order to run longer on CR2032 battery, then there's [another article (no paywall link)](https://che-adrian.medium.com/optimize-energy-consumption-for-silabs-thunderboard-on-battery-0bc573b6b453?sk=6427c6423fb92c98742e6ba5092267bd).

# Installation
You need to manually copy the thunderboard directory from custom_components into the `<config>/custom_components/` directory (so you end up with `<config>/custom_components/thunderboard`).

# Debugging
Into your configuration.yaml

    logger:
      default: warning
      logs:
        custom_components.thunderboard: debug

# Functions
This helps you to integrate the board sensors with the Home Assistant, compatible with the base software that comes with the board named Bluetooth - SoC Thunderboard Sense 2, which you can update through Simplicity Studio.

Using this integration, you can:

- Read sensors values for:
    - Atmospheric pressure
    - Humidity
    - Illuminance
    - Magnetic field strength
    - Sound pressure
    - Temperature
    - UV Index

- Read buttons and digital IO states
- Power source check if it is USB or battery
- Control RGB LED lights of the board

Additionally, you can:

- Customize device polling time
- Keep connection active
    - This might draw battery fast, but you can read both the buttons states instantly (using the built-in BLE notification of module)
- Customize timeout and connections attempts
- Add callback to read data from device when there's a change in BLE advertisement
- Set the minimum time between the above-mentioned callback trigger

## Images


Integration configuration             |  Sensors from the board
:-------------------------:|:-------------------------:
![Integration settings](images/thunderboard_ha_integration_2.png) |   ![Integration sensors](images/thunderboard_ha_integration.png)
