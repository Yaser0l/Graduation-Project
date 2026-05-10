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

void test_mqtt_init_loads_broker_from_nvs(void)
{
    nvs_set_str(1, MQTT_NVS_KEY_BROKER_URI, "mqtt://saved.example");

    TEST_ASSERT_EQUAL(ESP_OK, mqtt_module_init());

    char broker[MQTT_BROKER_URI_MAX_LEN] = {0};
    TEST_ASSERT_TRUE(mqtt_module_get_broker_uri(broker, sizeof(broker)));
    TEST_ASSERT_EQUAL_STRING("mqtt://saved.example", broker);
}

void test_mqtt_init_falls_back_on_invalid_nvs_value(void)
{
    nvs_set_str(1, MQTT_NVS_KEY_BROKER_URI, "");

    TEST_ASSERT_EQUAL(ESP_OK, mqtt_module_init());

    char broker[MQTT_BROKER_URI_MAX_LEN] = {0};
    TEST_ASSERT_TRUE(mqtt_module_get_broker_uri(broker, sizeof(broker)));
    TEST_ASSERT_EQUAL_STRING(MQTT_DEFAULT_BROKER_URI, broker);
}

void test_mqtt_init_falls_back_on_get_str_error(void)
{
    nvs_stub_set_get_str_result(ESP_FAIL);

    TEST_ASSERT_EQUAL(ESP_OK, mqtt_module_init());

    char broker[MQTT_BROKER_URI_MAX_LEN] = {0};
    TEST_ASSERT_TRUE(mqtt_module_get_broker_uri(broker, sizeof(broker)));
    TEST_ASSERT_EQUAL_STRING(MQTT_DEFAULT_BROKER_URI, broker);
}

void test_mqtt_vehicle_id_fallback_uses_random_once(void)
{
    esp_random_stub_set_value(0xDEADBEEFu);

    const char *first = mqtt_get_vehicle_id_locked();
    const char *second = mqtt_get_vehicle_id_locked();

    TEST_ASSERT_EQUAL_STRING("vehicle_deadbeef", first);
    TEST_ASSERT_EQUAL_STRING("vehicle_deadbeef", second);
}

void test_mqtt_build_topic_rejects_invalid_args(void)
{
    char topic[16] = {0};

    TEST_ASSERT_EQUAL(ESP_ERR_INVALID_ARG, mqtt_build_topic_locked(NULL, topic, sizeof(topic)));
    TEST_ASSERT_EQUAL(ESP_ERR_INVALID_ARG, mqtt_build_topic_locked(MQTT_TOPIC_DATA_SUFFIX, NULL, sizeof(topic)));
    TEST_ASSERT_EQUAL(ESP_ERR_INVALID_ARG, mqtt_build_topic_locked(MQTT_TOPIC_DATA_SUFFIX, topic, 0));
}

void test_mqtt_build_topic_rejects_truncated_buffer(void)
{
    char topic[8] = {0};

    TEST_ASSERT_EQUAL(ESP_ERR_INVALID_SIZE, mqtt_build_topic_locked(MQTT_TOPIC_DATA_SUFFIX, topic, sizeof(topic)));
}

void test_mqtt_set_broker_uri_rejects_invalid(void)
{
    mqtt_module_init();

    TEST_ASSERT_EQUAL(ESP_ERR_INVALID_ARG, mqtt_module_set_broker_uri(NULL));
    TEST_ASSERT_EQUAL(ESP_ERR_INVALID_ARG, mqtt_module_set_broker_uri(""));

    char long_uri[MQTT_BROKER_URI_MAX_LEN + 2];
    memset(long_uri, 'a', sizeof(long_uri));
    long_uri[sizeof(long_uri) - 1] = '\0';
    TEST_ASSERT_EQUAL(ESP_ERR_INVALID_ARG, mqtt_module_set_broker_uri(long_uri));
}

