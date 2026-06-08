#pragma once

#include "esp_err.h"
#include <stdbool.h>
#include <stdint.h>

#define MQTT_EVENT_CONNECTED 1

typedef void* esp_mqtt_client_handle_t;

typedef struct {
    esp_mqtt_client_handle_t client;
} esp_mqtt_event_t;

typedef esp_mqtt_event_t* esp_mqtt_event_handle_t;

typedef struct {
    struct {
        struct {
            const char* uri;
        } address;
    } broker;
    struct {
        struct {
            const char* topic;
            const char* msg;
            int msg_len;
            int qos;
            int retain;
        } last_will;
    } session;
} esp_mqtt_client_config_t;

esp_mqtt_client_handle_t esp_mqtt_client_init(const esp_mqtt_client_config_t* config);
esp_err_t esp_mqtt_client_register_event(esp_mqtt_client_handle_t client, int event_id,
                                          void (*handler)(void*, const char*, int32_t, void*),
                                          void* arg);
esp_err_t esp_mqtt_client_start(esp_mqtt_client_handle_t client);
esp_err_t esp_mqtt_client_stop(esp_mqtt_client_handle_t client);
esp_err_t esp_mqtt_client_destroy(esp_mqtt_client_handle_t client);
int esp_mqtt_client_publish(esp_mqtt_client_handle_t client, const char* topic,
                             const char* data, int len, int qos, int retain);
