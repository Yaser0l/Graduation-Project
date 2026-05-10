#pragma once

#include <stdbool.h>
#include <stdint.h>

#include "esp_err.h"

typedef enum
{
    WIFI_MODE_STA = 0,
    WIFI_MODE_APSTA = 1
} wifi_mode_t;

typedef enum
{
    WIFI_IF_STA = 0,
    WIFI_IF_AP = 1
} wifi_interface_t;

typedef enum
{
    WIFI_AUTH_OPEN = 0,
    WIFI_AUTH_WPA2_PSK = 3
} wifi_auth_mode_t;

typedef struct
{
    bool capable;
    bool required;
} wifi_pmf_config_t;

typedef struct
{
    wifi_auth_mode_t authmode;
} wifi_scan_threshold_t;

typedef struct
{
    uint8_t ssid[32];
    uint8_t password[64];
    wifi_scan_threshold_t threshold;
    wifi_pmf_config_t pmf_cfg;
} wifi_sta_config_t;

typedef struct
{
    uint8_t ssid[32];
    uint8_t ssid_len;
    uint8_t channel;
    char password[64];
    uint8_t max_connection;
    wifi_auth_mode_t authmode;
} wifi_ap_config_t;

typedef union
{
    wifi_sta_config_t sta;
    wifi_ap_config_t ap;
} wifi_config_t;

esp_err_t esp_wifi_set_mode(wifi_mode_t mode);
esp_err_t esp_wifi_set_config(wifi_interface_t iface, const wifi_config_t *config);
esp_err_t esp_wifi_connect(void);
esp_err_t esp_wifi_disconnect(void);

void esp_wifi_stub_reset(void);
int esp_wifi_stub_get_set_mode_calls(void);
int esp_wifi_stub_get_set_config_calls(void);
int esp_wifi_stub_get_connect_calls(void);
int esp_wifi_stub_get_disconnect_calls(void);
wifi_mode_t esp_wifi_stub_get_last_mode(void);
wifi_interface_t esp_wifi_stub_get_last_iface(void);
const wifi_config_t *esp_wifi_stub_get_last_config(void);
