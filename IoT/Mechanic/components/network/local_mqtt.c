#include "local_mqtt.h"

#include <stdbool.h>
#include <stdio.h>
#include <string.h>

#include "esp_log.h"
#include "esp_timer.h"
#include "esp_random.h"
#include "mqtt_client.h"
#include "nvs.h"

#include "freertos/FreeRTOS.h"
#include "freertos/semphr.h"
#include "freertos/task.h"

#include "canmodule.h"
#include "wifi_manager.h"

#define MQTT_DEFAULT_BROKER_URI "mqtt://broker.emqx.io"
#define MQTT_PUBLISH_INTERVAL_MS 5000
#define MQTT_TOPIC_PREFIX "MechanicAI/user1/"
#define MQTT_TOPIC_DATA_SUFFIX "/data"
#define MQTT_TOPIC_STATUS_SUFFIX "/status"
#define MQTT_TOPIC_DTC_SUFFIX "/DTC"
#define MQTT_NVS_NAMESPACE "mqtt_cfg"
#define MQTT_NVS_KEY_BROKER_URI "broker_uri"

static const char *TAG = "mqtt_module";

static SemaphoreHandle_t s_lock = NULL;
static esp_mqtt_client_handle_t s_client = NULL;
static char s_broker_uri[MQTT_BROKER_URI_MAX_LEN] = MQTT_DEFAULT_BROKER_URI;
static char s_vehicle_fallback[24] = {0};
static char s_vehicle_vin[20] = {0};

static const char *mqtt_get_vehicle_id_locked(void)
{
    if (s_vehicle_vin[0] != '\0')
    {
        return s_vehicle_vin;
    }

    if (s_vehicle_fallback[0] == '\0')
    {
        uint32_t rand_val = esp_random();
        snprintf(s_vehicle_fallback, sizeof(s_vehicle_fallback), "vehicle_%08lx", (unsigned long)rand_val);
    }

    return s_vehicle_fallback;
}

static esp_err_t mqtt_build_topic_locked(const char *suffix, char *out, size_t out_len)
{
    if (!suffix || !out || out_len == 0)
    {
        return ESP_ERR_INVALID_ARG;
    }

    const char *id = mqtt_get_vehicle_id_locked();
    int topic_len = snprintf(out, out_len, "%s%s%s", MQTT_TOPIC_PREFIX, id, suffix);
    if (topic_len <= 0 || topic_len >= (int)out_len)
    {
        return ESP_ERR_INVALID_SIZE;
    }

    return ESP_OK;
}

static esp_err_t mqtt_store_broker_uri_locked(void)
{
    nvs_handle_t nvs;
    esp_err_t err = nvs_open(MQTT_NVS_NAMESPACE, NVS_READWRITE, &nvs);
    if (err != ESP_OK)
    {
        return err;
    }

    err = nvs_set_str(nvs, MQTT_NVS_KEY_BROKER_URI, s_broker_uri);
    if (err == ESP_OK)
    {
        err = nvs_commit(nvs);
    }

    nvs_close(nvs);
    return err;
}

static void mqtt_load_broker_uri(void)
{
    nvs_handle_t nvs;
    esp_err_t err = nvs_open(MQTT_NVS_NAMESPACE, NVS_READONLY, &nvs);
    if (err != ESP_OK)
    {
        ESP_LOGI(TAG, "No persisted broker URI, using default");
        return;
    }

    size_t len = sizeof(s_broker_uri);
    err = nvs_get_str(nvs, MQTT_NVS_KEY_BROKER_URI, s_broker_uri, &len);
    nvs_close(nvs);

    if (err != ESP_OK || s_broker_uri[0] == '\0')
    {
        strncpy(s_broker_uri, MQTT_DEFAULT_BROKER_URI, sizeof(s_broker_uri) - 1);
        s_broker_uri[sizeof(s_broker_uri) - 1] = '\0';
        ESP_LOGI(TAG, "Invalid broker URI in NVS, using default");
    }
}

