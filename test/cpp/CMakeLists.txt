cmake_minimum_required(VERSION 3.16)
project(OpenpilotUITest)

# Set C++ standard
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Find Qt5
find_package(Qt5 REQUIRED COMPONENTS Core Widgets Network Test)

# Enable Qt MOC
set(CMAKE_AUTOMOC ON)

# Add include directories
include_directories(${CMAKE_CURRENT_SOURCE_DIR})
include_directories(${CMAKE_CURRENT_SOURCE_DIR}/../..)

# Source files
set(SOURCES
    simple_ui_test.cc
    ../../frame_streamer.cc
    ../../touch_injector.cc
)

set(HEADERS
    ../../frame_streamer.h
    ../../touch_injector.h
)

# Create executable
add_executable(openpilot_ui_test ${SOURCES} ${HEADERS})

# Link Qt libraries
target_link_libraries(openpilot_ui_test
    Qt5::Core
    Qt5::Widgets
    Qt5::Network
    rt  # For shared memory functions
)

# Compiler flags
target_compile_options(openpilot_ui_test PRIVATE
    -Wall
    -Wextra
    -g
    -O2
)

# Unit tests executable
add_executable(unit_tests unit_tests.cc ../../frame_streamer.cc ../../touch_injector.cc)
target_link_libraries(unit_tests
    Qt5::Core
    Qt5::Widgets
    Qt5::Network
    Qt5::Test
    rt
)

# Custom target to run tests
add_custom_target(run_tests
    COMMAND openpilot_ui_test
    DEPENDS openpilot_ui_test
    WORKING_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}
    COMMENT "Running OpenPilot UI interactive tests"
)

add_custom_target(run_unit_tests
    COMMAND unit_tests
    DEPENDS unit_tests
    WORKING_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}
    COMMENT "Running OpenPilot UI unit tests"
)