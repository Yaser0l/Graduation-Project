#pragma once

#include <stddef.h>

#include "esp_err.h"

typedef struct mqtt_client_stub *esp_mqtt_client_handle_t;

typedef struct
{
    struct
    {
        struct
        {
            const char *uri;
        } address;
    } broker;
} esp_mqtt_client_config_t;

esp_mqtt_client_handle_t esp_mqtt_client_init(const esp_mqtt_client_config_t *config);
void esp_mqtt_client_start(esp_mqtt_client_handle_t client);
void esp_mqtt_client_stop(esp_mqtt_client_handle_t client);
void esp_mqtt_client_destroy(esp_mqtt_client_handle_t client);
int esp_mqtt_client_publish(esp_mqtt_client_handle_t client,
                            const char *topic,
                            const char *data,
                            int len,
                            int qos,
                            int retain);

void mqtt_client_stub_reset(void);
int mqtt_client_stub_get_start_calls(void);
int mqtt_client_stub_get_stop_calls(void);
int mqtt_client_stub_get_destroy_calls(void);
int mqtt_client_stub_get_publish_calls(void);
const char *mqtt_client_stub_get_last_topic(void);
const char *mqtt_client_stub_get_last_payload(void);
const char *mqtt_client_stub_get_last_uri(void);
