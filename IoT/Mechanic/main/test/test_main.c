#include "unity.h"

#include <string.h>

#include "esp_err.h"
#include "nvs_flash.h"

#include "local_mqtt.h"

static void test_mqtt_set_vin_validation(void)
{
    TEST_ASSERT_EQUAL(ESP_ERR_INVALID_ARG, mqtt_module_set_vin(NULL));
    TEST_ASSERT_EQUAL(ESP_ERR_INVALID_ARG, mqtt_module_set_vin(""));
    TEST_ASSERT_EQUAL(ESP_OK, mqtt_module_set_vin("TESTVIN123"));
}

static void test_mqtt_broker_uri_validation(void)
{
    char uri[MQTT_BROKER_URI_MAX_LEN];
    TEST_ASSERT_TRUE(mqtt_module_get_broker_uri(uri, sizeof(uri)));

    TEST_ASSERT_EQUAL(ESP_ERR_INVALID_ARG, mqtt_module_set_broker_uri(NULL));
    TEST_ASSERT_EQUAL(ESP_ERR_INVALID_ARG, mqtt_module_set_broker_uri(""));

    char too_long[MQTT_BROKER_URI_MAX_LEN + 1];
    memset(too_long, 'a', MQTT_BROKER_URI_MAX_LEN);
    too_long[MQTT_BROKER_URI_MAX_LEN] = '\0';
    TEST_ASSERT_EQUAL(ESP_ERR_INVALID_ARG, mqtt_module_set_broker_uri(too_long));
}

static void test_mqtt_broker_uri_roundtrip(void)
{
    const char *expected = "mqtt://test.example.com";
    TEST_ASSERT_EQUAL(ESP_OK, mqtt_module_set_broker_uri(expected));

    char uri[MQTT_BROKER_URI_MAX_LEN];
    TEST_ASSERT_TRUE(mqtt_module_get_broker_uri(uri, sizeof(uri)));
    TEST_ASSERT_EQUAL_STRING(expected, uri);
}

static void init_nvs_or_erase(void)
{
    esp_err_t err = nvs_flash_init();
    if (err == ESP_ERR_NVS_NO_FREE_PAGES || err == ESP_ERR_NVS_NEW_VERSION_FOUND)
    {
        nvs_flash_erase();
        err = nvs_flash_init();
    }
    TEST_ASSERT_EQUAL(ESP_OK, err);
}

void app_main(void)
{
    UNITY_BEGIN();

    init_nvs_or_erase();
    TEST_ASSERT_EQUAL(ESP_OK, mqtt_module_init());

    RUN_TEST(test_mqtt_set_vin_validation);
    RUN_TEST(test_mqtt_broker_uri_validation);
    RUN_TEST(test_mqtt_broker_uri_roundtrip);

    UNITY_END();
}
