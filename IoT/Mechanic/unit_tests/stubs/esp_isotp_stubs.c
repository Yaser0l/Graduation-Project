#include "esp_isotp.h"

#include <string.h>

struct esp_isotp_stub
{
    int dummy;
};

typedef struct
{
    uint8_t data[256];
    uint32_t len;
} isotp_rx_item_t;

static struct esp_isotp_stub s_isotp;
static esp_err_t s_new_transport_result = ESP_OK;
static esp_err_t s_send_result = ESP_OK;
static esp_err_t s_receive_result = ESP_OK;
static int s_send_calls = 0;
static uint8_t s_last_send_payload[64];
static uint32_t s_last_send_len = 0;
static isotp_rx_item_t s_rx_queue[4];
static int s_rx_head = 0;
static int s_rx_tail = 0;
static int s_rx_count = 0;

void isotp_stub_reset(void)
{
    s_new_transport_result = ESP_OK;
    s_send_result = ESP_OK;
    s_receive_result = ESP_OK;
    s_send_calls = 0;
    s_last_send_len = 0;
    memset(s_last_send_payload, 0, sizeof(s_last_send_payload));
    memset(s_rx_queue, 0, sizeof(s_rx_queue));
    s_rx_head = 0;
    s_rx_tail = 0;
    s_rx_count = 0;
}

void isotp_stub_set_new_transport_result(esp_err_t result)
{
    s_new_transport_result = result;
}

void isotp_stub_set_send_result(esp_err_t result)
{
    s_send_result = result;
}

void isotp_stub_set_receive_result(esp_err_t result)
{
    s_receive_result = result;
}

int isotp_stub_get_send_calls(void)
{
    return s_send_calls;
}

uint32_t isotp_stub_get_last_send_len(void)
{
    return s_last_send_len;
}

const uint8_t *isotp_stub_get_last_send_payload(void)
{
    return s_last_send_payload;
}

int isotp_stub_queue_rx(const uint8_t *data, uint32_t len)
{
    if (s_rx_count >= (int)(sizeof(s_rx_queue) / sizeof(s_rx_queue[0])))
    {
        return 0;
    }

    if (len > sizeof(s_rx_queue[0].data))
    {
        len = sizeof(s_rx_queue[0].data);
    }

    if (data && len > 0)
    {
        memcpy(s_rx_queue[s_rx_tail].data, data, len);
        s_rx_queue[s_rx_tail].len = len;
    }
    else
    {
        s_rx_queue[s_rx_tail].len = 0;
    }

    s_rx_tail = (s_rx_tail + 1) % (int)(sizeof(s_rx_queue) / sizeof(s_rx_queue[0]));
    s_rx_count++;
    return 1;
}

esp_err_t esp_isotp_new_transport(twai_node_handle_t node,
                                 const esp_isotp_config_t *config,
                                 esp_isotp_handle_t *out_handle)
{
    (void)node;
    (void)config;

    if (out_handle)
    {
        *out_handle = &s_isotp;
    }

    return s_new_transport_result;
}

esp_err_t esp_isotp_send(esp_isotp_handle_t handle, const uint8_t *data, uint32_t len)
{
    (void)handle;
    s_send_calls++;

    if (data && len > 0)
    {
        if (len > sizeof(s_last_send_payload))
        {
            len = sizeof(s_last_send_payload);
        }
        memcpy(s_last_send_payload, data, len);
        s_last_send_len = len;
    }
    else
    {
        s_last_send_len = 0;
    }

    return s_send_result;
}

esp_err_t esp_isotp_receive(esp_isotp_handle_t handle, uint8_t *data, uint32_t max_len, uint32_t *out_len)
{
    (void)handle;

    if (s_receive_result != ESP_OK)
    {
        return s_receive_result;
    }

    if (s_rx_count == 0)
    {
        return ESP_FAIL;
    }

    const isotp_rx_item_t *item = &s_rx_queue[s_rx_head];
    uint32_t copy_len = item->len;
    if (copy_len > max_len)
    {
        copy_len = max_len;
    }

    if (data && copy_len > 0)
    {
        memcpy(data, item->data, copy_len);
    }

    if (out_len)
    {
        *out_len = copy_len;
    }

    s_rx_head = (s_rx_head + 1) % (int)(sizeof(s_rx_queue) / sizeof(s_rx_queue[0]));
    s_rx_count--;

    return ESP_OK;
}

void esp_isotp_poll(esp_isotp_handle_t handle)
{
    (void)handle;
}
