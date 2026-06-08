#include "esp_random_stubs.h"

static uint32_t s_random_value = 0x12345678u;

void esp_random_stub_set_value(uint32_t value) { s_random_value = value; }

uint32_t esp_random(void) { return s_random_value; }
