set(srcs)
set(include_dirs "include")
set(requires)
set(priv_requires)

if(CONFIG_WIFI_CONNECT)
    list(APPEND priv_requires "wifi_manager")
endif()

if(CONFIG_ETHERNET_QEMU_CONNECT)
    list(APPEND priv_requires "ethernet_qemu")
endif()

list(APPEND srcs "network_wrapper.c")


idf_component_register(
    SRCS "${srcs}"
    INCLUDE_DIRS "${include_dirs}"
    REQUIRES
        "${requires}"
    PRIV_REQUIRES
        "${priv_requires}"
)