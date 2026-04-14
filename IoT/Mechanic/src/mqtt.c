/*
 * PROJECT: DHT11 SENSOR PUBLISHER
 *
 * This code reads temperature and humidity from a DHT11 sensor
 * and publishes the data to an MQTT broker.
 */

#include <stdio.h>
#include <string.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/event_groups.h" // Added for synchronization
#include "esp_system.h"
#include "esp_wifi.h"
#include "esp_event.h"
#include "esp_log.h"
#include "nvs_flash.h"

#include "mqtt_client.h"
#include "dht.h" // Include DHT sensor library

// --- Configuration ---
#define WIFI_SSID "SSID"
#define WIFI_PASS "password"

#define MQTT_BROKER_URI "mqtt://broker.emqx.io"
#define DHT_GPIO 4 // GPIO pin for the DHT11 sensor data line

// --- Global Variables ---
static const char *TAG = "DHT_PUBLISHER";
esp_mqtt_client_handle_t client;

/* --- Event Group for Synchronization --- */
static EventGroupHandle_t wifi_event_group;
// Define a bit for when we are connected to Wi-Fi and have an IP
#define WIFI_CONNECTED_BIT BIT0

// --- Event Handlers ---
static void mqtt_event_handler(void *handler_args, esp_event_base_t base, int32_t event_id, void *event_data)
{
    switch ((esp_mqtt_event_id_t)event_id)
    {
    case MQTT_EVENT_CONNECTED:
        ESP_LOGI(TAG, "MQTT client connected");
        esp_mqtt_client_publish(client, "iotfrontier/esp32/status", "sensor_online", 0, 1, 0);
        break;
    case MQTT_EVENT_DISCONNECTED:
        ESP_LOGI(TAG, "MQTT client disconnected");
        break;
    default:
        break;
    }
}

// This function now signals the event group when an IP is obtained.
static void wifi_event_handler(void *arg, esp_event_base_t event_base,
                               int32_t event_id, void *event_data)
{
    if (event_id == WIFI_EVENT_STA_START)
    {
        esp_wifi_connect();
        ESP_LOGI(TAG, "Wi-Fi connecting...");
    }
    else if (event_id == WIFI_EVENT_STA_DISCONNECTED)
    {
        ESP_LOGI(TAG, "Wi-Fi disconnected, trying to reconnect...");
        esp_wifi_connect();
    }
    else if (event_id == IP_EVENT_STA_GOT_IP)
    {
        ip_event_got_ip_t *event = (ip_event_got_ip_t *)event_data;
        ESP_LOGI(TAG, "Got IP address: " IPSTR, IP2STR(&event->ip_info.ip));
        // Set the bit to signal that the connection is ready
        xEventGroupSetBits(wifi_event_group, WIFI_CONNECTED_BIT);
    }
}

// --- Initialization Functions ---
static void wifi_init(void)
{
    // Create the event group before anything else
    wifi_event_group = xEventGroupCreate();

    ESP_ERROR_CHECK(nvs_flash_init());
    ESP_ERROR_CHECK(esp_netif_init());
    ESP_ERROR_CHECK(esp_event_loop_create_default());

    ESP_ERROR_CHECK(esp_event_handler_instance_register(WIFI_EVENT, ESP_EVENT_ANY_ID, &wifi_event_handler, NULL, NULL));
    ESP_ERROR_CHECK(esp_event_handler_instance_register(IP_EVENT, IP_EVENT_STA_GOT_IP, &wifi_event_handler, NULL, NULL));

    esp_netif_create_default_wifi_sta();
    wifi_init_config_t cfg = WIFI_INIT_CONFIG_DEFAULT();
    ESP_ERROR_CHECK(esp_wifi_init(&cfg));

    wifi_config_t wifi_config = {.sta = {.ssid = WIFI_SSID, .password = WIFI_PASS}};
    ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_STA));
    ESP_ERROR_CHECK(esp_wifi_set_config(ESP_IF_WIFI_STA, &wifi_config));
    ESP_ERROR_CHECK(esp_wifi_start());
    ESP_LOGI(TAG, "Wi-Fi initialization finished. Waiting for connection...");
}

static void mqtt_app_start(void)
{
    esp_mqtt_client_config_t mqtt_cfg = {.broker.address.uri = MQTT_BROKER_URI};
    client = esp_mqtt_client_init(&mqtt_cfg);
    esp_mqtt_client_register_event(client, ESP_EVENT_ANY_ID, mqtt_event_handler, NULL);
    esp_mqtt_client_start(client);
}

// --- Publisher Task ---
void publisher_task(void *pvParameters)
{
    float temperature, humidity;
    char json_payload[120];

    while (1)
    {
        if (dht_read_float_data(DHT_TYPE_DHT11, DHT_GPIO, &humidity, &temperature) == ESP_OK)
        {
            ESP_LOGI(TAG, "Sensor Read OK: Temp=%.1fC, Humidity=%.1f%%", temperature, humidity);

            snprintf(json_payload, sizeof(json_payload),
                     "{\"device_id\":\"dht11_sensor_1\", \"temperature\":%.1f, \"humidity\":%.1f}",
                     temperature, humidity);

            esp_mqtt_client_publish(client, "iotfrontier/esp32/data", json_payload, 0, 1, 0);
        }
        else
        {
            ESP_LOGE(TAG, "Failed to read data from DHT11 sensor");
        }

        vTaskDelay(10000 / portTICK_PERIOD_MS);
    }
}

// --- Main Application (Updated) ---
void app_main(void)
{
    // Initialize Wi-Fi and start the connection process
    wifi_init();

    // --- Wait here until the WIFI_CONNECTED_BIT is set ---
    // The program will pause on this line until the event handler
    // signals that an IP address has been received.
    xEventGroupWaitBits(wifi_event_group,
                        WIFI_CONNECTED_BIT,
                        pdFALSE,
                        pdFALSE,
                        portMAX_DELAY);

    ESP_LOGI(TAG, "Wi-Fi connection established. Starting MQTT client.");

    // Now that we are connected, we can safely start the MQTT client
    mqtt_app_start();

    // Create and run the publisher task
    xTaskCreate(&publisher_task, "publisher_task", 2048, NULL, 5, NULL);
}
