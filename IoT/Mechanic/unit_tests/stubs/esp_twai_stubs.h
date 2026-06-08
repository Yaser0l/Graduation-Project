#pragma once

#include "esp_twai_types.h"

void twai_stub_reset(void);
void twai_stub_set_results(int32_t new_node_ret, int32_t register_ret,
                           int32_t enable_ret, int32_t receive_ret);
void twai_stub_set_next_frame(uint32_t id, const uint8_t* data, uint8_t len);
const twai_event_callbacks_t* twai_stub_get_callbacks(void);
twai_node_handle_t twai_stub_get_handle(void);
int twai_stub_get_new_node_calls(void);
int twai_stub_get_register_calls(void);
int twai_stub_get_enable_calls(void);
int twai_stub_get_receive_calls(void);
int twai_stub_get_transmit_calls(void);
