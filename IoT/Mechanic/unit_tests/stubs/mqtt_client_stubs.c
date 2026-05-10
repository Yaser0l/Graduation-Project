#include "mqtt_client.h"

#include <stdbool.h>
#include <string.h>

struct mqtt_client_stub
{
    int dummy;
};

static struct mqtt_client_stub s_client;
static int s_start_calls = 0;
static int s_stop_calls = 0;
static int s_destroy_calls = 0;
static int s_publish_calls = 0;
static char s_last_topic[128] = {0};
static char s_last_payload[512] = {0};
static char s_last_uri[128] = {0};
static bool s_init_should_fail = false;
static bool s_publish_override = false;
static int s_publish_override_result = 0;

void mqtt_client_stub_reset(void)
{
    s_start_calls = 0;
    s_stop_calls = 0;
    s_destroy_calls = 0;
    s_publish_calls = 0;
    memset(s_last_topic, 0, sizeof(s_last_topic));
    memset(s_last_payload, 0, sizeof(s_last_payload));
    memset(s_last_uri, 0, sizeof(s_last_uri));
    s_init_should_fail = false;
    s_publish_override = false;
    s_publish_override_result = 0;
}

int mqtt_client_stub_get_start_calls(void)
{
    return s_start_calls;
}

int mqtt_client_stub_get_stop_calls(void)
{
    return s_stop_calls;
}

int mqtt_client_stub_get_destroy_calls(void)
{
    return s_destroy_calls;
}

int mqtt_client_stub_get_publish_calls(void)
{
    return s_publish_calls;
}

const char *mqtt_client_stub_get_last_topic(void)
{
    return s_last_topic;
}

const char *mqtt_client_stub_get_last_payload(void)
{
    return s_last_payload;
}

const char *mqtt_client_stub_get_last_uri(void)
{
    return s_last_uri;
}

void mqtt_client_stub_set_init_should_fail(bool should_fail)
{
    s_init_should_fail = should_fail;
}

void mqtt_client_stub_set_publish_result(int result)
{
    s_publish_override = true;
    s_publish_override_result = result;
}

esp_mqtt_client_handle_t esp_mqtt_client_init(const esp_mqtt_client_config_t *config)
{
    if (s_init_should_fail)
    {
        return NULL;
    }

    if (config && config->broker.address.uri)
    {
        strncpy(s_last_uri, config->broker.address.uri, sizeof(s_last_uri) - 1);
        s_last_uri[sizeof(s_last_uri) - 1] = '\0';
    }
    return &s_client;
}

void esp_mqtt_client_start(esp_mqtt_client_handle_t client)
{
    (void)client;
    s_start_calls++;
}

void esp_mqtt_client_stop(esp_mqtt_client_handle_t client)
{
    (void)client;
    s_stop_calls++;
}

void esp_mqtt_client_destroy(esp_mqtt_client_handle_t client)
{
    (void)client;
    s_destroy_calls++;
}

int esp_mqtt_client_publish(esp_mqtt_client_handle_t client,
                            const char *topic,
                            const char *data,
                            int len,
                            int qos,
                            int retain)
{
    (void)client;
    (void)len;
    (void)qos;
    (void)retain;
    s_publish_calls++;
    if (topic)
    {
        strncpy(s_last_topic, topic, sizeof(s_last_topic) - 1);
        s_last_topic[sizeof(s_last_topic) - 1] = '\0';
    }
    if (data)
    {
        strncpy(s_last_payload, data, sizeof(s_last_payload) - 1);
        s_last_payload[sizeof(s_last_payload) - 1] = '\0';
    }
    if (s_publish_override)
    {
        return s_publish_override_result;
    }
    return s_publish_calls;
}
