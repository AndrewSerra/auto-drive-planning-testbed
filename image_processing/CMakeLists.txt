
add_library(
    image_transform
    SHARED
    image_transform.cpp
    boundary_detection.cpp
)

target_compile_definitions(
    image_transform
    PRIVATE
    VISUALIZE_TAGS=$<BOOL:${DRAW_APRILTAG}>
)

target_include_directories(
    image_transform
    PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}
)

target_link_libraries(
    image_transform
    PUBLIC
    ${OpenCV_LIBS}
)
