#include "driver/gpio.h"

static int s_reset_calls = 0;
static int s_set_direction_calls = 0;
static int s_set_level_calls = 0;
static int s_last_level = 0;

void gpio_stub_reset(void)
{
    s_reset_calls = 0;
    s_set_direction_calls = 0;
    s_set_level_calls = 0;
    s_last_level = 0;
}

int gpio_stub_get_reset_calls(void)
{
    return s_reset_calls;
}

int gpio_stub_get_set_direction_calls(void)
{
    return s_set_direction_calls;
}

int gpio_stub_get_set_level_calls(void)
{
    return s_set_level_calls;
}

int gpio_stub_get_last_level(void)
{
    return s_last_level;
}

void gpio_reset_pin(gpio_num_t gpio_num)
{
    (void)gpio_num;
    s_reset_calls++;
}

void gpio_set_direction(gpio_num_t gpio_num, int mode)
{
    (void)gpio_num;
    (void)mode;
    s_set_direction_calls++;
}

void gpio_set_level(gpio_num_t gpio_num, int level)
{
    (void)gpio_num;
    s_last_level = level;
    s_set_level_calls++;
}