static void mqtt_stop_client_locked(void)
{
    if (!s_client)
    {
        return;
    }

    esp_mqtt_client_stop(s_client);
    esp_mqtt_client_destroy(s_client);
    s_client = NULL;
}

static void mqtt_start_client_locked(void)
{
    if (s_client || !wifi_manager_is_connected())
    {
        return;
    }

    esp_mqtt_client_config_t mqtt_cfg = {
        .broker.address.uri = s_broker_uri,
    };

    s_client = esp_mqtt_client_init(&mqtt_cfg);
    if (!s_client)
    {
        ESP_LOGE(TAG, "Failed to initialize MQTT client");
        return;
    }

    esp_mqtt_client_start(s_client);
    char topic[96];
    if (mqtt_build_topic_locked(MQTT_TOPIC_STATUS_SUFFIX, topic, sizeof(topic)) == ESP_OK)
    {
        esp_mqtt_client_publish(s_client, topic, "online", 0, 1, 0);
    }
    ESP_LOGI(TAG, "MQTT client started with broker: %s", s_broker_uri);
}

static void mqtt_restart_client_locked(void)
{
    mqtt_stop_client_locked();
    mqtt_start_client_locked();
}

static void mqtt_publish_task(void *arg)
{
    (void)arg;

    while (true)
    {
        esp_mqtt_client_handle_t client = NULL;
        bool should_publish = false;

        xSemaphoreTake(s_lock, portMAX_DELAY);

        if (wifi_manager_is_connected())
        {
            if (!s_client)
            {
                mqtt_start_client_locked();
            }
            if (s_client)
            {
                should_publish = true;
                client = s_client;
            }
        }
        else if (s_client)
        {
            mqtt_stop_client_locked();
        }

        xSemaphoreGive(s_lock);

        if (should_publish && client)
        {
            char payload[512];
            char topic[96];
            int64_t timestamp_ms = esp_timer_get_time() / 1000;
            can_decoded_signals_t signals = {0};

            if (canmodule_get_latest_signals(&signals) != ESP_OK)
            {
                ESP_LOGW(TAG, "Failed to read CAN decoded signals");
            }

            snprintf(payload, sizeof(payload),
                     "{\"device_id\":\"esp32_s3_1\",\"ts_ms\":%lld,\"rx_frames\":%lu,\"vehicle_speed_mph\":%.3f,\"wheel_speed_fl_mph\":%.3f,\"wheel_speed_fr_mph\":%.3f,\"wheel_speed_rl_mph\":%.3f,\"wheel_speed_rr_mph\":%.3f,\"steer_angle_deg\":%.3f,\"steer_rate_deg_s\":%.3f,\"engine_rpm\":%.3f,\"gas_pedal\":%.3f,\"brake_pedal\":%.3f,\"gear\":%u}",
                     (long long)timestamp_ms,
                     (unsigned long)signals.rx_frames,
                     signals.vehicle_speed_mph,
                     signals.wheel_speed_fl_mph,
                     signals.wheel_speed_fr_mph,
                     signals.wheel_speed_rl_mph,
                     signals.wheel_speed_rr_mph,
                     signals.steer_angle_deg,
                     signals.steer_rate_deg_s,
                     signals.engine_rpm,
                     signals.gas_pedal,
                     signals.brake_pedal,
                     (unsigned int)signals.gear);

            if (mqtt_build_topic_locked(MQTT_TOPIC_DATA_SUFFIX, topic, sizeof(topic)) == ESP_OK)
            {
                int msg_id = esp_mqtt_client_publish(client, topic, payload, 0, 1, 0);
                ESP_LOGI(TAG, "Publish result=%d payload=%s", msg_id, payload);
            }
        }

        vTaskDelay(pdMS_TO_TICKS(MQTT_PUBLISH_INTERVAL_MS));
    }
}

