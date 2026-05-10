#pragma once

#include <stdint.h>

typedef int gpio_num_t;

#define GPIO_NUM_48 48
#define GPIO_MODE_OUTPUT 1

void gpio_reset_pin(gpio_num_t gpio_num);
void gpio_set_direction(gpio_num_t gpio_num, int mode);
void gpio_set_level(gpio_num_t gpio_num, int level);

void gpio_stub_reset(void);
int gpio_stub_get_reset_calls(void);
int gpio_stub_get_set_direction_calls(void);
int gpio_stub_get_set_level_calls(void);
int gpio_stub_get_last_level(void);
