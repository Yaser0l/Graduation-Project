#pragma once

#include <stdint.h>

int64_t esp_timer_get_time(void);
void esp_timer_stub_set_time(int64_t time_us);
