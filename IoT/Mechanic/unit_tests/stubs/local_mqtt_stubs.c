#include "local_mqtt.h"

#include <string.h>

static int s_set_vin_calls = 0;
static int s_publish_calls = 0;
static char s_last_vin[32] = {0};
static char s_last_payload[512] = {0};

void mqtt_stub_reset(void)
{
    s_set_vin_calls = 0;
    s_publish_calls = 0;
    memset(s_last_vin, 0, sizeof(s_last_vin));
    memset(s_last_payload, 0, sizeof(s_last_payload));
}

int mqtt_stub_get_set_vin_calls(void)
{
    return s_set_vin_calls;
}

int mqtt_stub_get_publish_calls(void)
{
    return s_publish_calls;
}

const char *mqtt_stub_get_last_vin(void)
{
    return s_last_vin;
}

const char *mqtt_stub_get_last_payload(void)
{
    return s_last_payload;
}

void mqtt_module_set_vin(const char *vin)
{
    s_set_vin_calls++;
    if (vin)
    {
        strncpy(s_last_vin, vin, sizeof(s_last_vin) - 1);
        s_last_vin[sizeof(s_last_vin) - 1] = '\0';
    }
}

esp_err_t mqtt_module_publish_dtc(const char *vin, const char *payload)
{
    s_publish_calls++;
    if (vin)
    {
        strncpy(s_last_vin, vin, sizeof(s_last_vin) - 1);
        s_last_vin[sizeof(s_last_vin) - 1] = '\0';
    }
    if (payload)
    {
        strncpy(s_last_payload, payload, sizeof(s_last_payload) - 1);
        s_last_payload[sizeof(s_last_payload) - 1] = '\0';
    }
    return ESP_OK;
}
