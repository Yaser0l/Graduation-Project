#include <string.h>

#include "unity.h"

#include "driver/gpio.h"
#include "esp_event.h"
#include "esp_wifi.h"
#include "freertos/event_groups.h"
#include "nvs.h"

#include "wifi_store.h"

#include "wifi_manager.c"

static void wifi_manager_test_reset(void) {
  memset(&s_ap_store, 0, sizeof(s_ap_store));
  s_config_ap = false;
  s_should_connect = false;
  s_wifi_event_group = NULL;

  esp_event_stub_reset();
  esp_wifi_stub_reset();
  event_group_stub_reset();
  gpio_stub_reset();
  nvs_stub_reset();
}

void setUp(void) { wifi_manager_test_reset(); }

void tearDown(void) {}

void test_wifi_manager_init_registers_events_and_copies_store(void) {
  saved_ap_store_t init_store = {0};
  init_store.count = 1;
  strncpy(init_store.entries[0].ssid, "ssid",
          sizeof(init_store.entries[0].ssid) - 1);

  wifi_manager_init(&init_store);

  TEST_ASSERT_NOT_NULL(s_wifi_event_group);
  TEST_ASSERT_EQUAL_UINT8(1, s_ap_store.count);
  TEST_ASSERT_EQUAL_STRING("ssid", s_ap_store.entries[0].ssid);
  TEST_ASSERT_EQUAL_INT(3, esp_event_stub_get_register_calls());
}

void test_wifi_manager_notify_store_changed_ignores_null(void) {
  s_ap_store.count = 1;

  wifi_manager_notify_store_changed(NULL);

  TEST_ASSERT_EQUAL_UINT8(1, s_ap_store.count);
}

void test_wifi_manager_notify_store_changed_copies_store(void) {
  saved_ap_store_t store = {0};
  store.count = 2;
  strncpy(store.entries[0].ssid, "ssid-1", sizeof(store.entries[0].ssid) - 1);
  strncpy(store.entries[0].passphrase, "pass-1",
          sizeof(store.entries[0].passphrase) - 1);
  strncpy(store.entries[1].ssid, "ssid-2", sizeof(store.entries[1].ssid) - 1);
  strncpy(store.entries[1].passphrase, "pass-2",
          sizeof(store.entries[1].passphrase) - 1);

  wifi_manager_notify_store_changed(&store);

  TEST_ASSERT_EQUAL_UINT8(2, s_ap_store.count);
  TEST_ASSERT_EQUAL_STRING("ssid-1", s_ap_store.entries[0].ssid);
  TEST_ASSERT_EQUAL_STRING("pass-1", s_ap_store.entries[0].passphrase);
  TEST_ASSERT_EQUAL_STRING("ssid-2", s_ap_store.entries[1].ssid);
  TEST_ASSERT_EQUAL_STRING("pass-2", s_ap_store.entries[1].passphrase);
}

void test_wifi_manager_request_connect_sets_flag(void) {
  TEST_ASSERT_FALSE(s_should_connect);

  wifi_manager_request_connect();

  TEST_ASSERT_TRUE(s_should_connect);
}

void test_wifi_manager_start_config_ap_is_idempotent(void) {
  wifi_manager_start_config_ap();

  TEST_ASSERT_TRUE(s_config_ap);
  TEST_ASSERT_EQUAL_INT(1, esp_wifi_stub_get_set_mode_calls());
  TEST_ASSERT_EQUAL_INT(1, esp_wifi_stub_get_set_config_calls());
  TEST_ASSERT_EQUAL(WIFI_MODE_APSTA, esp_wifi_stub_get_last_mode());

  wifi_manager_start_config_ap();

  TEST_ASSERT_EQUAL_INT(1, esp_wifi_stub_get_set_mode_calls());
  TEST_ASSERT_EQUAL_INT(1, esp_wifi_stub_get_set_config_calls());
}

void test_wifi_manager_start_task_initializes_led(void) {
  wifi_manager_start_task();

  TEST_ASSERT_EQUAL_INT(1, gpio_stub_get_reset_calls());
  TEST_ASSERT_EQUAL_INT(1, gpio_stub_get_set_direction_calls());
  TEST_ASSERT_EQUAL_INT(1, gpio_stub_get_set_level_calls());
  TEST_ASSERT_EQUAL_INT(LED_OFF_LEVEL, gpio_stub_get_last_level());
}

void test_stop_config_ap_is_noop_when_disabled(void) {
  s_config_ap = false;

  stop_config_ap();

  TEST_ASSERT_FALSE(s_config_ap);
  TEST_ASSERT_EQUAL_INT(0, esp_wifi_stub_get_set_mode_calls());
}

void test_stop_config_ap_switches_to_sta_when_enabled(void) {
  s_config_ap = true;

  stop_config_ap();

  TEST_ASSERT_FALSE(s_config_ap);
  TEST_ASSERT_EQUAL_INT(1, esp_wifi_stub_get_set_mode_calls());
  TEST_ASSERT_EQUAL(WIFI_MODE_STA, esp_wifi_stub_get_last_mode());
}

void test_wifi_manager_is_connected_reads_event_bits(void) {
  event_group_stub_set_bits(WIFI_CONNECTED_BIT);
  TEST_ASSERT_TRUE(wifi_manager_is_connected());

  event_group_stub_set_bits(0);
  TEST_ASSERT_FALSE(wifi_manager_is_connected());
}

void test_wifi_event_handler_disconnect_sets_reconnect_flag(void) {
  s_ap_store.count = 1;
  event_group_stub_set_bits(WIFI_CONNECTED_BIT);

  wifi_event_handler(NULL, WIFI_EVENT, WIFI_EVENT_STA_DISCONNECTED, NULL);

  TEST_ASSERT_EQUAL_UINT32(0, event_group_stub_get_bits() & WIFI_CONNECTED_BIT);
  TEST_ASSERT_TRUE(s_should_connect);
}

