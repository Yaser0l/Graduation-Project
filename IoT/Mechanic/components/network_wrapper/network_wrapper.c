#if CONFIG_WIFI_CONNECT && !CONFIG_ETHERNET_QEMU_CONNECT
#include "wifi_manager.h"
#elif CONFIG_ETHERNET_QEMU_CONNECT && !CONFIG_WIFI_CONNECT
#include "ethernet_qemu.h"
#else
#error Please select one (and only one) WiFi STA or QEMU Ethernet driver in menuconfig
#endif
