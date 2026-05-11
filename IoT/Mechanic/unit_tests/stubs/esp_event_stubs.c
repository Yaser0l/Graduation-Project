#include "esp_event.h"

#include <stddef.h>

static int s_register_calls = 0;

const esp_event_base_t WIFI_EVENT = "WIFI_EVENT";
const esp_event_base_t IP_EVENT = "IP_EVENT";

void esp_event_stub_reset(void)
{
    s_register_calls = 0;
}

int esp_event_stub_get_register_calls(void)
{
    return s_register_calls;
}

esp_err_t esp_event_handler_instance_register(esp_event_base_t event_base,
                                              int32_t event_id,
                                              esp_event_handler_t event_handler,
                                              void *event_handler_arg,
                                              esp_event_handler_instance_t *instance)
{
    (void)event_base;
    (void)event_id;
    (void)event_handler;
    (void)event_handler_arg;
    if (instance)
    {
        *instance = NULL;
    }
    s_register_calls++;
    return ESP_OK;
}
