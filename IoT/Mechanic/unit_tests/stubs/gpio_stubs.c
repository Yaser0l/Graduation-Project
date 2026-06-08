#include "gpio_stubs.h"

#include "driver/gpio.h"

static int s_reset_calls = 0;
static int s_set_direction_calls = 0;
static int s_set_level_calls = 0;
static uint32_t s_last_level = 0;

void gpio_stub_reset(void) {
    s_reset_calls = 0;
    s_set_direction_calls = 0;
    s_set_level_calls = 0;
    s_last_level = 0;
}

int gpio_stub_get_reset_calls(void) { return s_reset_calls; }
int gpio_stub_get_set_direction_calls(void) { return s_set_direction_calls; }
int gpio_stub_get_set_level_calls(void) { return s_set_level_calls; }
uint32_t gpio_stub_get_last_level(void) { return s_last_level; }

esp_err_t gpio_reset_pin(int gpio_num) {
    (void)gpio_num;
    s_reset_calls++;
    return 0;
}

esp_err_t gpio_set_direction(int gpio_num, int mode) {
    (void)gpio_num; (void)mode;
    s_set_direction_calls++;
    return 0;
}

esp_err_t gpio_set_level(int gpio_num, uint32_t level) {
    (void)gpio_num;
    s_last_level = level;
    s_set_level_calls++;
    return 0;
}
