#include "esp_twai_stubs.h"

#include <string.h>

struct twai_node_stub
{
    int dummy;
};

static struct twai_node_stub s_node;
static twai_event_callbacks_t s_callbacks;
static esp_err_t s_new_node_result = ESP_OK;
static esp_err_t s_register_result = ESP_OK;
static esp_err_t s_enable_result = ESP_OK;
static esp_err_t s_receive_result = ESP_OK;
static int s_new_node_calls = 0;
static int s_register_calls = 0;
static int s_enable_calls = 0;
static twai_stub_frame_t s_next_frame = {0};

void twai_stub_reset(void)
{
    s_new_node_result = ESP_OK;
    s_register_result = ESP_OK;
    s_enable_result = ESP_OK;
    s_receive_result = ESP_OK;
    s_new_node_calls = 0;
    s_register_calls = 0;
    s_enable_calls = 0;
    memset(&s_callbacks, 0, sizeof(s_callbacks));
    memset(&s_next_frame, 0, sizeof(s_next_frame));
}

void twai_stub_set_results(esp_err_t new_node_result,
                           esp_err_t register_result,
                           esp_err_t enable_result,
                           esp_err_t receive_result)
{
    s_new_node_result = new_node_result;
    s_register_result = register_result;
    s_enable_result = enable_result;
    s_receive_result = receive_result;
}

void twai_stub_set_next_frame(uint32_t id, const uint8_t *data, uint8_t len)
{
    s_next_frame.id = id;
    s_next_frame.len = len;
    s_next_frame.valid = true;
    if (data && len > 0)
    {
        memcpy(s_next_frame.data, data, len);
    }
}

int twai_stub_get_new_node_calls(void)
{
    return s_new_node_calls;
}

int twai_stub_get_register_calls(void)
{
    return s_register_calls;
}

int twai_stub_get_enable_calls(void)
{
    return s_enable_calls;
}

const twai_event_callbacks_t *twai_stub_get_callbacks(void)
{
    return &s_callbacks;
}

twai_node_handle_t twai_stub_get_handle(void)
{
    return &s_node;
}

esp_err_t twai_new_node_onchip(const twai_onchip_node_config_t *config, twai_node_handle_t *out_handle)
{
    (void)config;
    s_new_node_calls++;
    if (out_handle)
    {
        *out_handle = &s_node;
    }
    return s_new_node_result;
}

esp_err_t twai_node_register_event_callbacks(twai_node_handle_t handle,
                                             const twai_event_callbacks_t *cbs,
                                             void *user_ctx)
{
    (void)handle;
    (void)user_ctx;
    s_register_calls++;
    if (cbs)
    {
        s_callbacks = *cbs;
    }
    return s_register_result;
}

esp_err_t twai_node_enable(twai_node_handle_t handle)
{
    (void)handle;
    s_enable_calls++;
    return s_enable_result;
}

esp_err_t twai_node_receive_from_isr(twai_node_handle_t handle, twai_frame_t *rx_frame)
{
    (void)handle;
    if (s_receive_result != ESP_OK)
    {
        return s_receive_result;
    }

    if (!rx_frame)
    {
        return ESP_ERR_INVALID_ARG;
    }

    if (s_next_frame.valid)
    {
        rx_frame->header.id = s_next_frame.id;
        rx_frame->buffer_len = s_next_frame.len;
        if (rx_frame->buffer && s_next_frame.len > 0)
        {
            memcpy(rx_frame->buffer, s_next_frame.data, s_next_frame.len);
        }
    }

    return ESP_OK;
}
