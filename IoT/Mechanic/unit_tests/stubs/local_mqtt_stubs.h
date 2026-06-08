#pragma once

#include <stdint.h>

#include "esp_err.h"

void mqtt_stub_reset(void);
int mqtt_stub_get_set_vin_calls(void);
int mqtt_stub_get_publish_calls(void);
const char* mqtt_stub_get_last_vin(void);
const char* mqtt_stub_get_last_payload(void);
void mqtt_stub_set_publish_result(esp_err_t ret);
