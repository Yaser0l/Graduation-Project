#pragma once

#include "esp_err.h"
#include <stdbool.h>
#include <stdint.h>

typedef void* twai_node_handle_t;

typedef struct {
    uint32_t val;
    bool ack_err;
    bool stuff_err;
} twai_error_flags_t;

typedef enum {
    TWAI_ERROR_BUS_OFF = 3,
} twai_state_t;

typedef struct {
    uint32_t id;
    bool ide;
    bool rtr;
    uint8_t dlc;
} twai_frame_header_t;

typedef struct {
    twai_frame_header_t header;
    uint8_t* buffer;
    uint8_t buffer_len;
} twai_frame_t;

typedef struct {
    twai_state_t old_sta;
    twai_state_t new_sta;
} twai_state_change_event_data_t;

typedef struct {
    twai_error_flags_t err_flags;
} twai_error_event_data_t;

typedef struct {
    twai_frame_t rx_frame;
} twai_rx_done_event_data_t;

typedef struct twai_event_callbacks_t {
    bool (*on_rx_done)(twai_node_handle_t handle,
                       const twai_rx_done_event_data_t* edata,
                       void* user_ctx);
    bool (*on_state_change)(twai_node_handle_t handle,
                            const twai_state_change_event_data_t* edata,
                            void* user_ctx);
    bool (*on_error)(twai_node_handle_t handle,
                     const twai_error_event_data_t* edata,
                     void* user_ctx);
} twai_event_callbacks_t;

typedef struct {
    int tx;
    int rx;
} twai_io_config_t;

typedef struct {
    int bitrate;
} twai_bit_timing_t;

typedef struct {
    bool enable_self_test;
} twai_node_flags_t;

typedef struct {
    twai_io_config_t io_cfg;
    twai_bit_timing_t bit_timing;
    int tx_queue_depth;
    twai_node_flags_t flags;
} twai_onchip_node_config_t;

typedef struct {
    uint32_t id;
    uint32_t mask;
    bool is_ext;
} twai_mask_filter_config_t;

void twai_node_config_mask_filter(twai_node_handle_t h, int idx, const void* cfg);
