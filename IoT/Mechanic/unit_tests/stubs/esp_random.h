#pragma once

#include <stdint.h>

uint32_t esp_random(void);
void esp_random_stub_set_value(uint32_t value);
