set(srcs)
set(include_dirs "include")
set(requires)
set(priv_requires)

if(CONFIG_WIFI_CONNECT)
    list(APPEND priv_requires "wifi_manager")
endif()

list(APPEND srcs "network_wrapper.c" "network_events.c")

list(APPEND requires "esp_event")


idf_component_register(
    SRCS "${srcs}"
    INCLUDE_DIRS "${include_dirs}"
    REQUIRES
        "${requires}"
    PRIV_REQUIRES
        "${priv_requires}"
)