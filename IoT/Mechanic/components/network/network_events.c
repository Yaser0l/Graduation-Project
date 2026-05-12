#include "network_events.h"

#include "freertos/FreeRTOS.h"

ESP_EVENT_DEFINE_BASE(NETWORK_EVENT);

esp_err_t network_events_post(network_event_id_t event_id,
                              const void *event_data, size_t event_data_size) {
  return esp_event_post(NETWORK_EVENT, event_id, event_data, event_data_size,
                        portMAX_DELAY);
}
