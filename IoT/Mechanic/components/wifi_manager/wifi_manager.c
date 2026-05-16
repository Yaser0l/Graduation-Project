#include "wifi_manager.h"

#include <stdbool.h>
#include <string.h>

#include "driver/gpio.h"
#include "esp_event.h"
#include "esp_log.h"
#include "esp_wifi.h"
#include "freertos/FreeRTOS.h"
#include "freertos/event_groups.h"
#include "freertos/task.h"
#include "sdkconfig.h"

#include "network_events.h"

#define WIFI_CONNECT_TIMEOUT_MS CONFIG_WIFI_MANAGER_CONNECT_TIMEOUT_MS
#define WIFI_RETRY_LOOP_DELAY_MS CONFIG_WIFI_MANAGER_RETRY_LOOP_DELAY_MS
#define LED_BLINK_INTERVAL_MS CONFIG_WIFI_MANAGER_LED_BLINK_INTERVAL_MS

#define BLINK_GPIO CONFIG_WIFI_MANAGER_STATUS_LED_GPIO
#define LED_ON_LEVEL CONFIG_WIFI_MANAGER_LED_ON_LEVEL
#define LED_OFF_LEVEL CONFIG_WIFI_MANAGER_LED_OFF_LEVEL

#if CONFIG_WIFI_MANAGER_AP_AUTH_OPEN
#define WIFI_MANAGER_AP_AUTHMODE WIFI_AUTH_OPEN
#elif CONFIG_WIFI_MANAGER_AP_AUTH_WPA_PSK
#define WIFI_MANAGER_AP_AUTHMODE WIFI_AUTH_WPA_PSK
#elif CONFIG_WIFI_MANAGER_AP_AUTH_WPA2_PSK
#define WIFI_MANAGER_AP_AUTHMODE WIFI_AUTH_WPA2_PSK
#elif CONFIG_WIFI_MANAGER_AP_AUTH_WPA_WPA2_PSK
#define WIFI_MANAGER_AP_AUTHMODE WIFI_AUTH_WPA_WPA2_PSK
#elif CONFIG_WIFI_MANAGER_AP_AUTH_WPA3_PSK
#define WIFI_MANAGER_AP_AUTHMODE WIFI_AUTH_WPA3_PSK
#elif CONFIG_WIFI_MANAGER_AP_AUTH_WPA2_WPA3_PSK
#define WIFI_MANAGER_AP_AUTHMODE WIFI_AUTH_WPA2_WPA3_PSK
#else
#define WIFI_MANAGER_AP_AUTHMODE WIFI_AUTH_OPEN
#endif

#if CONFIG_WIFI_MANAGER_STA_AUTH_OPEN
#define WIFI_MANAGER_STA_AUTHMODE WIFI_AUTH_OPEN
#elif CONFIG_WIFI_MANAGER_STA_AUTH_WEP
#define WIFI_MANAGER_STA_AUTHMODE WIFI_AUTH_WEP
#elif CONFIG_WIFI_MANAGER_STA_AUTH_WPA_PSK
#define WIFI_MANAGER_STA_AUTHMODE WIFI_AUTH_WPA_PSK
#elif CONFIG_WIFI_MANAGER_STA_AUTH_WPA2_PSK
#define WIFI_MANAGER_STA_AUTHMODE WIFI_AUTH_WPA2_PSK
#elif CONFIG_WIFI_MANAGER_STA_AUTH_WPA_WPA2_PSK
#define WIFI_MANAGER_STA_AUTHMODE WIFI_AUTH_WPA_WPA2_PSK
#elif CONFIG_WIFI_MANAGER_STA_AUTH_WPA3_PSK
#define WIFI_MANAGER_STA_AUTHMODE WIFI_AUTH_WPA3_PSK
#elif CONFIG_WIFI_MANAGER_STA_AUTH_WPA2_WPA3_PSK
#define WIFI_MANAGER_STA_AUTHMODE WIFI_AUTH_WPA2_WPA3_PSK
#elif CONFIG_WIFI_MANAGER_STA_AUTH_WAPI_PSK
#define WIFI_MANAGER_STA_AUTHMODE WIFI_AUTH_WAPI_PSK
#else
#define WIFI_MANAGER_STA_AUTHMODE WIFI_AUTH_WPA2_PSK
#endif

