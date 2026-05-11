#include "esp_event.h"
#include "esp_log.h"
#include "esp_netif.h"
#include "esp_wifi.h"
#include "nvs_flash.h"

#include "local_mqtt.h"
#include "canmodule.h"
#include "dtc_reporter.h"
#include "web_server.h"
#include "wifi_manager.h"
#include "wifi_store.h"

static const char *TAG = "main";
static saved_ap_store_t s_ap_store = {0};

void app_main(void)
{
    esp_err_t ret = nvs_flash_init();
    if (ret == ESP_ERR_NVS_NO_FREE_PAGES || ret == ESP_ERR_NVS_NEW_VERSION_FOUND)
    {
        ESP_ERROR_CHECK(nvs_flash_erase());
        ret = nvs_flash_init();
    }
    ESP_ERROR_CHECK(ret);

    ESP_ERROR_CHECK(esp_netif_init());
    ESP_ERROR_CHECK(esp_event_loop_create_default());
    esp_netif_create_default_wifi_sta();
    esp_netif_create_default_wifi_ap();

    wifi_init_config_t cfg = WIFI_INIT_CONFIG_DEFAULT();
    ESP_ERROR_CHECK(esp_wifi_init(&cfg));

    ESP_ERROR_CHECK(canmodule_init());
    ESP_ERROR_CHECK(dtc_reporter_init());

    ESP_ERROR_CHECK(wifi_store_load(&s_ap_store));

    wifi_manager_init(&s_ap_store);
    ESP_ERROR_CHECK(mqtt_module_init());

    ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_APSTA));
    ESP_ERROR_CHECK(esp_wifi_start());

    if (s_ap_store.count == 0)
    {
        ESP_LOGI(TAG, "No saved APs found. Starting configuration AP...");
        wifi_manager_start_config_ap();
    }
    else
    {
        ESP_LOGI(TAG, "Saved APs found. Auto-connecting...");
        wifi_manager_request_connect();
    }

    web_server_start(&s_ap_store);
    wifi_manager_start_task();
    mqtt_module_start_task();
    dtc_reporter_start_task();
}