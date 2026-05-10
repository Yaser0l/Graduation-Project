#pragma once

#include <stdint.h>

#include "esp_err.h"
#include "esp_twai_types.h"

typedef struct esp_isotp_stub *esp_isotp_handle_t;

typedef struct
{
    uint32_t tx_id;
    uint32_t rx_id;
    uint16_t tx_buffer_size;
    uint16_t rx_buffer_size;
} esp_isotp_config_t;

esp_err_t esp_isotp_new_transport(twai_node_handle_t node,
                                 const esp_isotp_config_t *config,
                                 esp_isotp_handle_t *out_handle);

esp_err_t esp_isotp_send(esp_isotp_handle_t handle, const uint8_t *data, uint32_t len);

esp_err_t esp_isotp_receive(esp_isotp_handle_t handle, uint8_t *data, uint32_t max_len, uint32_t *out_len);

void esp_isotp_poll(esp_isotp_handle_t handle);

void isotp_stub_reset(void);
void isotp_stub_set_send_result(esp_err_t result);
void isotp_stub_set_receive_result(esp_err_t result);
int isotp_stub_get_send_calls(void);
uint32_t isotp_stub_get_last_send_len(void);
const uint8_t *isotp_stub_get_last_send_payload(void);
int isotp_stub_queue_rx(const uint8_t *data, uint32_t len);
