#pragma once

#include "esp_err.h"
#include <stdint.h>

#define GPIO_MODE_OUTPUT 2

esp_err_t gpio_reset_pin(int gpio_num);
esp_err_t gpio_set_direction(int gpio_num, int mode);
esp_err_t gpio_set_level(int gpio_num, uint32_t level);
