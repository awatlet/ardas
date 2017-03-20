# arDAS
[![Build Status](https://travis-ci.org/UMONS-GFA/ardas.svg?branch=master)](https://travis-ci.org/UMONS-GFA/ardas)
[![Doc Latest](https://img.shields.io/badge/docs-latest-brightgreen.svg?style=flat)](http://ardas.readthedocs.io/en/latest/)
The arDAS project is an attempt to improve **nanoDAS** acquisition systems.

Features :
* Based on [Arduino] (http://arduino.cc/)
* 4 channels
* compatible with DAS network
* CRC control (raspardas_mode)


### Required libraries

* [Adafruit RTClib] (https://github.com/adafruit/RTClib) >= 1.0.0

## How to use it with Clion

Install required packages

    sudo apt-get install arduino cmake gcc-avr binutils-avr avr-libc avrdude
    
Create a directory for your Clion project

Put the [arduino cmake directory](https://github.com/queezythegreat/arduino-cmake) inside this directory

Create a CMakeLists.txt and modify it to your needs

    cmake_minimum_required(VERSION 2.8)
    set(CMAKE_TOOLCHAIN_FILE ${CMAKE_SOURCE_DIR}/cmake/ArduinoToolchain.cmake)
    set(PROJECT_NAME ardas)
    project(${PROJECT_NAME})
    link_directories(${CMAKE_CURRENT_SOURCE_DIR}/libraries)
    set(${CMAKE_PROJECT_NAME}_SKETCH ardas.ino)
    generate_arduino_firmware(${CMAKE_PROJECT_NAME}
        SERIAL cutecom @SERIAL_PORT@ -b 9600 -l
        PORT  /dev/ttyACM0
        BOARD uno
    )

Copy the .ino file inside this directory and open it with Clion

Edit the configuration

![](https://github.com/UMONS-GFA/ardas/blob/master/arduino-clion-config.png)

