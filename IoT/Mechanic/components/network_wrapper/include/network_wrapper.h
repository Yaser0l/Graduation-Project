#pragma once

#include <stdbool.h>

#include "wifi_store.h"

#include "sdkconfig.h"

void network_wrapper_init(const saved_ap_store_t *initial_store);
void network_wrapper_start_task(void);
void network_wrapper_notify_store_changed(const saved_ap_store_t *store);
void network_wrapper_request_connect(void);
bool network_wrapper_is_connected(void);
void network_wrapper_start_config_ap(void);
