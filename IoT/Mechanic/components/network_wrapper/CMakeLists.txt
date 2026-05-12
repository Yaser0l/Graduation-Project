set(srcs)
set(include_dirs "include")
set(requires)
list(APPEND requires "wifi_manager")

if(CONFIG_ETHERNET_QEMU_CONNECT)
    list(APPEND requires "ethernet_qemu")
endif()

list(APPEND srcs "network_wrapper.c")


idf_component_register(
    SRCS "${srcs}"
    INCLUDE_DIRS "${include_dirs}"
    REQUIRES
        "${requires}"
)