#include "esp_event_stubs.h"

#include <stdbool.h>
#include <string.h>

#include "mqtt_client.h"

static int s_start_calls = 0;
static int s_stop_calls = 0;
static int s_destroy_calls = 0;
static int s_publish_calls = 0;
static int s_publish_result = 0;
static bool s_init_should_fail = false;
static bool s_start_should_fail = false;
static char s_last_topic[256] = {0};
static char s_last_payload[1024] = {0};
static char s_last_uri[256] = {0};

static void (*s_last_event_handler)(void*, const char*, int32_t, void*) = NULL;

void mqtt_client_stub_reset(void) {
    s_start_calls = 0;
    s_stop_calls = 0;
    s_destroy_calls = 0;
    s_publish_calls = 0;
    s_publish_result = 0;
    s_init_should_fail = false;
    s_start_should_fail = false;
    memset(s_last_topic, 0, sizeof(s_last_topic));
    memset(s_last_payload, 0, sizeof(s_last_payload));
    memset(s_last_uri, 0, sizeof(s_last_uri));
    s_last_event_handler = NULL;
}

void mqtt_client_stub_set_init_should_fail(bool fail) { s_init_should_fail = fail; }
void mqtt_client_stub_set_start_should_fail(bool fail) { s_start_should_fail = fail; }
void mqtt_client_stub_set_publish_result(int result) { s_publish_result = result; }
int mqtt_client_stub_get_start_calls(void) { return s_start_calls; }
int mqtt_client_stub_get_stop_calls(void) { return s_stop_calls; }
int mqtt_client_stub_get_destroy_calls(void) { return s_destroy_calls; }
int mqtt_client_stub_get_publish_calls(void) { return s_publish_calls; }
const char* mqtt_client_stub_get_last_topic(void) { return s_last_topic; }
const char* mqtt_client_stub_get_last_payload(void) { return s_last_payload; }
const char* mqtt_client_stub_get_last_uri(void) { return s_last_uri; }
void (*mqtt_client_stub_get_last_event_handler(void))(void*, const char*, int32_t, void*) {
    return s_last_event_handler;
}

esp_mqtt_client_handle_t esp_mqtt_client_init(const esp_mqtt_client_config_t* config) {
    if (s_init_should_fail) return NULL;
    if (config && config->broker.address.uri) {
        strncpy(s_last_uri, config->broker.address.uri, 255);
        s_last_uri[255] = '\0';
    }
    return (esp_mqtt_client_handle_t)0x1000;
}

esp_err_t esp_mqtt_client_register_event(esp_mqtt_client_handle_t client, int event_id,
                                          void (*handler)(void*, const char*, int32_t, void*),
                                          void* arg) {
    (void)client; (void)event_id; (void)arg;
    s_last_event_handler = handler;
    return 0;
}

esp_err_t esp_mqtt_client_start(esp_mqtt_client_handle_t client) {
    (void)client;
    s_start_calls++;
    if (!s_start_should_fail && s_last_event_handler) {
        esp_mqtt_event_t evt = { .client = client };
        s_last_event_handler(NULL, NULL, MQTT_EVENT_CONNECTED, &evt);
    }
    return s_start_should_fail ? -1 : 0;
}

esp_err_t esp_mqtt_client_stop(esp_mqtt_client_handle_t client) {
    (void)client;
    s_stop_calls++;
    return 0;
}

esp_err_t esp_mqtt_client_destroy(esp_mqtt_client_handle_t client) {
    (void)client;
    s_destroy_calls++;
    return 0;
}

int esp_mqtt_client_publish(esp_mqtt_client_handle_t client, const char* topic,
                             const char* data, int len, int qos, int retain) {
    (void)client; (void)len; (void)qos; (void)retain;
    s_publish_calls++;
    if (topic) {
        strncpy(s_last_topic, topic, 255);
        s_last_topic[255] = '\0';
    }
    if (data) {
        strncpy(s_last_payload, data, 1023);
        s_last_payload[1023] = '\0';
    }
    return s_publish_result;
}
