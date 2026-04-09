#include "wifi_manager.h"

#include <stdbool.h>
#include <string.h>

#include "esp_event.h"
#include "esp_log.h"
#include "esp_wifi.h"
#include "freertos/FreeRTOS.h"
#include "freertos/event_groups.h"
#include "freertos/task.h"

#define WIFI_CONNECT_TIMEOUT_MS 10000
#define WIFI_RETRY_LOOP_DELAY_MS 2000

static const char *TAG = "wifi_manager";
static EventGroupHandle_t s_wifi_event_group;
static const int WIFI_CONNECTED_BIT = BIT0;

static saved_ap_store_t s_ap_store = {0};
static bool s_config_ap = false;
static bool s_should_connect = false;

static bool is_wifi_connected(void)
{
    EventBits_t bits = xEventGroupGetBits(s_wifi_event_group);
    return (bits & WIFI_CONNECTED_BIT) != 0;
}

static void stop_config_ap(void)
{
    if (!s_config_ap)
    {
        return;
    }

    ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_STA));
    s_config_ap = false;
    ESP_LOGI(TAG, "Configuration AP stopped");
}

void wifi_manager_start_config_ap(void)
{
    if (s_config_ap)
    {
        return;
    }

    wifi_config_t ap_config = {
        .ap = {
            .ssid = "ESP32_Config",
            .ssid_len = 0,
            .channel = 1,
            .password = "",
            .max_connection = 4,
            .authmode = WIFI_AUTH_OPEN,
        },
    };

    ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_APSTA));
    ESP_ERROR_CHECK(esp_wifi_set_config(WIFI_IF_AP, &ap_config));
    s_config_ap = true;
    ESP_LOGI(TAG, "Configuration AP started: ESP32_Config");
}

static void try_connect_saved_aps(void)
{
    if (s_ap_store.count == 0)
    {
        wifi_manager_start_config_ap();
        return;
    }

    for (uint8_t i = 0; i < s_ap_store.count; ++i)
    {
        wifi_config_t sta_config = {0};
        strncpy((char *)sta_config.sta.ssid, s_ap_store.entries[i].ssid, sizeof(sta_config.sta.ssid) - 1);
        strncpy((char *)sta_config.sta.password, s_ap_store.entries[i].passphrase, sizeof(sta_config.sta.password) - 1);
        sta_config.sta.threshold.authmode = WIFI_AUTH_WPA2_PSK;
        sta_config.sta.pmf_cfg.capable = true;
        sta_config.sta.pmf_cfg.required = false;

        ESP_LOGI(TAG, "Trying AP: %s", s_ap_store.entries[i].ssid);
        ESP_ERROR_CHECK(esp_wifi_set_config(WIFI_IF_STA, &sta_config));
        ESP_ERROR_CHECK(esp_wifi_connect());

        EventBits_t bits = xEventGroupWaitBits(
            s_wifi_event_group,
            WIFI_CONNECTED_BIT,
            pdFALSE,
            pdFALSE,
            pdMS_TO_TICKS(WIFI_CONNECT_TIMEOUT_MS));

        if (bits & WIFI_CONNECTED_BIT)
        {
            ESP_LOGI(TAG, "Connected to: %s", s_ap_store.entries[i].ssid);
            stop_config_ap();
            s_should_connect = false;
            return;
        }

        ESP_LOGW(TAG, "Connection failed for: %s", s_ap_store.entries[i].ssid);
        esp_wifi_disconnect();
    }

    wifi_manager_start_config_ap();
}

static void wifi_manager_task(void *arg)
{
    (void)arg;
    while (true)
    {
        if (s_should_connect && !is_wifi_connected())
        {
            try_connect_saved_aps();
        }

        if (is_wifi_connected())
        {
            stop_config_ap();
        }
        else if (s_ap_store.count == 0)
        {
            wifi_manager_start_config_ap();
        }

        vTaskDelay(pdMS_TO_TICKS(WIFI_RETRY_LOOP_DELAY_MS));
    }
}

static void wifi_event_handler(void *arg, esp_event_base_t event_base,
                               int32_t event_id, void *event_data)
{
    (void)arg;
    (void)event_data;

    if (event_base == WIFI_EVENT && event_id == WIFI_EVENT_STA_DISCONNECTED)
    {
        xEventGroupClearBits(s_wifi_event_group, WIFI_CONNECTED_BIT);
        if (s_ap_store.count > 0)
        {
            s_should_connect = true;
        }
    }
    else if (event_base == IP_EVENT && event_id == IP_EVENT_STA_GOT_IP)
    {
        xEventGroupSetBits(s_wifi_event_group, WIFI_CONNECTED_BIT);
        s_should_connect = false;
    }
}

void wifi_manager_init(const saved_ap_store_t *initial_store)
{
    memset(&s_ap_store, 0, sizeof(s_ap_store));
    if (initial_store)
    {
        memcpy(&s_ap_store, initial_store, sizeof(s_ap_store));
    }

    s_wifi_event_group = xEventGroupCreate();

    ESP_ERROR_CHECK(esp_event_handler_instance_register(
        WIFI_EVENT, ESP_EVENT_ANY_ID, &wifi_event_handler, NULL, NULL));
    ESP_ERROR_CHECK(esp_event_handler_instance_register(
        IP_EVENT, IP_EVENT_STA_GOT_IP, &wifi_event_handler, NULL, NULL));
}

void wifi_manager_start_task(void)
{
    xTaskCreate(wifi_manager_task, "wifi_manager_task", 4096, NULL, 5, NULL);
}

void wifi_manager_notify_store_changed(const saved_ap_store_t *store)
{
    if (!store)
    {
        return;
    }

    memcpy(&s_ap_store, store, sizeof(s_ap_store));
}

void wifi_manager_request_connect(void)
{
    s_should_connect = true;
}

bool wifi_manager_is_connected(void)
{
    return is_wifi_connected();
}