void test_mqtt_set_broker_uri_reports_nvs_open_failure(void)
{
    mqtt_module_init();
    nvs_stub_set_open_result(ESP_FAIL);

    TEST_ASSERT_EQUAL(ESP_FAIL, mqtt_module_set_broker_uri("mqtt://fail-open"));
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

void test_mqtt_set_broker_uri_restarts_on_change(void)
{
    mqtt_module_init();
    wifi_stub_set_connected(true);
    mqtt_start_client_locked();
    mqtt_client_stub_reset();

    TEST_ASSERT_EQUAL(ESP_OK, mqtt_module_set_broker_uri("mqtt://new-broker"));

    TEST_ASSERT_EQUAL_INT(1, mqtt_client_stub_get_stop_calls());
    TEST_ASSERT_EQUAL_INT(1, mqtt_client_stub_get_destroy_calls());
    TEST_ASSERT_EQUAL_INT(1, mqtt_client_stub_get_start_calls());
    TEST_ASSERT_EQUAL_STRING("mqtt://new-broker", mqtt_client_stub_get_last_uri());
}

void test_mqtt_set_broker_uri_does_not_restart_on_commit_failure(void)
{
    mqtt_module_init();
    wifi_stub_set_connected(true);
    mqtt_start_client_locked();
    mqtt_client_stub_reset();
    nvs_stub_set_commit_result(ESP_FAIL);

    TEST_ASSERT_EQUAL(ESP_FAIL, mqtt_module_set_broker_uri("mqtt://other"));

    TEST_ASSERT_EQUAL_INT(0, mqtt_client_stub_get_stop_calls());
    TEST_ASSERT_EQUAL_INT(0, mqtt_client_stub_get_destroy_calls());
    TEST_ASSERT_EQUAL_INT(0, mqtt_client_stub_get_start_calls());
}

void test_mqtt_set_broker_uri_does_not_restart_on_same_value(void)
{
    mqtt_module_init();
    wifi_stub_set_connected(true);
    mqtt_start_client_locked();
    mqtt_client_stub_reset();

    TEST_ASSERT_EQUAL(ESP_OK, mqtt_module_set_broker_uri(MQTT_DEFAULT_BROKER_URI));

    TEST_ASSERT_EQUAL_INT(0, mqtt_client_stub_get_stop_calls());
    TEST_ASSERT_EQUAL_INT(0, mqtt_client_stub_get_destroy_calls());
    TEST_ASSERT_EQUAL_INT(0, mqtt_client_stub_get_start_calls());
}

void test_mqtt_get_broker_uri_rejects_invalid_args(void)
{
    char broker[MQTT_BROKER_URI_MAX_LEN] = {0};

    TEST_ASSERT_FALSE(mqtt_module_get_broker_uri(broker, sizeof(broker)));

    mqtt_module_init();

    TEST_ASSERT_FALSE(mqtt_module_get_broker_uri(NULL, sizeof(broker)));
    TEST_ASSERT_FALSE(mqtt_module_get_broker_uri(broker, 0));
}

void test_mqtt_get_broker_uri_rejects_small_buffer(void)
{
    mqtt_module_init();

    char broker[4] = {0};
    TEST_ASSERT_FALSE(mqtt_module_get_broker_uri(broker, sizeof(broker)));
}

void test_mqtt_publish_dtc_requires_client(void)
{
    mqtt_module_init();

    TEST_ASSERT_EQUAL(ESP_ERR_INVALID_ARG, mqtt_module_publish_dtc("VIN", NULL));
    TEST_ASSERT_EQUAL(ESP_ERR_INVALID_STATE, mqtt_module_publish_dtc("VIN", "payload"));
}

void test_mqtt_start_client_locked_requires_wifi(void)
{
    mqtt_start_client_locked();

    TEST_ASSERT_EQUAL_INT(0, mqtt_client_stub_get_start_calls());
    TEST_ASSERT_EQUAL_INT(0, mqtt_client_stub_get_publish_calls());
}

void test_mqtt_start_client_locked_handles_init_failure(void)
{
    wifi_stub_set_connected(true);
    mqtt_client_stub_set_init_should_fail(true);

    mqtt_start_client_locked();

    TEST_ASSERT_EQUAL_INT(0, mqtt_client_stub_get_start_calls());
    TEST_ASSERT_EQUAL_INT(0, mqtt_client_stub_get_publish_calls());
    TEST_ASSERT_NULL(s_client);
}

void test_mqtt_start_client_locked_publishes_status(void)
{
    wifi_stub_set_connected(true);

    mqtt_start_client_locked();

    TEST_ASSERT_EQUAL_INT(1, mqtt_client_stub_get_start_calls());
    TEST_ASSERT_EQUAL_INT(1, mqtt_client_stub_get_publish_calls());
    TEST_ASSERT_NOT_NULL(strstr(mqtt_client_stub_get_last_topic(), "/status"));
    TEST_ASSERT_EQUAL_STRING("online", mqtt_client_stub_get_last_payload());
}

void test_mqtt_stop_client_locked_stops_and_destroys(void)
{
    wifi_stub_set_connected(true);
    mqtt_start_client_locked();
    mqtt_client_stub_reset();

    mqtt_stop_client_locked();

    TEST_ASSERT_EQUAL_INT(1, mqtt_client_stub_get_stop_calls());
    TEST_ASSERT_EQUAL_INT(1, mqtt_client_stub_get_destroy_calls());
    TEST_ASSERT_NULL(s_client);
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

void test_mqtt_publish_dtc_reports_publish_failure(void)
{
    mqtt_module_init();
    wifi_stub_set_connected(true);

    mqtt_start_client_locked();
    mqtt_client_stub_set_publish_result(-1);

    TEST_ASSERT_EQUAL(ESP_ERR_INVALID_STATE, mqtt_module_publish_dtc("VIN123", "payload"));
}

void test_mqtt_publish_task_step_publishes_data(void)
{
    mqtt_module_init();
    wifi_stub_set_connected(true);

    s_can_signals_result = ESP_OK;
    s_can_signals.rx_frames = 7;
    s_can_signals.vehicle_speed_mph = 42.0f;
    esp_timer_stub_set_time(1234000);

    mqtt_publish_task_step();

    TEST_ASSERT_EQUAL_INT(2, mqtt_client_stub_get_publish_calls());
    TEST_ASSERT_NOT_NULL(strstr(mqtt_client_stub_get_last_topic(), "/data"));
    TEST_ASSERT_NOT_NULL(strstr(mqtt_client_stub_get_last_payload(), "\"ts_ms\":1234"));
}

void test_mqtt_publish_task_step_handles_can_error(void)
{
    mqtt_module_init();
    wifi_stub_set_connected(true);
    s_can_signals_result = ESP_FAIL;

    mqtt_publish_task_step();

    TEST_ASSERT_EQUAL_INT(2, mqtt_client_stub_get_publish_calls());
    TEST_ASSERT_NOT_NULL(strstr(mqtt_client_stub_get_last_topic(), "/data"));
}

void test_mqtt_publish_task_step_stops_client_when_disconnected(void)
{
    mqtt_module_init();
    wifi_stub_set_connected(true);
    mqtt_start_client_locked();
    mqtt_client_stub_reset();

    wifi_stub_set_connected(false);
    mqtt_publish_task_step();

    TEST_ASSERT_EQUAL_INT(1, mqtt_client_stub_get_stop_calls());
    TEST_ASSERT_EQUAL_INT(1, mqtt_client_stub_get_destroy_calls());
    TEST_ASSERT_NULL(s_client);
}

void test_mqtt_module_start_task_runs(void)
{
    mqtt_module_start_task();
    TEST_ASSERT_TRUE(true);
}

void test_mqtt_module_set_vin_validates_input(void)
{
    TEST_ASSERT_EQUAL(ESP_ERR_INVALID_ARG, mqtt_module_set_vin("VIN"));

    mqtt_module_init();

    TEST_ASSERT_EQUAL(ESP_ERR_INVALID_ARG, mqtt_module_set_vin(""));
}

void test_mqtt_module_set_vin_updates_vehicle_id(void)
{
    mqtt_module_init();

    TEST_ASSERT_EQUAL(ESP_OK, mqtt_module_set_vin("VIN555"));

    TEST_ASSERT_EQUAL_STRING("VIN555", mqtt_get_vehicle_id_locked());
}

int main(void)
{
    UNITY_BEGIN();

    RUN_TEST(test_mqtt_init_uses_default_when_nvs_unavailable);
    RUN_TEST(test_mqtt_init_loads_broker_from_nvs);
    RUN_TEST(test_mqtt_init_falls_back_on_invalid_nvs_value);
    RUN_TEST(test_mqtt_init_falls_back_on_get_str_error);
    RUN_TEST(test_mqtt_vehicle_id_fallback_uses_random_once);
    RUN_TEST(test_mqtt_build_topic_rejects_invalid_args);
    RUN_TEST(test_mqtt_build_topic_rejects_truncated_buffer);
    RUN_TEST(test_mqtt_set_broker_uri_rejects_invalid);
    RUN_TEST(test_mqtt_set_broker_uri_reports_nvs_open_failure);
    RUN_TEST(test_mqtt_set_and_get_broker_uri);
    RUN_TEST(test_mqtt_set_broker_uri_restarts_on_change);
    RUN_TEST(test_mqtt_set_broker_uri_does_not_restart_on_commit_failure);
    RUN_TEST(test_mqtt_set_broker_uri_does_not_restart_on_same_value);
    RUN_TEST(test_mqtt_get_broker_uri_rejects_invalid_args);
    RUN_TEST(test_mqtt_get_broker_uri_rejects_small_buffer);
    RUN_TEST(test_mqtt_publish_dtc_requires_client);
    RUN_TEST(test_mqtt_start_client_locked_requires_wifi);
    RUN_TEST(test_mqtt_start_client_locked_handles_init_failure);
    RUN_TEST(test_mqtt_start_client_locked_publishes_status);
    RUN_TEST(test_mqtt_stop_client_locked_stops_and_destroys);
    RUN_TEST(test_mqtt_publish_dtc_publishes_topic_and_payload);
    RUN_TEST(test_mqtt_publish_dtc_reports_publish_failure);
    RUN_TEST(test_mqtt_publish_task_step_publishes_data);
    RUN_TEST(test_mqtt_publish_task_step_handles_can_error);
    RUN_TEST(test_mqtt_publish_task_step_stops_client_when_disconnected);
    RUN_TEST(test_mqtt_module_start_task_runs);
    RUN_TEST(test_mqtt_module_set_vin_validates_input);
    RUN_TEST(test_mqtt_module_set_vin_updates_vehicle_id);

    return UNITY_END();
}
