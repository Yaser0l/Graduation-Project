#pragma once

#include <stdbool.h>

struct saved_ap_store;

void ethernet_qemu_init(const struct saved_ap_store *initial_store);
void ethernet_qemu_start_task(void);
void ethernet_qemu_notify_store_changed(const struct saved_ap_store *store);
void ethernet_qemu_request_connect(void);
bool ethernet_qemu_is_connected(void);
void ethernet_qemu_start_config_ap(void);
