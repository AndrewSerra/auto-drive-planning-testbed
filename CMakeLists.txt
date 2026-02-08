
cmake_minimum_required(VERSION 3.23)

project(PlanningTestbed LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

set(CMAKE_RUNTIME_OUTPUT_DIRECTORY "${PROJECT_BINARY_DIR}/bin")
set(CMAKE_LIBRARY_OUTPUT_DIRECTORY "${PROJECT_BINARY_DIR}/lib")

find_package(OpenCV REQUIRED)

option(DRAW_APRILTAG "Draw April Tag detected areas on image" OFF)

add_executable(testbed
    main.cpp
)

add_subdirectory(image_processing/)

target_link_libraries(testbed
    PRIVATE
    image_transform
)

