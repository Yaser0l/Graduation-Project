#pragma once

#include <stdint.h>

#include "esp_wifi.h"

void esp_wifi_stub_reset(void);
int esp_wifi_stub_get_set_mode_calls(void);
int esp_wifi_stub_get_set_config_calls(void);
int esp_wifi_stub_get_connect_calls(void);
int esp_wifi_stub_get_disconnect_calls(void);
wifi_mode_t esp_wifi_stub_get_last_mode(void);
