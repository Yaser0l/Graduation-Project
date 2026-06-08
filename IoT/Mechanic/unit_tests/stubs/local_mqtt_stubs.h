#pragma once

#include <stdint.h>

void mqtt_stub_reset(void);
int mqtt_stub_get_set_vin_calls(void);
int mqtt_stub_get_publish_calls(void);
const char* mqtt_stub_get_last_vin(void);
const char* mqtt_stub_get_last_payload(void);
