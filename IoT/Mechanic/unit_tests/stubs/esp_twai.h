#pragma once

#include "esp_twai_types.h"

esp_err_t twai_new_node_onchip(const twai_onchip_node_config_t* cfg, twai_node_handle_t* handle);
esp_err_t twai_node_register_event_callbacks(twai_node_handle_t handle,
                                             const twai_event_callbacks_t* cbs,
                                             void* user_ctx);
esp_err_t twai_node_enable(twai_node_handle_t handle);
esp_err_t twai_node_receive_from_isr(twai_node_handle_t handle, twai_frame_t* frame);

esp_err_t twai_node_transmit(twai_node_handle_t handle, const twai_frame_t* frame, uint32_t timeout);
void twai_node_transmit_wait_all_done(twai_node_handle_t handle, uint32_t timeout);
