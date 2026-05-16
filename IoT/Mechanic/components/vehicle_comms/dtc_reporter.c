#include "dtc_reporter.h"

#include <stdarg.h>
#include <stdbool.h>
#include <stdio.h>
#include <string.h>

#include "canmodule.h"
#include "esp_log.h"
#include "esp_timer.h"
#include "esp_twai.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "isotp.h"
#include "local_mqtt.h"

// CRITICAL: ISO-TP polling MUST be fast (1-10ms)
#define DTC_POLL_PERIOD_MS 5
#define DTC_POLL_INTERVAL_US (8ULL * 60ULL * 60ULL * 1000000ULL)
#define DTC_RESPONSE_WINDOW_US (5ULL * 1000000ULL)

#define DTC_MAX_CODES 32
#define DTC_CODE_MAX_LEN 12

#define DTC_TX_BUFFER_SIZE 32
#define DTC_RX_BUFFER_SIZE 256

#define OBD_FUNCTIONAL_REQ_ID 0x7DF
#define OBD_ENGINE_RESP_ID 0x7E8

#define OBD_SERVICE_DTC 0x03
#define OBD_SERVICE_DTC_RESP 0x43

#define OBD_SERVICE_CURRENT_DATA 0x01
#define OBD_SERVICE_CURRENT_DATA_RESP 0x41
#define OBD_PID_ODOMETER 0xA6

#define OBD_SERVICE_VEHICLE_INFO 0x09
#define OBD_SERVICE_VEHICLE_INFO_RESP 0x49
#define OBD_PID_VIN 0x02

#define UDS_SERVICE_READ_DTC 0x19
#define UDS_SUBFUNC_REPORT_BY_STATUS 0x02
#define UDS_NEGATIVE_RESPONSE 0x7F
#define UDS_POSITIVE_RESP_BASE 0x40

static const char *TAG = "dtc_reporter";

// Direct isotp-c integration variables
static IsoTpLink s_isotp_link;
static uint8_t s_isotp_tx_buf[DTC_TX_BUFFER_SIZE];
static uint8_t s_isotp_rx_buf[DTC_RX_BUFFER_SIZE];

static bool s_ready = false;

static char s_dtc_codes[DTC_MAX_CODES][DTC_CODE_MAX_LEN];
static size_t s_dtc_count = 0;

static char s_vin[20] = {0};
static uint32_t s_mileage = 0;

static uint64_t s_last_request_us = 0;
static uint64_t s_request_start_us = 0;
static bool s_waiting_for_response = false;

// --- ISO-TP C Library Hooks ---

uint32_t isotp_user_get_us(void) { return (uint32_t)esp_timer_get_time(); }

void isotp_user_debug(const char *message, ...) {
  va_list args;
  va_start(args, message);
  esp_log_writev(ESP_LOG_DEBUG, "isotp", message, args);
  va_end(args);
}

int isotp_user_send_can(const uint32_t arbitration_id, const uint8_t *data,
                        const uint8_t size) {
  twai_node_handle_t node = canmodule_get_twai_handle();
  if (!node)
    return ISOTP_RET_ERROR;

  twai_frame_t tx_msg = {0};
  tx_msg.header.id = arbitration_id;
  tx_msg.header.ide = false; // Standard 11-bit ID
  tx_msg.header.rtr = false;
  tx_msg.buffer = (uint8_t *)data;
  tx_msg.buffer_len = size;

  esp_err_t ret = twai_node_transmit(node, &tx_msg, pdMS_TO_TICKS(10));
  return (ret == ESP_OK) ? ISOTP_RET_OK : ISOTP_RET_ERROR;
}

// --- Application Logic ---

void dtc_reporter_feed_frame(uint32_t id, const uint8_t *data, uint8_t len) {
  // Only feed frames that match our target response ID
  if (id == OBD_ENGINE_RESP_ID) {
    isotp_on_can_message(&s_isotp_link, data, len);
  }
}

static void dtc_reset_list(void) {
  s_dtc_count = 0;
  memset(s_dtc_codes, 0, sizeof(s_dtc_codes));
}

