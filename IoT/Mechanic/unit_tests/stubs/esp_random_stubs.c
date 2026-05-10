#include "esp_random.h"

static uint32_t s_rand_value = 0x12345678u;

uint32_t esp_random(void)
{
    return s_rand_value;
}

void esp_random_stub_set_value(uint32_t value)
{
    s_rand_value = value;
}
