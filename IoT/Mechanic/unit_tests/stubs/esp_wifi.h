#pragma once

#include "esp_err.h"
#include <stdbool.h>
#include <stdint.h>

#define WIFI_IF_STA 0
#define WIFI_IF_AP  1

typedef enum {
    WIFI_MODE_STA = 1,
    WIFI_MODE_AP  = 2,
    WIFI_MODE_APSTA = 3,
} wifi_mode_t;

typedef enum {
    WIFI_AUTH_OPEN = 0,
    WIFI_AUTH_WEP = 1,
    WIFI_AUTH_WPA_PSK = 2,
    WIFI_AUTH_WPA2_PSK = 3,
    WIFI_AUTH_WPA_WPA2_PSK = 4,
    WIFI_AUTH_WPA3_PSK = 5,
    WIFI_AUTH_WPA2_WPA3_PSK = 6,
    WIFI_AUTH_WAPI_PSK = 7,
} wifi_auth_mode_t;

typedef struct {
    uint8_t ssid[33];
    uint8_t password[65];
    uint8_t ssid_len;
    uint8_t channel;
    uint8_t max_connection;
    wifi_auth_mode_t authmode;
} wifi_ap_config_t;

typedef struct {
    uint8_t ssid[33];
    uint8_t password[65];
    struct {
        wifi_auth_mode_t authmode;
    } threshold;
    struct {
        bool capable;
        bool required;
    } pmf_cfg;
} wifi_sta_config_t;

typedef union {
    wifi_ap_config_t ap;
    wifi_sta_config_t sta;
} wifi_config_t;

esp_err_t esp_wifi_set_mode(wifi_mode_t mode);
esp_err_t esp_wifi_set_config(int iface, wifi_config_t* cfg);
esp_err_t esp_wifi_connect(void);
esp_err_t esp_wifi_disconnect(void);
