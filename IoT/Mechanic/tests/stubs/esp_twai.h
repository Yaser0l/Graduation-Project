#ifndef ESP_TWAI_H
#define ESP_TWAI_H

#include <stdbool.h>
#include <stdint.h>

#include "esp_err.h"
#include "esp_twai_types.h"

typedef struct
{
    uint32_t id;
} twai_frame_header_t;

typedef struct
{
    twai_frame_header_t header;
    uint8_t *buffer;
    uint8_t buffer_len;
} twai_frame_t;

typedef struct twai_rx_done_event_data_t
{
    uint32_t dummy;
} twai_rx_done_event_data_t;

typedef struct
{
    bool (*on_rx_done)(twai_node_handle_t handle, const twai_rx_done_event_data_t *edata, void *user_ctx);
} twai_event_callbacks_t;

esp_err_t twai_node_register_event_callbacks(twai_node_handle_t handle,
                                             const twai_event_callbacks_t *cbs,
                                             void *user_ctx);

esp_err_t twai_node_receive_from_isr(twai_node_handle_t handle, twai_frame_t *rx_frame);

esp_err_t twai_node_enable(twai_node_handle_t handle);

#endif