esp_err_t mqtt_module_init(void)
{
    if (!s_lock)
    {
        s_lock = xSemaphoreCreateMutex();
        if (!s_lock)
        {
            return ESP_ERR_NO_MEM;
        }
    }

    xSemaphoreTake(s_lock, portMAX_DELAY);
    mqtt_load_broker_uri();
    xSemaphoreGive(s_lock);

    return ESP_OK;
}

void mqtt_module_start_task(void)
{
    xTaskCreate(mqtt_publish_task, "mqtt_publish_task", 4096, NULL, 5, NULL);
}

esp_err_t mqtt_module_set_broker_uri(const char *broker_uri)
{
    if (!s_lock || !broker_uri)
    {
        return ESP_ERR_INVALID_ARG;
    }

    size_t len = strnlen(broker_uri, MQTT_BROKER_URI_MAX_LEN);
    if (len == 0 || len >= MQTT_BROKER_URI_MAX_LEN)
    {
        return ESP_ERR_INVALID_ARG;
    }

    xSemaphoreTake(s_lock, portMAX_DELAY);

    bool changed = strcmp(s_broker_uri, broker_uri) != 0;
    strncpy(s_broker_uri, broker_uri, sizeof(s_broker_uri) - 1);
    s_broker_uri[sizeof(s_broker_uri) - 1] = '\0';

    esp_err_t err = mqtt_store_broker_uri_locked();
    if (err == ESP_OK && changed)
    {
        mqtt_restart_client_locked();
    }

    xSemaphoreGive(s_lock);
    return err;
}

bool mqtt_module_get_broker_uri(char *out, size_t out_len)
{
    if (!s_lock || !out || out_len == 0)
    {
        return false;
    }

    xSemaphoreTake(s_lock, portMAX_DELAY);
    size_t len = strnlen(s_broker_uri, sizeof(s_broker_uri));
    if (len + 1 > out_len)
    {
        xSemaphoreGive(s_lock);
        return false;
    }

    memcpy(out, s_broker_uri, len + 1);
    xSemaphoreGive(s_lock);
    return true;
}

esp_err_t mqtt_module_publish_dtc(const char *vin, const char *payload)
{
    if (!payload || !s_lock)
    {
        return ESP_ERR_INVALID_ARG;
    }

    esp_err_t result = ESP_ERR_INVALID_STATE;
    char topic[96];
    xSemaphoreTake(s_lock, portMAX_DELAY);

    if (vin && vin[0] != '\0' && strncmp(s_vehicle_vin, vin, sizeof(s_vehicle_vin)) != 0)
    {
        strncpy(s_vehicle_vin, vin, sizeof(s_vehicle_vin) - 1);
        s_vehicle_vin[sizeof(s_vehicle_vin) - 1] = '\0';
    }

    if (mqtt_build_topic_locked(MQTT_TOPIC_DTC_SUFFIX, topic, sizeof(topic)) != ESP_OK)
    {
        xSemaphoreGive(s_lock);
        return ESP_ERR_INVALID_SIZE;
    }

    if (s_client && wifi_manager_is_connected())
    {
        int msg_id = esp_mqtt_client_publish(s_client, topic, payload, 0, 1, 0);
        if (msg_id >= 0)
        {
            result = ESP_OK;
        }
    }

    xSemaphoreGive(s_lock);
    return result;
}

esp_err_t mqtt_module_set_vin(const char *vin)
{
    if (!s_lock || !vin)
    {
        return ESP_ERR_INVALID_ARG;
    }

    if (vin[0] == '\0')
    {
        return ESP_ERR_INVALID_ARG;
    }

    xSemaphoreTake(s_lock, portMAX_DELAY);
    strncpy(s_vehicle_vin, vin, sizeof(s_vehicle_vin) - 1);
    s_vehicle_vin[sizeof(s_vehicle_vin) - 1] = '\0';
    xSemaphoreGive(s_lock);
    return ESP_OK;
}
