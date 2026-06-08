#pragma once

#include <stdint.h>

void esp_timer_stub_set_time(uint64_t time_us);
uint64_t esp_timer_stub_get_time(void);