#if CONFIG_WIFI_MANAGER_STA_PMF_CAPABLE
#define WIFI_MANAGER_STA_PMF_CAPABLE 1
#else
#define WIFI_MANAGER_STA_PMF_CAPABLE 0
#endif

#if CONFIG_WIFI_MANAGER_STA_PMF_REQUIRED
#define WIFI_MANAGER_STA_PMF_REQUIRED 1
#else
#define WIFI_MANAGER_STA_PMF_REQUIRED 0
#endif

static const char *TAG = "wifi_manager";
static EventGroupHandle_t s_wifi_event_group;
static const int WIFI_CONNECTED_BIT = BIT0;

static saved_ap_store_t s_ap_store = {0};
static bool s_config_ap = false;
static bool s_should_connect = false;

static void wifi_manager_refresh_store_from_nvs(void) {
  saved_ap_store_t store = {0};
  if (wifi_store_load(&store) == ESP_OK) {
    s_ap_store = store;
  }
}

static void wifi_status_led_init(void) {
  gpio_reset_pin(BLINK_GPIO);
  gpio_set_direction(BLINK_GPIO, GPIO_MODE_OUTPUT);
  gpio_set_level(BLINK_GPIO, LED_OFF_LEVEL);
}

static bool is_wifi_connected(void) {
  EventBits_t bits = xEventGroupGetBits(s_wifi_event_group);
  return (bits & WIFI_CONNECTED_BIT) != 0;
}

static void stop_config_ap(void) {
  if (!s_config_ap) {
    return;
  }

  ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_STA));
  s_config_ap = false;
  ESP_LOGI(TAG, "Configuration AP stopped");
}

void wifi_manager_start_config_ap(void) {
  if (s_config_ap) {
    return;
  }

  wifi_config_t ap_config = {0};
  size_t ssid_len = strlen(CONFIG_WIFI_MANAGER_AP_SSID);
  if (ssid_len >= sizeof(ap_config.ap.ssid)) {
    ssid_len = sizeof(ap_config.ap.ssid) - 1;
  }

  strncpy((char *)ap_config.ap.ssid, CONFIG_WIFI_MANAGER_AP_SSID,
          sizeof(ap_config.ap.ssid) - 1);
  ap_config.ap.ssid_len = (uint8_t)ssid_len;

  strncpy((char *)ap_config.ap.password, CONFIG_WIFI_MANAGER_AP_PASSWORD,
          sizeof(ap_config.ap.password) - 1);
  ap_config.ap.channel = CONFIG_WIFI_MANAGER_AP_CHANNEL;
  ap_config.ap.max_connection = CONFIG_WIFI_MANAGER_AP_MAX_CONNECTIONS;
  ap_config.ap.authmode = WIFI_MANAGER_AP_AUTHMODE;
  if (ap_config.ap.password[0] == '\0') {
    ap_config.ap.authmode = WIFI_AUTH_OPEN;
  }

  ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_APSTA));
  ESP_ERROR_CHECK(esp_wifi_set_config(WIFI_IF_AP, &ap_config));
  s_config_ap = true;
  ESP_LOGI(TAG, "Configuration AP started: ESP32_Config");
}

static void try_connect_saved_aps(void) {
  if (s_ap_store.count == 0) {
    wifi_manager_start_config_ap();
    return;
  }

  for (uint8_t i = 0; i < s_ap_store.count; ++i) {
    wifi_config_t sta_config = {0};
    strncpy((char *)sta_config.sta.ssid, s_ap_store.entries[i].ssid,
            sizeof(sta_config.sta.ssid) - 1);
    strncpy((char *)sta_config.sta.password, s_ap_store.entries[i].passphrase,
            sizeof(sta_config.sta.password) - 1);
    sta_config.sta.threshold.authmode = WIFI_MANAGER_STA_AUTHMODE;
    sta_config.sta.pmf_cfg.capable = WIFI_MANAGER_STA_PMF_CAPABLE;
    sta_config.sta.pmf_cfg.required = WIFI_MANAGER_STA_PMF_REQUIRED;

    ESP_LOGI(TAG, "Trying AP: %s", s_ap_store.entries[i].ssid);
    ESP_ERROR_CHECK(esp_wifi_set_config(WIFI_IF_STA, &sta_config));
    ESP_ERROR_CHECK(esp_wifi_connect());

    EventBits_t bits =
        xEventGroupWaitBits(s_wifi_event_group, WIFI_CONNECTED_BIT, pdFALSE,
                            pdFALSE, pdMS_TO_TICKS(WIFI_CONNECT_TIMEOUT_MS));

    if (bits & WIFI_CONNECTED_BIT) {
      ESP_LOGI(TAG, "Connected to: %s", s_ap_store.entries[i].ssid);
      stop_config_ap();
      s_should_connect = false;
      return;
    }

    ESP_LOGW(TAG, "Connection failed for: %s", s_ap_store.entries[i].ssid);
    esp_wifi_disconnect();
  }

  wifi_manager_start_config_ap();
}

