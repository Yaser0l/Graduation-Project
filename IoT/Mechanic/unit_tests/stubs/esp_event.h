#pragma once

#include "esp_err.h"
#include <stddef.h>
#include <stdint.h>

#define ESP_EVENT_ANY_ID -1
#define WIFI_EVENT ((esp_event_base_t)(uintptr_t)0x1001)
#define WIFI_EVENT_STA_DISCONNECTED 1
#define IP_EVENT ((esp_event_base_t)(uintptr_t)0x1002)
#define IP_EVENT_STA_GOT_IP 3

typedef const char* esp_event_base_t;

#define ESP_EVENT_DECLARE_BASE(id) extern esp_event_base_t id
#define ESP_EVENT_DEFINE_BASE(id)  esp_event_base_t id = #id

esp_err_t esp_event_post(esp_event_base_t event_base, int32_t event_id,
                          const void* event_data, size_t event_data_size,
                          uint32_t ticks_to_wait);

esp_err_t esp_event_handler_instance_register(esp_event_base_t event_base,
                                               int32_t event_id,
                                               void (*handler)(void*, esp_event_base_t, int32_t, void*),
                                               void* handler_arg,
                                               void* instance);
