#include "esp_twai.h"
#include "esp_twai_onchip.h"
#include "esp_log.h"
#include <toyota_prius_2010_pt.h>
twai_node_handle_t node_hdl = NULL;
twai_onchip_node_config_t node_config = {
    .io_cfg.tx = 43,              // TWAI TX GPIO pin
    .io_cfg.rx = 44,              // TWAI RX GPIO pin
    .bit_timing.bitrate = 200000, // 200 kbps bitrate
    .tx_queue_depth = 5,          // Transmit queue depth set to 5
};
// Create a new TWAI controller driver instance
ESP_ERROR_CHECK(twai_new_node_onchip(&node_config, &node_hdl));
// Start the TWAI controller
ESP_ERROR_CHECK(twai_node_enable(node_hdl));
