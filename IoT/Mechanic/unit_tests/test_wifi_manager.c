#include <string.h>

#include "unity.h"

#include "esp_event.h"
#include "esp_wifi.h"
#include "freertos/event_groups.h"
#include "driver/gpio.h"

#include "wifi_store.h"

#include "wifi_manager.c"

static void wifi_manager_test_reset(void)
{
    memset(&s_ap_store, 0, sizeof(s_ap_store));
    s_config_ap = false;
    s_should_connect = false;
    s_wifi_event_group = NULL;

    esp_event_stub_reset();
    esp_wifi_stub_reset();
    event_group_stub_reset();
    gpio_stub_reset();
}

void setUp(void)
{
    wifi_manager_test_reset();
}

void tearDown(void)
{
}

void test_wifi_manager_init_registers_events_and_copies_store(void)
{
    saved_ap_store_t init_store = {0};
    init_store.count = 1;
    strncpy(init_store.entries[0].ssid, "ssid", sizeof(init_store.entries[0].ssid) - 1);

    wifi_manager_init(&init_store);

    TEST_ASSERT_NOT_NULL(s_wifi_event_group);
    TEST_ASSERT_EQUAL_UINT8(1, s_ap_store.count);
    TEST_ASSERT_EQUAL_STRING("ssid", s_ap_store.entries[0].ssid);
    TEST_ASSERT_EQUAL_INT(2, esp_event_stub_get_register_calls());
}

void test_wifi_manager_notify_store_changed_ignores_null(void)
{
    s_ap_store.count = 1;

    wifi_manager_notify_store_changed(NULL);

    TEST_ASSERT_EQUAL_UINT8(1, s_ap_store.count);
}

void test_wifi_manager_request_connect_sets_flag(void)
{
    TEST_ASSERT_FALSE(s_should_connect);

    wifi_manager_request_connect();

    TEST_ASSERT_TRUE(s_should_connect);
}

void test_wifi_manager_start_config_ap_is_idempotent(void)
{
    wifi_manager_start_config_ap();

    TEST_ASSERT_TRUE(s_config_ap);
    TEST_ASSERT_EQUAL_INT(1, esp_wifi_stub_get_set_mode_calls());
    TEST_ASSERT_EQUAL_INT(1, esp_wifi_stub_get_set_config_calls());
    TEST_ASSERT_EQUAL(WIFI_MODE_APSTA, esp_wifi_stub_get_last_mode());

    wifi_manager_start_config_ap();

    TEST_ASSERT_EQUAL_INT(1, esp_wifi_stub_get_set_mode_calls());
    TEST_ASSERT_EQUAL_INT(1, esp_wifi_stub_get_set_config_calls());
}

void test_wifi_event_handler_disconnect_sets_reconnect_flag(void)
{
    s_ap_store.count = 1;
    event_group_stub_set_bits(WIFI_CONNECTED_BIT);

    wifi_event_handler(NULL, WIFI_EVENT, WIFI_EVENT_STA_DISCONNECTED, NULL);

    TEST_ASSERT_EQUAL_UINT32(0, event_group_stub_get_bits() & WIFI_CONNECTED_BIT);
    TEST_ASSERT_TRUE(s_should_connect);
}

void test_wifi_event_handler_got_ip_sets_connected(void)
{
    s_should_connect = true;

    wifi_event_handler(NULL, IP_EVENT, IP_EVENT_STA_GOT_IP, NULL);

    TEST_ASSERT_TRUE(event_group_stub_get_bits() & WIFI_CONNECTED_BIT);
    TEST_ASSERT_FALSE(s_should_connect);
}

void test_try_connect_saved_aps_starts_config_when_empty(void)
{
    s_ap_store.count = 0;

    try_connect_saved_aps();

    TEST_ASSERT_TRUE(s_config_ap);
    TEST_ASSERT_EQUAL_INT(1, esp_wifi_stub_get_set_mode_calls());
    TEST_ASSERT_EQUAL(WIFI_MODE_APSTA, esp_wifi_stub_get_last_mode());
}

void test_try_connect_saved_aps_connects_and_stops_ap(void)
{
    s_ap_store.count = 1;
    strncpy(s_ap_store.entries[0].ssid, "home", sizeof(s_ap_store.entries[0].ssid) - 1);
    strncpy(s_ap_store.entries[0].passphrase, "pass", sizeof(s_ap_store.entries[0].passphrase) - 1);
    s_config_ap = true;
    s_should_connect = true;
    event_group_stub_set_wait_bits(WIFI_CONNECTED_BIT);

    try_connect_saved_aps();

    TEST_ASSERT_EQUAL_INT(1, esp_wifi_stub_get_connect_calls());
    TEST_ASSERT_EQUAL_INT(1, esp_wifi_stub_get_set_config_calls());
    TEST_ASSERT_EQUAL_INT(1, esp_wifi_stub_get_set_mode_calls());
    TEST_ASSERT_EQUAL(WIFI_MODE_STA, esp_wifi_stub_get_last_mode());
    TEST_ASSERT_FALSE(s_should_connect);
    TEST_ASSERT_FALSE(s_config_ap);
}

int main(void)
{
    UNITY_BEGIN();

    RUN_TEST(test_wifi_manager_init_registers_events_and_copies_store);
    RUN_TEST(test_wifi_manager_notify_store_changed_ignores_null);
    RUN_TEST(test_wifi_manager_request_connect_sets_flag);
    RUN_TEST(test_wifi_manager_start_config_ap_is_idempotent);
    RUN_TEST(test_wifi_event_handler_disconnect_sets_reconnect_flag);
    RUN_TEST(test_wifi_event_handler_got_ip_sets_connected);
    RUN_TEST(test_try_connect_saved_aps_starts_config_when_empty);
    RUN_TEST(test_try_connect_saved_aps_connects_and_stops_ap);

    return UNITY_END();
}
