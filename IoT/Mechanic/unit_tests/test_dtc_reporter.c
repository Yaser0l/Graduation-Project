#include <string.h>

#include "unity.h"

#include "esp_isotp.h"
#include "esp_timer.h"
#include "local_mqtt.h"
#include "esp_twai_types.h"

static twai_node_handle_t s_can_handle = (twai_node_handle_t)1;

twai_node_handle_t canmodule_get_twai_handle(void)
{
    return s_can_handle;
}

#include "dtc_reporter.c"

static void dtc_test_reset(void)
{
    s_isotp = NULL;
    s_ready = false;
    s_dtc_count = 0;
    memset(s_dtc_codes, 0, sizeof(s_dtc_codes));
    memset(s_vin, 0, sizeof(s_vin));
    s_mileage = 0;
    s_last_request_us = 0;
    s_request_start_us = 0;
    s_waiting_for_response = false;
    s_can_handle = (twai_node_handle_t)1;
    isotp_stub_reset();
    mqtt_stub_reset();
    esp_timer_stub_set_time(0);
}

void setUp(void)
{
    dtc_test_reset();
}

void tearDown(void)
{
}

void test_dtc_obd_response_adds_codes(void)
{
    uint8_t data[] = {0x43, 0x01, 0x23, 0xC4, 0x56, 0x00, 0x00};

    dtc_handle_obd_response(data, sizeof(data));

    TEST_ASSERT_EQUAL_UINT32(2, s_dtc_count);
    TEST_ASSERT_EQUAL_STRING("P0123", s_dtc_codes[0]);
    TEST_ASSERT_EQUAL_STRING("U0456", s_dtc_codes[1]);
}

void test_dtc_obd_pid_odometer_updates_mileage(void)
{
    uint8_t data[] = {0x41, 0xA6, 0x00, 0x00, 0x27, 0x10};

    dtc_handle_obd_pid_response(data, sizeof(data));

    TEST_ASSERT_EQUAL_UINT32(1000, s_mileage);
}

void test_dtc_vin_response_sets_vin_and_calls_mqtt(void)
{
    uint8_t data[] = {
        0x49, 0x02, 0x01,
        '1', 'H', 'G', 'C', 'M', '8', '2', '6', '3', '3', 'A', '0', '0', '4', '3', '5', '2'
    };

    dtc_handle_vin_response(data, sizeof(data));

    TEST_ASSERT_EQUAL_STRING("1HGCM82633A004352", s_vin);
    TEST_ASSERT_EQUAL_INT(1, mqtt_stub_get_set_vin_calls());
    TEST_ASSERT_EQUAL_STRING("1HGCM82633A004352", mqtt_stub_get_last_vin());
}

void test_dtc_uds_response_adds_codes(void)
{
    uint8_t data[] = {0x59, 0x02, 0xFF, 0x12, 0x34, 0x56, 0x01, 0xAA, 0xBB, 0xCC, 0x02};

    dtc_handle_uds_response(data, sizeof(data));

    TEST_ASSERT_EQUAL_UINT32(2, s_dtc_count);
    TEST_ASSERT_EQUAL_STRING("0x123456", s_dtc_codes[0]);
    TEST_ASSERT_EQUAL_STRING("0xAABBCC", s_dtc_codes[1]);
}

void test_dtc_publish_sends_payload(void)
{
    strncpy(s_vin, "VIN123", sizeof(s_vin) - 1);
    s_mileage = 321;
    dtc_add_code("P0123");

    dtc_publish();

    TEST_ASSERT_EQUAL_INT(1, mqtt_stub_get_publish_calls());
    TEST_ASSERT_EQUAL_STRING("VIN123", mqtt_stub_get_last_vin());
    TEST_ASSERT_NOT_NULL(strstr(mqtt_stub_get_last_payload(), "P0123"));
    TEST_ASSERT_NOT_NULL(strstr(mqtt_stub_get_last_payload(), "\"mileage\":321"));
}

void test_dtc_send_requests_calls_isotp_send(void)
{
    dtc_send_requests();

    TEST_ASSERT_EQUAL_INT(4, isotp_stub_get_send_calls());
    TEST_ASSERT_EQUAL_UINT32(2, isotp_stub_get_last_send_len());
}

void test_dtc_init_requires_can_handle(void)
{
    s_can_handle = NULL;

    TEST_ASSERT_EQUAL(ESP_ERR_INVALID_STATE, dtc_reporter_init());
    TEST_ASSERT_FALSE(s_ready);
}

void test_dtc_init_is_idempotent(void)
{
    TEST_ASSERT_EQUAL(ESP_OK, dtc_reporter_init());
    TEST_ASSERT_TRUE(s_ready);
    TEST_ASSERT_EQUAL(ESP_OK, dtc_reporter_init());
}

int main(void)
{
    UNITY_BEGIN();

    RUN_TEST(test_dtc_obd_response_adds_codes);
    RUN_TEST(test_dtc_obd_pid_odometer_updates_mileage);
    RUN_TEST(test_dtc_vin_response_sets_vin_and_calls_mqtt);
    RUN_TEST(test_dtc_uds_response_adds_codes);
    RUN_TEST(test_dtc_publish_sends_payload);
    RUN_TEST(test_dtc_send_requests_calls_isotp_send);
    RUN_TEST(test_dtc_init_requires_can_handle);
    RUN_TEST(test_dtc_init_is_idempotent);

    return UNITY_END();
}
