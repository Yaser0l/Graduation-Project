#include "esp_timer_stubs.h"

static uint64_t s_timer_time_us = 0;

void esp_timer_stub_set_time(uint64_t time_us) { s_timer_time_us = time_us; }
uint64_t esp_timer_stub_get_time(void) { return s_timer_time_us; }
uint64_t esp_timer_get_time(void) { return s_timer_time_us; }
