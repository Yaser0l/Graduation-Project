#ifndef ESP_TWAI_ONCHIP_H
#define ESP_TWAI_ONCHIP_H

#include <stdint.h>

#include "esp_err.h"
#include "esp_twai_types.h"

typedef struct
{
    struct
    {
        int tx;
        int rx;
    } io_cfg;
    struct
    {
        uint32_t bitrate;
    } bit_timing;
    uint32_t tx_queue_depth;
} twai_onchip_node_config_t;

esp_err_t twai_new_node_onchip(const twai_onchip_node_config_t *config, twai_node_handle_t *out_handle);

#endif
