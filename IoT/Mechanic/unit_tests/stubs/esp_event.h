#pragma once

#include <stddef.h>
#include <stdint.h>

#include "freertos/FreeRTOS.h"

#include "esp_err.h"

typedef const char *esp_event_base_t;

typedef void (*esp_event_handler_t)(void *arg, esp_event_base_t event_base,
                                    int32_t event_id, void *event_data);

typedef void *esp_event_handler_instance_t;

#define ESP_EVENT_ANY_ID (-1)

#define ESP_EVENT_DECLARE_BASE(id) extern const esp_event_base_t id
#define ESP_EVENT_DEFINE_BASE(id) const esp_event_base_t id = #id

extern const esp_event_base_t WIFI_EVENT;
extern const esp_event_base_t IP_EVENT;

#define WIFI_EVENT_STA_DISCONNECTED 1
#define IP_EVENT_STA_GOT_IP 2

esp_err_t esp_event_handler_instance_register(
    esp_event_base_t event_base, int32_t event_id,
    esp_event_handler_t event_handler, void *event_handler_arg,
    esp_event_handler_instance_t *instance);

esp_err_t esp_event_post(esp_event_base_t event_base, int32_t event_id,
                         const void *event_data, size_t event_data_size,
                         TickType_t ticks_to_wait);

void esp_event_stub_reset(void);
int esp_event_stub_get_register_calls(void);
