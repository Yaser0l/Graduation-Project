#pragma once

#include <stdbool.h>

struct saved_ap_store;

void network_wrapper_init(const struct saved_ap_store *initial_store);
void network_wrapper_start_task(void);
void network_wrapper_notify_store_changed(const struct saved_ap_store *store);
void network_wrapper_request_connect(void);
bool network_wrapper_is_connected(void);
void network_wrapper_start_config_ap(void);
