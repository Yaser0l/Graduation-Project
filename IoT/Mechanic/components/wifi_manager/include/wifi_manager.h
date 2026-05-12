#pragma once

#include <stdbool.h>

#include "wifi_store.h"

void wifi_manager_init(const saved_ap_store_t *initial_store);
void wifi_manager_start_task(void);
void wifi_manager_notify_store_changed(const saved_ap_store_t *store);
void wifi_manager_request_connect(void);
bool wifi_manager_is_connected(void);
void wifi_manager_start_config_ap(void);