static void wifi_manager_task_step(void) {
  if (s_should_connect && !is_wifi_connected()) {
    try_connect_saved_aps();
  }

  if (is_wifi_connected()) {
    stop_config_ap();
  } else if (s_ap_store.count == 0) {
    wifi_manager_start_config_ap();
  }
}

static void wifi_manager_task(void *arg) {
  (void)arg;
  while (true) {
    wifi_manager_task_step();

    vTaskDelay(pdMS_TO_TICKS(WIFI_RETRY_LOOP_DELAY_MS));
  }
}

static void wifi_status_led_task_step(bool *led_on) {
  if (is_wifi_connected()) {
    gpio_set_level(BLINK_GPIO, LED_ON_LEVEL);
    return;
  }

  *led_on = !*led_on;
  gpio_set_level(BLINK_GPIO, *led_on ? LED_ON_LEVEL : LED_OFF_LEVEL);
}

static void wifi_status_led_task(void *arg) {
  (void)arg;
  bool led_on = false;

  while (true) {
    wifi_status_led_task_step(&led_on);

    vTaskDelay(pdMS_TO_TICKS(LED_BLINK_INTERVAL_MS));
  }
}

static void wifi_event_handler(void *arg, esp_event_base_t event_base,
                               int32_t event_id, void *event_data) {
  (void)arg;
  (void)event_data;

  if (event_base == WIFI_EVENT && event_id == WIFI_EVENT_STA_DISCONNECTED) {
    xEventGroupClearBits(s_wifi_event_group, WIFI_CONNECTED_BIT);
    network_events_post(NETWORK_EVENT_DOWN, NULL, 0);
    if (s_ap_store.count > 0) {
      s_should_connect = true;
    }
  } else if (event_base == IP_EVENT && event_id == IP_EVENT_STA_GOT_IP) {
    xEventGroupSetBits(s_wifi_event_group, WIFI_CONNECTED_BIT);
    network_events_post(NETWORK_EVENT_UP, NULL, 0);
    s_should_connect = false;
  }
}

static void network_request_handler(void *arg, esp_event_base_t event_base,
                                    int32_t event_id, void *event_data) {
  (void)arg;
  (void)event_base;
  (void)event_id;
  (void)event_data;

  wifi_manager_request_connect();
}

void wifi_manager_init(const saved_ap_store_t *initial_store) {
  memset(&s_ap_store, 0, sizeof(s_ap_store));
  if (initial_store) {
    memcpy(&s_ap_store, initial_store, sizeof(s_ap_store));
  }

  s_wifi_event_group = xEventGroupCreate();

  ESP_ERROR_CHECK(esp_event_handler_instance_register(
      WIFI_EVENT, ESP_EVENT_ANY_ID, &wifi_event_handler, NULL, NULL));
  ESP_ERROR_CHECK(esp_event_handler_instance_register(
      IP_EVENT, IP_EVENT_STA_GOT_IP, &wifi_event_handler, NULL, NULL));
  ESP_ERROR_CHECK(esp_event_handler_instance_register(
      NETWORK_EVENT, NETWORK_EVENT_REQUEST, &network_request_handler, NULL,
      NULL));
}

void wifi_manager_start_task(void) {
  xTaskCreate(wifi_manager_task, "wifi_manager_task", 4096, NULL, 5, NULL);
  wifi_status_led_init();
  xTaskCreate(wifi_status_led_task, "wifi_status_led_task", 2048, NULL, 4,
              NULL);
}

void wifi_manager_notify_store_changed(const saved_ap_store_t *store) {
  if (!store) {
    return;
  }

  memcpy(&s_ap_store, store, sizeof(s_ap_store));
}

void wifi_manager_request_connect(void) {
  wifi_manager_refresh_store_from_nvs();
  s_should_connect = true;
}

bool wifi_manager_is_connected(void) { return is_wifi_connected(); }
