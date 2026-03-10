idf_component_register(
    SRCS "main.c"
    INCLUDE_DIRS "."
    REQUIRES
    driver
    PRIV_REQUIRES
    esp_driver_gptimer
    esp_wifi
    nvs_flash
)
