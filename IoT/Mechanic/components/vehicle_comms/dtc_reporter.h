#pragma once

#include "esp_err.h"
#include <stdint.h>

esp_err_t dtc_reporter_init(void);
void dtc_reporter_start_task(void);

// New function to accept frames routed from the CAN module
void dtc_reporter_feed_frame(uint32_t id, const uint8_t *data, uint8_t len);