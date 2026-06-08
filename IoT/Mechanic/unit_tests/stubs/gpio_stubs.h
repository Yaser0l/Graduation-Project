#pragma once

#include <stdint.h>

void gpio_stub_reset(void);
int gpio_stub_get_reset_calls(void);
int gpio_stub_get_set_direction_calls(void);
int gpio_stub_get_set_level_calls(void);
uint32_t gpio_stub_get_last_level(void);
