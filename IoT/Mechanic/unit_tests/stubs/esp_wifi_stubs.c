#include "esp_wifi_stubs.h"

static int s_set_mode_calls = 0;
static int s_set_config_calls = 0;
static int s_connect_calls = 0;
static int s_disconnect_calls = 0;
static wifi_mode_t s_last_mode = WIFI_MODE_STA;

void esp_wifi_stub_reset(void) {
    s_set_mode_calls = 0;
    s_set_config_calls = 0;
    s_connect_calls = 0;
    s_disconnect_calls = 0;
    s_last_mode = WIFI_MODE_STA;
}

int esp_wifi_stub_get_set_mode_calls(void) { return s_set_mode_calls; }
int esp_wifi_stub_get_set_config_calls(void) { return s_set_config_calls; }
int esp_wifi_stub_get_connect_calls(void) { return s_connect_calls; }
int esp_wifi_stub_get_disconnect_calls(void) { return s_disconnect_calls; }
wifi_mode_t esp_wifi_stub_get_last_mode(void) { return s_last_mode; }

esp_err_t esp_wifi_set_mode(wifi_mode_t mode) {
    s_set_mode_calls++;
    s_last_mode = mode;
    return 0;
}

esp_err_t esp_wifi_set_config(int iface, wifi_config_t* cfg) {
    (void)iface; (void)cfg;
    s_set_config_calls++;
    return 0;
}

esp_err_t esp_wifi_connect(void) {
    s_connect_calls++;
    return 0;
}

esp_err_t esp_wifi_disconnect(void) {
    s_disconnect_calls++;
    return 0;
}
