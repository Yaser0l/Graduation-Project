#include "esp_timer.h"

static int64_t s_time_us = 0;

int64_t esp_timer_get_time(void)
{
    return s_time_us;
}

void esp_timer_stub_set_time(int64_t time_us)
{
    s_time_us = time_us;
}
