#include "network_wrapper.h"

#include "sdkconfig.h"

#if CONFIG_WIFI_CONNECT && !CONFIG_ETHERNET_QEMU_CONNECT

void wifi_manager_init(const struct saved_ap_store *initial_store);
void wifi_manager_start_task(void);
void wifi_manager_notify_store_changed(const struct saved_ap_store *store);
void wifi_manager_request_connect(void);
bool wifi_manager_is_connected(void);
void wifi_manager_start_config_ap(void);

void network_wrapper_init(const struct saved_ap_store *initial_store) {
  wifi_manager_init(initial_store);
}

void network_wrapper_start_task(void) { wifi_manager_start_task(); }

void network_wrapper_notify_store_changed(const struct saved_ap_store *store) {
  wifi_manager_notify_store_changed(store);
}

void network_wrapper_request_connect(void) { wifi_manager_request_connect(); }

bool network_wrapper_is_connected(void) { return wifi_manager_is_connected(); }

void network_wrapper_start_config_ap(void) { wifi_manager_start_config_ap(); }

#elif CONFIG_ETHERNET_QEMU_CONNECT && !CONFIG_WIFI_CONNECT

#include "esp_log.h"

static const char *TAG = "network_wrapper";

void network_wrapper_init(const struct saved_ap_store *initial_store) {
  (void)initial_store;
  ESP_LOGW(TAG, "Ethernet QEMU backend is not implemented");
}

void network_wrapper_start_task(void) {
  ESP_LOGW(TAG, "Ethernet QEMU backend is not implemented");
}

void network_wrapper_notify_store_changed(const struct saved_ap_store *store) {
  (void)store;
  ESP_LOGW(TAG, "Ethernet QEMU backend is not implemented");
}

void network_wrapper_request_connect(void) {
  ESP_LOGW(TAG, "Ethernet QEMU backend is not implemented");
}

bool network_wrapper_is_connected(void) { return false; }

void network_wrapper_start_config_ap(void) {
  ESP_LOGW(TAG, "Ethernet QEMU backend is not implemented");
}

#else
#error Please select one (and only one) WiFi or QEMU Ethernet driver in menuconfig
#endif
