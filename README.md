# Description
Custom component that integrates Silicon Labs Thunderboard Sense 2 with the Home Assistant.

# Functions
This helps you to integrate the board sensors with the Home Assistant, compatible with the base software that comes with the board named Bluetooth - SoC Thunderboard Sense 2, which you can update through Simplicity Studio.

Using this integration you can:

- Read sensors values for:
    - Atmospheric pressure
    - Humidity
    - Illuminance
    - Magnetic field strenght
    - Sound pressure
    - Temperature
    - UV Index

- Read buttons and digital IO states
- Power source check if it is USB or battery
- Control RGB led lights of the board

Additionally, you can:

- Customize device polling time
- Keep connection active
    - This might draw battery fast but you can read both the buttons states instantly (using the build-in BLE notification of module)
- Customize timeout and connections attempts
- Add callback to read data from device when there's an change in BLE advertisment
- Set the mininum time between the above mentioned callback trigger

## Images


Integration configuration             |  Sensors from the board
:-------------------------:|:-------------------------:
![Integration settings](images/thunderboard_ha_integration_2.png) |   ![Integration sensors](images/thunderboard_ha_integration.png)