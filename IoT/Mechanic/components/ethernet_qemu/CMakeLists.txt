# Dependencies are always declared unconditionally because ESP-IDF resolves
# them BEFORE Kconfig is processed. The C source uses #if guards instead.
idf_component_register(
    SRCS "ethernet_qemu.c"
    INCLUDE_DIRS "include"
    PRIV_REQUIRES
        "esp_eth"
        "esp_netif"
        "esp_system"
        "network_events"
)
