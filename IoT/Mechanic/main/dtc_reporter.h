#pragma once

#include "esp_err.h"
#include "esp_twai_types.h"

esp_err_t dtc_reporter_init(void);
void dtc_reporter_start_task(void);
void dtc_reporter_can_rx_isr(const twai_frame_t *rx_frame);
