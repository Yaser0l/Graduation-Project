set (srcs)
set (include_dirs "include")
set (requires)

list(APPEND srcs
    "local_mqtt.c"
)

idf_component_register(
    SRCS "${srcs}"
    INCLUDE_DIRS "${include_dirs}"
    REQUIRES
        "esp_event"
    PRIV_REQUIRES
        "vehicle_comms"
        "espressif__mqtt"
        "esp_timer"
        "nvs_flash"
        "network_events"
)