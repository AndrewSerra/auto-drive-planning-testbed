
cmake_minimum_required(VERSION 3.23)

project(PlanningTestbed LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

if(NOT CMAKE_BUILD_TYPE AND NOT CMAKE_CONFIGURATION_TYPES)
    set(CMAKE_BUILD_TYPE Release CACHE STRING "Build type" FORCE)
endif()

set(CMAKE_RUNTIME_OUTPUT_DIRECTORY "${PROJECT_BINARY_DIR}/bin")
set(CMAKE_LIBRARY_OUTPUT_DIRECTORY "${PROJECT_BINARY_DIR}/lib")

find_package(OpenCV REQUIRED)

add_executable(testbed
    main.cpp
)

target_link_libraries(
    testbed
    PRIVATE
    ${OpenCV_LIBS}
)

set_target_properties(testbed PROPERTIES
    OUTPUT_NAME "testbed$<$<CONFIG:Debug>:-debug>"
)

