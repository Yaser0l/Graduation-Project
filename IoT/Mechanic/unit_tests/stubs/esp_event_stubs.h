#pragma once

#include <stdbool.h>
#include <stdint.h>

void esp_event_stub_reset(void);
int esp_event_stub_get_register_calls(void);
int esp_event_stub_get_post_calls(void);
const char* esp_event_stub_get_last_post_base(void);
int32_t esp_event_stub_get_last_post_event_id(void);
void esp_event_stub_simulate_event(const char* event_base, int32_t event_id);

void mqtt_client_stub_reset(void);
void mqtt_client_stub_set_init_should_fail(bool fail);
void mqtt_client_stub_set_start_should_fail(bool fail);
void mqtt_client_stub_set_publish_result(int result);
int mqtt_client_stub_get_start_calls(void);
int mqtt_client_stub_get_stop_calls(void);
int mqtt_client_stub_get_destroy_calls(void);
int mqtt_client_stub_get_publish_calls(void);
const char* mqtt_client_stub_get_last_topic(void);
const char* mqtt_client_stub_get_last_payload(void);
const char* mqtt_client_stub_get_last_uri(void);
void (*mqtt_client_stub_get_last_event_handler(void))(void*, const char*, int32_t, void*);
