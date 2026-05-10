#include "esp_wifi.h"

#include <string.h>

static int s_set_mode_calls = 0;
static int s_set_config_calls = 0;
static int s_connect_calls = 0;
static int s_disconnect_calls = 0;
static wifi_mode_t s_last_mode = WIFI_MODE_STA;
static wifi_interface_t s_last_iface = WIFI_IF_STA;
static wifi_config_t s_last_config;

void esp_wifi_stub_reset(void)
{
    s_set_mode_calls = 0;
    s_set_config_calls = 0;
    s_connect_calls = 0;
    s_disconnect_calls = 0;
    s_last_mode = WIFI_MODE_STA;
    s_last_iface = WIFI_IF_STA;
    memset(&s_last_config, 0, sizeof(s_last_config));
}

int esp_wifi_stub_get_set_mode_calls(void)
{
    return s_set_mode_calls;
}

int esp_wifi_stub_get_set_config_calls(void)
{
    return s_set_config_calls;
}

int esp_wifi_stub_get_connect_calls(void)
{
    return s_connect_calls;
}

int esp_wifi_stub_get_disconnect_calls(void)
{
    return s_disconnect_calls;
}

wifi_mode_t esp_wifi_stub_get_last_mode(void)
{
    return s_last_mode;
}

wifi_interface_t esp_wifi_stub_get_last_iface(void)
{
    return s_last_iface;
}

const wifi_config_t *esp_wifi_stub_get_last_config(void)
{
    return &s_last_config;
}

esp_err_t esp_wifi_set_mode(wifi_mode_t mode)
{
    s_set_mode_calls++;
    s_last_mode = mode;
    return ESP_OK;
}

esp_err_t esp_wifi_set_config(wifi_interface_t iface, const wifi_config_t *config)
{
    s_set_config_calls++;
    s_last_iface = iface;
    if (config)
    {
        s_last_config = *config;
    }
    return ESP_OK;
}

esp_err_t esp_wifi_connect(void)
{
    s_connect_calls++;
    return ESP_OK;
}

esp_err_t esp_wifi_disconnect(void)
{
    s_disconnect_calls++;
    return ESP_OK;
}
