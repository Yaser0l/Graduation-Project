#include "esp_event.h"
#include "esp_event_stubs.h"

#include <stdbool.h>
#include <string.h>

static int s_register_calls = 0;
static int s_post_calls = 0;
static esp_event_base_t s_last_post_base_ptr = NULL;
static int32_t s_last_post_event_id = 0;

typedef struct {
    void (*handler)(void*, esp_event_base_t, int32_t, void*);
    esp_event_base_t base;
    int32_t event_id;
} event_handler_entry_t;

static event_handler_entry_t s_handlers[16] = {{0}};
static int s_handler_count = 0;

void esp_event_stub_reset(void) {
    s_register_calls = 0;
    s_post_calls = 0;
    s_last_post_base_ptr = NULL;
    s_last_post_event_id = 0;
    memset(s_handlers, 0, sizeof(s_handlers));
    s_handler_count = 0;
}

int esp_event_stub_get_register_calls(void) { return s_register_calls; }
int esp_event_stub_get_post_calls(void) { return s_post_calls; }
const char* esp_event_stub_get_last_post_base(void) { return s_last_post_base_ptr; }
int32_t esp_event_stub_get_last_post_event_id(void) { return s_last_post_event_id; }

void esp_event_stub_simulate_event(const char* event_base, int32_t event_id) {
    for (int i = 0; i < s_handler_count; ++i) {
        if ((s_handlers[i].event_id == ESP_EVENT_ANY_ID ||
             s_handlers[i].event_id == event_id) &&
            s_handlers[i].base == event_base) {
            if (s_handlers[i].handler) {
                s_handlers[i].handler(NULL, s_handlers[i].base, event_id, NULL);
            }
        }
    }
}

esp_err_t esp_event_post(esp_event_base_t event_base, int32_t event_id,
                          const void* event_data, size_t event_data_size,
                          uint32_t ticks_to_wait) {
    (void)ticks_to_wait;
    s_post_calls++;
    s_last_post_base_ptr = event_base;
    s_last_post_event_id = event_id;

    for (int i = 0; i < s_handler_count; ++i) {
        if ((s_handlers[i].event_id == ESP_EVENT_ANY_ID ||
             s_handlers[i].event_id == event_id) &&
            s_handlers[i].base == event_base) {
            if (s_handlers[i].handler) {
                s_handlers[i].handler(NULL, s_handlers[i].base, event_id, (void*)event_data);
            }
        }
    }
    return 0;
}

esp_err_t esp_event_handler_instance_register(esp_event_base_t event_base,
                                               int32_t event_id,
                                               void (*handler)(void*,
                                                               esp_event_base_t,
                                                               int32_t,
                                                               void*),
                                               void* handler_arg,
                                               void* instance) {
    (void)handler_arg; (void)instance;
    s_register_calls++;
    if (s_handler_count < 16) {
        s_handlers[s_handler_count].handler = handler;
        s_handlers[s_handler_count].base = event_base;
        s_handlers[s_handler_count].event_id = event_id;
        s_handler_count++;
    }
    return 0;
}
