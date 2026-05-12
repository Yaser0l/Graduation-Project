#pragma once

#include <stddef.h>

#include "esp_event.h"

ESP_EVENT_DECLARE_BASE(NETWORK_EVENT);

typedef enum {
  NETWORK_EVENT_UP = 1,
  NETWORK_EVENT_DOWN = 2,
  NETWORK_EVENT_REQUEST = 3,
} network_event_id_t;

esp_err_t network_events_post(network_event_id_t event_id,
                              const void *event_data, size_t event_data_size);
