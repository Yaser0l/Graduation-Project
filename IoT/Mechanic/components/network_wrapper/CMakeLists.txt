set(srcs)
set(include_dirs "include")
set(requires)

if(CONFIG_ESP_WIFI_ENABLED)
    list(APPEND requires "wifi_manager")
endif()

list(APPEND srcs "network_wrapper.c" "network_events.c")

list(APPEND requires "esp_event")


idf_component_register(
    SRCS "${srcs}"
    INCLUDE_DIRS "${include_dirs}"
    REQUIRES
        "${requires}"
)