void test_wifi_event_handler_got_ip_sets_connected(void) {
  s_should_connect = true;

  wifi_event_handler(NULL, IP_EVENT, IP_EVENT_STA_GOT_IP, NULL);

  TEST_ASSERT_TRUE(event_group_stub_get_bits() & WIFI_CONNECTED_BIT);
  TEST_ASSERT_FALSE(s_should_connect);
}

void test_try_connect_saved_aps_starts_config_when_empty(void) {
  s_ap_store.count = 0;

  try_connect_saved_aps();

  TEST_ASSERT_TRUE(s_config_ap);
  TEST_ASSERT_EQUAL_INT(1, esp_wifi_stub_get_set_mode_calls());
  TEST_ASSERT_EQUAL(WIFI_MODE_APSTA, esp_wifi_stub_get_last_mode());
}

void test_try_connect_saved_aps_connects_and_stops_ap(void) {
  s_ap_store.count = 1;
  strncpy(s_ap_store.entries[0].ssid, "home",
          sizeof(s_ap_store.entries[0].ssid) - 1);
  strncpy(s_ap_store.entries[0].passphrase, "pass",
          sizeof(s_ap_store.entries[0].passphrase) - 1);
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

void test_try_connect_saved_aps_failure_disconnects_and_starts_ap(void) {
  s_ap_store.count = 2;
  strncpy(s_ap_store.entries[0].ssid, "ap-1",
          sizeof(s_ap_store.entries[0].ssid) - 1);
  strncpy(s_ap_store.entries[1].ssid, "ap-2",
          sizeof(s_ap_store.entries[1].ssid) - 1);
  event_group_stub_set_wait_bits(0);

  try_connect_saved_aps();

  TEST_ASSERT_EQUAL_INT(2, esp_wifi_stub_get_connect_calls());
  TEST_ASSERT_EQUAL_INT(2, esp_wifi_stub_get_disconnect_calls());
  TEST_ASSERT_TRUE(s_config_ap);
  TEST_ASSERT_EQUAL(WIFI_MODE_APSTA, esp_wifi_stub_get_last_mode());
}

void test_wifi_manager_task_step_starts_ap_when_no_saved(void) {
  s_ap_store.count = 0;
  s_config_ap = false;

  wifi_manager_task_step();

  TEST_ASSERT_TRUE(s_config_ap);
  TEST_ASSERT_EQUAL(WIFI_MODE_APSTA, esp_wifi_stub_get_last_mode());
}

void test_wifi_manager_task_step_clears_connect_flag_on_success(void) {
  s_ap_store.count = 1;
  strncpy(s_ap_store.entries[0].ssid, "home",
          sizeof(s_ap_store.entries[0].ssid) - 1);
  s_should_connect = true;
  s_config_ap = true;
  event_group_stub_set_wait_bits(WIFI_CONNECTED_BIT);

  wifi_manager_task_step();

  TEST_ASSERT_FALSE(s_should_connect);
  TEST_ASSERT_FALSE(s_config_ap);
}

void test_wifi_status_led_task_step_sets_on_when_connected(void) {
  bool led_on = false;
  event_group_stub_set_bits(WIFI_CONNECTED_BIT);

  wifi_status_led_task_step(&led_on);

  TEST_ASSERT_EQUAL_INT(LED_ON_LEVEL, gpio_stub_get_last_level());
  TEST_ASSERT_FALSE(led_on);
}

void test_wifi_status_led_task_step_blinks_when_disconnected(void) {
  bool led_on = false;
  event_group_stub_set_bits(0);

  wifi_status_led_task_step(&led_on);
  TEST_ASSERT_EQUAL_INT(LED_ON_LEVEL, gpio_stub_get_last_level());

  wifi_status_led_task_step(&led_on);
  TEST_ASSERT_EQUAL_INT(LED_OFF_LEVEL, gpio_stub_get_last_level());
}

int main(void) {
  UNITY_BEGIN();

  RUN_TEST(test_wifi_manager_init_registers_events_and_copies_store);
  RUN_TEST(test_wifi_manager_notify_store_changed_ignores_null);
  RUN_TEST(test_wifi_manager_notify_store_changed_copies_store);
  RUN_TEST(test_wifi_manager_request_connect_sets_flag);
  RUN_TEST(test_wifi_manager_start_config_ap_is_idempotent);
  RUN_TEST(test_wifi_manager_start_task_initializes_led);
  RUN_TEST(test_stop_config_ap_is_noop_when_disabled);
  RUN_TEST(test_stop_config_ap_switches_to_sta_when_enabled);
  RUN_TEST(test_wifi_manager_is_connected_reads_event_bits);
  RUN_TEST(test_wifi_event_handler_disconnect_sets_reconnect_flag);
  RUN_TEST(test_wifi_event_handler_got_ip_sets_connected);
  RUN_TEST(test_try_connect_saved_aps_starts_config_when_empty);
  RUN_TEST(test_try_connect_saved_aps_connects_and_stops_ap);
  RUN_TEST(test_try_connect_saved_aps_failure_disconnects_and_starts_ap);
  RUN_TEST(test_wifi_manager_task_step_starts_ap_when_no_saved);
  RUN_TEST(test_wifi_manager_task_step_clears_connect_flag_on_success);
  RUN_TEST(test_wifi_status_led_task_step_sets_on_when_connected);
  RUN_TEST(test_wifi_status_led_task_step_blinks_when_disconnected);

  return UNITY_END();
}
