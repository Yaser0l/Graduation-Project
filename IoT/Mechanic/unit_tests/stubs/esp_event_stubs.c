#include "esp_event.h"

#include <stdbool.h>
#include <stddef.h>

#define MAX_EVENT_HANDLERS 8

typedef struct {
  esp_event_base_t event_base;
  int32_t event_id;
  esp_event_handler_t handler;
  void *handler_arg;
} event_handler_entry_t;

static int s_register_calls = 0;
static size_t s_handler_count = 0;
static event_handler_entry_t s_handlers[MAX_EVENT_HANDLERS];

const esp_event_base_t WIFI_EVENT = "WIFI_EVENT";
const esp_event_base_t IP_EVENT = "IP_EVENT";

void esp_event_stub_reset(void) {
  s_register_calls = 0;
  s_handler_count = 0;
}

int esp_event_stub_get_register_calls(void) { return s_register_calls; }

esp_err_t esp_event_handler_instance_register(
    esp_event_base_t event_base, int32_t event_id,
    esp_event_handler_t event_handler, void *event_handler_arg,
    esp_event_handler_instance_t *instance) {
  if (instance) {
    *instance = NULL;
  }

  if (s_handler_count < MAX_EVENT_HANDLERS) {
    s_handlers[s_handler_count].event_base = event_base;
    s_handlers[s_handler_count].event_id = event_id;
    s_handlers[s_handler_count].handler = event_handler;
    s_handlers[s_handler_count].handler_arg = event_handler_arg;
    s_handler_count++;
  }

  s_register_calls++;
  return ESP_OK;
}

esp_err_t esp_event_post(esp_event_base_t event_base, int32_t event_id,
                         const void *event_data, size_t event_data_size,
                         TickType_t ticks_to_wait) {
  (void)event_data_size;
  (void)ticks_to_wait;

  for (size_t i = 0; i < s_handler_count; ++i) {
    bool base_matches = s_handlers[i].event_base == event_base;
    bool id_matches = s_handlers[i].event_id == ESP_EVENT_ANY_ID ||
                      s_handlers[i].event_id == event_id;

    if (base_matches && id_matches && s_handlers[i].handler) {
      s_handlers[i].handler(s_handlers[i].handler_arg, event_base, event_id,
                            (void *)event_data);
    }
  }

  return ESP_OK;
}