static void dtc_add_code(const char *code) {
  if (!code || code[0] == '\0' || s_dtc_count >= DTC_MAX_CODES)
    return;
  for (size_t i = 0; i < s_dtc_count; ++i) {
    if (strncmp(s_dtc_codes[i], code, DTC_CODE_MAX_LEN) == 0)
      return;
  }
  strncpy(s_dtc_codes[s_dtc_count], code, DTC_CODE_MAX_LEN - 1);
  s_dtc_codes[s_dtc_count][DTC_CODE_MAX_LEN - 1] = '\0';
  s_dtc_count++;
}

static void dtc_decode_obd(uint8_t b1, uint8_t b2, char *out, size_t out_len) {
  static const char type_map[4] = {'P', 'C', 'B', 'U'};
  uint8_t type = (b1 >> 6) & 0x03;
  uint8_t digit1 = (b1 >> 4) & 0x03;
  uint8_t digit2 = b1 & 0x0F;
  uint8_t digit3 = (b2 >> 4) & 0x0F;
  uint8_t digit4 = b2 & 0x0F;
  snprintf(out, out_len, "%c%u%X%X%X", type_map[type], digit1, digit2, digit3,
           digit4);
}

static void dtc_handle_obd_response(const uint8_t *data, uint32_t len) {
  if (!data || len < 2 || data[0] != OBD_SERVICE_DTC_RESP)
    return;
  for (uint32_t i = 1; i + 1 < len; i += 2) {
    if (data[i] == 0x00 && data[i + 1] == 0x00)
      break;
    char code[DTC_CODE_MAX_LEN];
    dtc_decode_obd(data[i], data[i + 1], code, sizeof(code));
    dtc_add_code(code);
  }
}

static void dtc_handle_obd_pid_response(const uint8_t *data, uint32_t len) {
  if (!data || len < 2 || data[0] != OBD_SERVICE_CURRENT_DATA_RESP)
    return;
  if (data[1] == OBD_PID_ODOMETER && len >= 6) {
    uint32_t raw = ((uint32_t)data[2] << 24) | ((uint32_t)data[3] << 16) |
                   ((uint32_t)data[4] << 8) | data[5];
    s_mileage = raw / 10U;
  }
}

static void dtc_handle_vin_response(const uint8_t *data, uint32_t len) {
  if (!data || len < 3 || data[0] != OBD_SERVICE_VEHICLE_INFO_RESP ||
      data[1] != OBD_PID_VIN)
    return;
  size_t vin_len = 0;
  for (uint32_t i = 3; i < len && vin_len < sizeof(s_vin) - 1; ++i) {
    uint8_t ch = data[i];
    if (ch == 0 || ch == ' ')
      continue;
    if (ch >= 0x20 && ch <= 0x7E)
      s_vin[vin_len++] = (char)ch;
  }
  s_vin[vin_len] = '\0';
  if (s_vin[0] != '\0')
    mqtt_module_set_vin(s_vin);
}

static void dtc_handle_uds_response(const uint8_t *data, uint32_t len) {
  if (!data || len < 4 || data[0] == UDS_NEGATIVE_RESPONSE)
    return;
  if (data[0] != (UDS_SERVICE_READ_DTC + UDS_POSITIVE_RESP_BASE) ||
      data[1] != UDS_SUBFUNC_REPORT_BY_STATUS)
    return;
  for (uint32_t i = 3; i + 3 < len; i += 4) {
    char code[DTC_CODE_MAX_LEN];
    snprintf(code, sizeof(code), "0x%02X%02X%02X", data[i], data[i + 1],
             data[i + 2]);
    dtc_add_code(code);
  }
}

static void dtc_check_receive(void) {
  uint8_t rx_buffer[DTC_RX_BUFFER_SIZE];
  uint32_t received_size = 0;

  while (isotp_receive(&s_isotp_link, rx_buffer, sizeof(rx_buffer),
                       &received_size) == ISOTP_RET_OK) {
    if (received_size == 0)
      break;
    dtc_handle_obd_response(rx_buffer, received_size);
    dtc_handle_obd_pid_response(rx_buffer, received_size);
    dtc_handle_vin_response(rx_buffer, received_size);
    dtc_handle_uds_response(rx_buffer, received_size);
  }
}

