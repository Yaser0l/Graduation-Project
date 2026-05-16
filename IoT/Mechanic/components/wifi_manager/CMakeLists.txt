set (srcs)
set (include_dirs "include")
set (requires)

list(APPEND srcs
    "wifi_manager.c"
    "wifi_store.c"
)

idf_component_register(
    SRCS "${srcs}"
    INCLUDE_DIRS "${include_dirs}"
    REQUIRES
        "esp_event"
    PRIV_REQUIRES
        "vehicle_comms"
        "esp_driver_gpio"
        "esp_system"
        "esp_timer"
        "esp_wifi"
        "nvs_flash"
        "network_events"
)