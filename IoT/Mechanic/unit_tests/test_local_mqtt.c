#include <string.h>

#include "unity.h"

#include "esp_timer.h"
#include "esp_random.h"
#include "mqtt_client.h"
#include "nvs.h"
#include "wifi_manager.h"

#include "canmodule.h"

static esp_err_t s_can_signals_result = ESP_OK;
static can_decoded_signals_t s_can_signals = {0};

esp_err_t canmodule_get_latest_signals(can_decoded_signals_t *out_signals)
{
    if (!out_signals)
    {
        return ESP_ERR_INVALID_ARG;
    }
    *out_signals = s_can_signals;
    return s_can_signals_result;
}

#include "local_mqtt.c"

static void mqtt_test_reset(void)
{
    s_lock = NULL;
    s_client = NULL;
    strncpy(s_broker_uri, MQTT_DEFAULT_BROKER_URI, sizeof(s_broker_uri) - 1);
    s_broker_uri[sizeof(s_broker_uri) - 1] = '\0';
    memset(s_vehicle_fallback, 0, sizeof(s_vehicle_fallback));
    memset(s_vehicle_vin, 0, sizeof(s_vehicle_vin));

    s_can_signals_result = ESP_OK;
    memset(&s_can_signals, 0, sizeof(s_can_signals));

    mqtt_client_stub_reset();
    nvs_stub_reset();
    wifi_stub_reset();
    esp_timer_stub_set_time(0);
    esp_random_stub_set_value(0xABCDEF12u);
}

void setUp(void)
{
    mqtt_test_reset();
}

void tearDown(void)
{
}

void test_mqtt_init_uses_default_when_nvs_unavailable(void)
{
    nvs_stub_set_open_result(ESP_FAIL);

    TEST_ASSERT_EQUAL(ESP_OK, mqtt_module_init());

    char broker[MQTT_BROKER_URI_MAX_LEN] = {0};
    TEST_ASSERT_TRUE(mqtt_module_get_broker_uri(broker, sizeof(broker)));
    TEST_ASSERT_EQUAL_STRING(MQTT_DEFAULT_BROKER_URI, broker);
}

void test_mqtt_set_broker_uri_rejects_invalid(void)
{
    mqtt_module_init();

    TEST_ASSERT_EQUAL(ESP_ERR_INVALID_ARG, mqtt_module_set_broker_uri(NULL));

    char long_uri[MQTT_BROKER_URI_MAX_LEN + 2];
    memset(long_uri, 'a', sizeof(long_uri));
    long_uri[sizeof(long_uri) - 1] = '\0';
    TEST_ASSERT_EQUAL(ESP_ERR_INVALID_ARG, mqtt_module_set_broker_uri(long_uri));
}

void test_mqtt_set_and_get_broker_uri(void)
{
    mqtt_module_init();

    TEST_ASSERT_EQUAL(ESP_OK, mqtt_module_set_broker_uri("mqtt://example.com"));

    char broker[MQTT_BROKER_URI_MAX_LEN] = {0};
    TEST_ASSERT_TRUE(mqtt_module_get_broker_uri(broker, sizeof(broker)));
    TEST_ASSERT_EQUAL_STRING("mqtt://example.com", broker);
    TEST_ASSERT_EQUAL_STRING("mqtt://example.com", nvs_stub_get_last_set_value());
}

void test_mqtt_publish_dtc_requires_client(void)
{
    mqtt_module_init();

    TEST_ASSERT_EQUAL(ESP_ERR_INVALID_ARG, mqtt_module_publish_dtc("VIN", NULL));
    TEST_ASSERT_EQUAL(ESP_ERR_INVALID_STATE, mqtt_module_publish_dtc("VIN", "payload"));
}

void test_mqtt_publish_dtc_publishes_topic_and_payload(void)
{
    mqtt_module_init();
    wifi_stub_set_connected(true);

    mqtt_start_client_locked();

    TEST_ASSERT_EQUAL(ESP_OK, mqtt_module_publish_dtc("VIN123", "payload"));

    TEST_ASSERT_EQUAL_INT(2, mqtt_client_stub_get_publish_calls());
    TEST_ASSERT_NOT_NULL(strstr(mqtt_client_stub_get_last_topic(), "/DTC"));
    TEST_ASSERT_NOT_NULL(strstr(mqtt_client_stub_get_last_topic(), "VIN123"));
    TEST_ASSERT_EQUAL_STRING("payload", mqtt_client_stub_get_last_payload());
}

int main(void)
{
    UNITY_BEGIN();

    RUN_TEST(test_mqtt_init_uses_default_when_nvs_unavailable);
    RUN_TEST(test_mqtt_set_broker_uri_rejects_invalid);
    RUN_TEST(test_mqtt_set_and_get_broker_uri);
    RUN_TEST(test_mqtt_publish_dtc_requires_client);
    RUN_TEST(test_mqtt_publish_dtc_publishes_topic_and_payload);

    return UNITY_END();
}
