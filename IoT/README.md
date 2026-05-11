# SayyarTech IoT

This folder contains the IoT modules used to build and test the device. The firmware targets an ESP32-S3 microcontroller, uses ESP-IDF as the build system, and relies on Unity for embedded tests.

## Modules

- Mechanic/ - ESP-IDF firmware project (CMakeLists, components, main, sdkconfig, unit_tests).
- cantools_env/ - Python tooling workspace for CAN decoding and experiments (pyproject.toml, main.py).
- cars/ - Vehicle-specific CAN resources (DBC/C/H), currently Toyota Prius 2010.

## Setup (Firmware)

1. Install the VS Code ESP-IDF extension:
   https://docs.espressif.com/projects/esp-idf/en/v4.2.1/esp32/get-started/vscode-setup.html
2. Open the ESP-IDF Installation Manager from the Command Palette:
   `>ESP-IDF: Open ESP-IDF Installation Manager`
3. Choose Custom Installation and include optional additions.
4. Use the ESP-IDF extension to build, flash, and monitor the ESP32-S3 device from the Mechanic/ project.