static void dtc_publish(void) {
  if (s_dtc_count == 0)
    return;

  char payload[1024]; // Increased size to prevent overflow
  int offset =
      snprintf(payload, sizeof(payload), "{\"vin\":\"%s\",\"dtc_list\":[",
               s_vin[0] ? s_vin : "");
  if (offset < 0 || offset >= (int)sizeof(payload))
    return;

  for (size_t i = 0; i < s_dtc_count; ++i) {
    int written = snprintf(payload + offset, sizeof(payload) - (size_t)offset,
                           "%s\"%s\"", (i > 0) ? "," : "", s_dtc_codes[i]);
    if (written < 0)
      return;
    offset += written;
    if (offset >= (int)sizeof(payload))
      return;
  }

  int64_t ts_ms = esp_timer_get_time() / 1000;
  int written = snprintf(payload + offset, sizeof(payload) - (size_t)offset,
                         "],\"mileage\":%lu,\"ts_ms\":%lld}",
                         (unsigned long)s_mileage, (long long)ts_ms);
  if (written < 0 || offset + written >= (int)sizeof(payload))
    return;

  esp_err_t err = mqtt_module_publish_dtc(s_vin, payload);
  if (err != ESP_OK) {
    ESP_LOGW(TAG, "Failed to publish DTC payload: %s", esp_err_to_name(err));
  } else {
    ESP_LOGI(TAG, "Published DTC payload: %s", payload);
  }
}

static void dtc_reporter_task(void *arg) {
  (void)arg;

  // A simple state machine to prevent sending requests simultaneously
  enum {
    REQ_IDLE,
    REQ_OBD,
    REQ_UDS,
    REQ_ODO,
    REQ_VIN,
    REQ_WAIT
  } req_state = REQ_IDLE;

  while (true) {
    if (!s_ready) {
      vTaskDelay(pdMS_TO_TICKS(DTC_POLL_PERIOD_MS));
      continue;
    }

    isotp_poll(&s_isotp_link);
    uint64_t now = esp_timer_get_time();

    // Check if it's time to start a new sequence
    if (req_state == REQ_IDLE &&
        (now - s_last_request_us) >= DTC_POLL_INTERVAL_US) {
      dtc_reset_list();
      req_state = REQ_OBD;
      s_last_request_us = now;
      s_request_start_us = now;
      s_waiting_for_response = true;
    }

    // Only send the next request when ISO-TP is not busy
    if (req_state != REQ_IDLE && req_state != REQ_WAIT &&
        s_isotp_link.send_status == ISOTP_SEND_STATUS_IDLE) {
      if (req_state == REQ_OBD) {
        uint8_t req[] = {OBD_SERVICE_DTC};
        isotp_send(&s_isotp_link, req, sizeof(req));
        req_state = REQ_UDS;
      } else if (req_state == REQ_UDS) {
        uint8_t req[] = {UDS_SERVICE_READ_DTC, UDS_SUBFUNC_REPORT_BY_STATUS,
                         0xFF};
        isotp_send(&s_isotp_link, req, sizeof(req));
        req_state = REQ_ODO;
      } else if (req_state == REQ_ODO) {
        uint8_t req[] = {OBD_SERVICE_CURRENT_DATA, OBD_PID_ODOMETER};
        isotp_send(&s_isotp_link, req, sizeof(req));
        req_state = REQ_VIN;
      } else if (req_state == REQ_VIN) {
        uint8_t req[] = {OBD_SERVICE_VEHICLE_INFO, OBD_PID_VIN};
        isotp_send(&s_isotp_link, req, sizeof(req));
        req_state = REQ_WAIT;
      }
    }

    if (s_waiting_for_response) {
      dtc_check_receive();
      if ((now - s_request_start_us) >= DTC_RESPONSE_WINDOW_US) {
        dtc_publish();
        s_waiting_for_response = false;
        req_state = REQ_IDLE;
      }
    }

    vTaskDelay(pdMS_TO_TICKS(DTC_POLL_PERIOD_MS));
  }
}

esp_err_t dtc_reporter_init(void) {
  if (s_ready)
    return ESP_OK;

  // Note: We no longer need to grab the TWAI handle here, we just init the
  // ISO-TP memory
  isotp_init_link(&s_isotp_link, OBD_FUNCTIONAL_REQ_ID, s_isotp_tx_buf,
                  sizeof(s_isotp_tx_buf), s_isotp_rx_buf,
                  sizeof(s_isotp_rx_buf));

  s_isotp_link.receive_arbitration_id = OBD_ENGINE_RESP_ID;

  s_ready = true;
  return ESP_OK;
}

void dtc_reporter_start_task(void) {
  xTaskCreate(dtc_reporter_task, "dtc_reporter_task", 4096, NULL, 5, NULL);
}