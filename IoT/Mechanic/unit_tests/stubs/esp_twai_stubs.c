#include "esp_twai_stubs.h"

#include "esp_twai.h"
#include <stdbool.h>
#include <string.h>

static int32_t s_twai_new_node_ret = 0;
static int32_t s_twai_register_ret = 0;
static int32_t s_twai_enable_ret = 0;
static int32_t s_twai_receive_ret = 0;
static int s_receive_ok_remaining = -1;

static int s_new_node_calls = 0;
static int s_register_calls = 0;
static int s_enable_calls = 0;
static int s_receive_calls = 0;
static int s_transmit_calls = 0;

static twai_node_handle_t s_twai_handle = (twai_node_handle_t)0x1;
static twai_event_callbacks_t s_callbacks;
static bool s_callbacks_registered = false;

static uint32_t s_next_frame_id = 0;
static uint8_t s_next_frame_data[8] = {0};
static uint8_t s_next_frame_len = 0;

void twai_stub_reset(void) {
    s_twai_new_node_ret = 0;
    s_twai_register_ret = 0;
    s_twai_enable_ret = 0;
    s_twai_receive_ret = 0;
    s_receive_ok_remaining = -1;
    s_new_node_calls = 0;
    s_register_calls = 0;
    s_enable_calls = 0;
    s_receive_calls = 0;
    s_transmit_calls = 0;
    s_twai_handle = (twai_node_handle_t)0x1;
    memset(&s_callbacks, 0, sizeof(s_callbacks));
    s_callbacks_registered = false;
    s_next_frame_id = 0;
    memset(s_next_frame_data, 0, sizeof(s_next_frame_data));
    s_next_frame_len = 0;
}

void twai_stub_set_receive_ok_limit(int limit) { s_receive_ok_remaining = limit; }

void twai_stub_set_results(int32_t new_node_ret, int32_t register_ret,
                           int32_t enable_ret, int32_t receive_ret) {
    s_twai_new_node_ret = new_node_ret;
    s_twai_register_ret = register_ret;
    s_twai_enable_ret = enable_ret;
    s_twai_receive_ret = receive_ret;
}

void twai_stub_set_next_frame(uint32_t id, const uint8_t* data, uint8_t len) {
    s_next_frame_id = id;
    memcpy(s_next_frame_data, data, len > 8 ? 8 : len);
    s_next_frame_len = len;
}

const twai_event_callbacks_t* twai_stub_get_callbacks(void) {
    return s_callbacks_registered ? &s_callbacks : NULL;
}

twai_node_handle_t twai_stub_get_handle(void) { return s_twai_handle; }
int twai_stub_get_new_node_calls(void) { return s_new_node_calls; }
int twai_stub_get_register_calls(void) { return s_register_calls; }
int twai_stub_get_enable_calls(void) { return s_enable_calls; }
int twai_stub_get_receive_calls(void) { return s_receive_calls; }
int twai_stub_get_transmit_calls(void) { return s_transmit_calls; }

esp_err_t twai_new_node_onchip(const twai_onchip_node_config_t* cfg,
                                twai_node_handle_t* handle) {
    (void)cfg;
    s_new_node_calls++;
    if (handle) *handle = s_twai_handle;
    return s_twai_new_node_ret;
}

void twai_node_config_mask_filter(twai_node_handle_t h, int idx, const void* cfg) {
    (void)h; (void)idx; (void)cfg;
}

esp_err_t twai_node_register_event_callbacks(twai_node_handle_t handle,
                                              const twai_event_callbacks_t* cbs,
                                              void* user_ctx) {
    (void)handle; (void)user_ctx;
    s_register_calls++;
    if (cbs) {
        memcpy(&s_callbacks, cbs, sizeof(s_callbacks));
        s_callbacks_registered = true;
    }
    return s_twai_register_ret;
}

esp_err_t twai_node_enable(twai_node_handle_t handle) {
    (void)handle;
    s_enable_calls++;
    return s_twai_enable_ret;
}

esp_err_t twai_node_receive_from_isr(twai_node_handle_t handle, twai_frame_t* frame) {
    (void)handle;
    if (s_receive_ok_remaining == 0) {
        return ESP_FAIL;
    }
    if (s_receive_ok_remaining > 0) {
        s_receive_ok_remaining--;
    }
    if (s_twai_receive_ret == 0) {
        s_receive_calls++;
        frame->header.id = s_next_frame_id;
        frame->header.dlc = s_next_frame_len;
        memcpy(frame->buffer, s_next_frame_data, s_next_frame_len > 8 ? 8 : s_next_frame_len);
        frame->buffer_len = s_next_frame_len;
    }
    return s_twai_receive_ret;
}

esp_err_t twai_node_transmit(twai_node_handle_t handle, const twai_frame_t* frame,
                              uint32_t timeout) {
    (void)handle; (void)frame; (void)timeout;
    s_transmit_calls++;
    return 0;
}

void twai_node_transmit_wait_all_done(twai_node_handle_t handle, uint32_t timeout) {
    (void)handle; (void)timeout;
}
