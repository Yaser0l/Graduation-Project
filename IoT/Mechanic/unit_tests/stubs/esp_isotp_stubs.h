#pragma once

#include <stdint.h>

#include "esp_err.h"

void isotp_stub_reset(void);
void isotp_stub_set_new_transport_result(int result);
void isotp_stub_set_send_result(int result);
void isotp_stub_set_receive_result(int result);
int isotp_stub_get_send_calls(void);
int isotp_stub_get_receive_calls(void);
uint32_t isotp_stub_get_last_send_len(void);
const uint8_t* isotp_stub_get_last_send_payload(void);
void isotp_stub_queue_rx(const uint8_t* data, uint32_t len);
int isotp_stub_get_on_can_message_calls(void);
