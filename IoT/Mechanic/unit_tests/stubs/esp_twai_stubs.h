#pragma once

#include <stdbool.h>
#include <stdint.h>

#include "esp_err.h"
#include "esp_twai.h"
#include "esp_twai_onchip.h"

typedef struct
{
    uint32_t id;
    uint8_t data[8];
    uint8_t len;
    bool valid;
} twai_stub_frame_t;

void twai_stub_reset(void);
void twai_stub_set_results(esp_err_t new_node_result,
                           esp_err_t register_result,
                           esp_err_t enable_result,
                           esp_err_t receive_result);
void twai_stub_set_next_frame(uint32_t id, const uint8_t *data, uint8_t len);
int twai_stub_get_new_node_calls(void);
int twai_stub_get_register_calls(void);
int twai_stub_get_enable_calls(void);
const twai_event_callbacks_t *twai_stub_get_callbacks(void);
twai_node_handle_t twai_stub_get_handle(void);
