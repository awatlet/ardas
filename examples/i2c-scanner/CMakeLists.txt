cmake_minimum_required(VERSION 2.8)
set(CMAKE_TOOLCHAIN_FILE ${CMAKE_SOURCE_DIR}/cmake/ArduinoToolchain.cmake)
set(PROJECT_NAME i2c-scanner)
project(${PROJECT_NAME})

link_directories(${CMAKE_CURRENT_SOURCE_DIR}/libraries)


set(${CMAKE_PROJECT_NAME}_SKETCH i2c-scanner.ino)

generate_arduino_firmware(${CMAKE_PROJECT_NAME}
        SERIAL picocom @SERIAL_PORT@ -b 57600 -l
        PORT  /dev/ttyACM0
        BOARD uno
)

