cmake_minimum_required(VERSION 3.10)
project(uart_interface C)

# Find required packages
find_package(SDL2 REQUIRED)  # We'll use SDL2 for simulation
find_package(LVGL REQUIRED)  # You'll need to install LVGL

# Include directories
include_directories(${CMAKE_SOURCE_DIR}/include)
include_directories(${LVGL_INCLUDE_DIRS})

# Add source files
add_executable(uart_interface
    src/main.c
    src/uart_interface.c
    src/display_driver.c
)

# Link libraries
target_link_libraries(uart_interface
    ${SDL2_LIBRARIES}
    ${LVGL_LIBRARIES}
)