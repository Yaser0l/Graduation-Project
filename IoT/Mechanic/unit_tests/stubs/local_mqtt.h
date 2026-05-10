#pragma once

#include "esp_err.h"

void mqtt_module_set_vin(const char *vin);
esp_err_t mqtt_module_publish_dtc(const char *vin, const char *payload);

void mqtt_stub_reset(void);
int mqtt_stub_get_set_vin_calls(void);
int mqtt_stub_get_publish_calls(void);
const char *mqtt_stub_get_last_vin(void);
const char *mqtt_stub_get_last_payload(void);
