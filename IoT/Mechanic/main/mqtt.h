#pragma once

#include <stdbool.h>
#include <stddef.h>

#include "esp_err.h"

#define MQTT_BROKER_URI_MAX_LEN 128

esp_err_t mqtt_module_init(void);
void mqtt_module_start_task(void);
esp_err_t mqtt_module_set_broker_uri(const char *broker_uri);
bool mqtt_module_get_broker_uri(char *out, size_t out_len);
esp_err_t mqtt_module_publish_dtc(const char *vin, const char *payload);