#include "dtc_reporter.h"

#include <stdio.h>
#include <string.h>

#include "canmodule.h"
#include "esp_isotp.h"
#include "esp_log.h"
#include "esp_timer.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "mqtt.h"

#define DTC_POLL_PERIOD_MS 50
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

static esp_isotp_handle_t s_isotp = NULL;
static bool s_ready = false;

static char s_dtc_codes[DTC_MAX_CODES][DTC_CODE_MAX_LEN];
static size_t s_dtc_count = 0;

static char s_vin[20] = {0};
static uint32_t s_mileage = 0;

static uint64_t s_last_request_us = 0;
static uint64_t s_request_start_us = 0;
static bool s_waiting_for_response = false;

static void dtc_reset_list(void)
{
    s_dtc_count = 0;
    memset(s_dtc_codes, 0, sizeof(s_dtc_codes));
}

static void dtc_add_code(const char *code)
{
    if (!code || code[0] == '\0' || s_dtc_count >= DTC_MAX_CODES)
    {
        return;
    }

    for (size_t i = 0; i < s_dtc_count; ++i)
    {
        if (strncmp(s_dtc_codes[i], code, DTC_CODE_MAX_LEN) == 0)
        {
            return;
        }
    }

    strncpy(s_dtc_codes[s_dtc_count], code, DTC_CODE_MAX_LEN - 1);
    s_dtc_codes[s_dtc_count][DTC_CODE_MAX_LEN - 1] = '\0';
    s_dtc_count++;
}

static void dtc_decode_obd(uint8_t b1, uint8_t b2, char *out, size_t out_len)
{
    static const char type_map[4] = {'P', 'C', 'B', 'U'};
    uint8_t type = (b1 >> 6) & 0x03;
    uint8_t digit1 = (b1 >> 4) & 0x03;
    uint8_t digit2 = b1 & 0x0F;
    uint8_t digit3 = (b2 >> 4) & 0x0F;
    uint8_t digit4 = b2 & 0x0F;

    snprintf(out, out_len, "%c%u%X%X%X", type_map[type], digit1, digit2, digit3, digit4);
}

static void dtc_handle_obd_response(const uint8_t *data, uint32_t len)
{
    if (!data || len < 2)
    {
        return;
    }

    if (data[0] != OBD_SERVICE_DTC_RESP)
    {
        return;
    }

    for (uint32_t i = 1; i + 1 < len; i += 2)
    {
        if (data[i] == 0x00 && data[i + 1] == 0x00)
        {
            break;
        }

        char code[DTC_CODE_MAX_LEN];
        dtc_decode_obd(data[i], data[i + 1], code, sizeof(code));
        dtc_add_code(code);
    }
}

static void dtc_handle_obd_pid_response(const uint8_t *data, uint32_t len)
{
    if (!data || len < 2)
    {
        return;
    }

    if (data[0] != OBD_SERVICE_CURRENT_DATA_RESP)
    {
        return;
    }

    if (data[1] == OBD_PID_ODOMETER && len >= 6)
    {
        uint32_t raw = ((uint32_t)data[2] << 24) | ((uint32_t)data[3] << 16) | ((uint32_t)data[4] << 8) | data[5];
        s_mileage = raw / 10U;
    }
}

static void dtc_handle_vin_response(const uint8_t *data, uint32_t len)
{
    if (!data || len < 3)
    {
        return;
    }

    if (data[0] != OBD_SERVICE_VEHICLE_INFO_RESP || data[1] != OBD_PID_VIN)
    {
        return;
    }

    size_t vin_len = 0;
    for (uint32_t i = 3; i < len && vin_len < sizeof(s_vin) - 1; ++i)
    {
        uint8_t ch = data[i];
        if (ch == 0 || ch == ' ')
        {
            continue;
        }
        if (ch >= 0x20 && ch <= 0x7E)
        {
            s_vin[vin_len++] = (char)ch;
        }
    }
    s_vin[vin_len] = '\0';

    if (s_vin[0] != '\0')
    {
        mqtt_module_set_vin(s_vin);
    }
}

static void dtc_handle_uds_response(const uint8_t *data, uint32_t len)
{
    if (!data || len < 4)
    {
        return;
    }

    if (data[0] == UDS_NEGATIVE_RESPONSE)
    {
        return;
    }

    if (data[0] != (UDS_SERVICE_READ_DTC + UDS_POSITIVE_RESP_BASE) || data[1] != UDS_SUBFUNC_REPORT_BY_STATUS)
    {
        return;
    }

    for (uint32_t i = 3; i + 3 < len; i += 4)
    {
        char code[DTC_CODE_MAX_LEN];
        snprintf(code, sizeof(code), "0x%02X%02X%02X", data[i], data[i + 1], data[i + 2]);
        dtc_add_code(code);
    }
}

static void dtc_check_receive(void)
{
    uint8_t rx_buffer[DTC_RX_BUFFER_SIZE];
    uint32_t received_size = 0;

    while (esp_isotp_receive(s_isotp, rx_buffer, sizeof(rx_buffer), &received_size) == ESP_OK)
    {
        if (received_size == 0)
        {
            break;
        }

        dtc_handle_obd_response(rx_buffer, received_size);
        dtc_handle_obd_pid_response(rx_buffer, received_size);
        dtc_handle_vin_response(rx_buffer, received_size);
        dtc_handle_uds_response(rx_buffer, received_size);
    }
}

static void dtc_publish(void)
{
    if (s_dtc_count == 0)
    {
        return;
    }

    char payload[512];
    int offset = snprintf(payload, sizeof(payload),
                          "{\"vin\":\"%s\",\"dtc_list\":[",
                          s_vin[0] ? s_vin : "");
    if (offset < 0 || offset >= (int)sizeof(payload))
    {
        return;
    }

    for (size_t i = 0; i < s_dtc_count; ++i)
    {
        int written = snprintf(payload + offset, sizeof(payload) - (size_t)offset,
                               "%s\"%s\"",
                               (i > 0) ? "," : "",
                               s_dtc_codes[i]);
        if (written < 0)
        {
            return;
        }
        offset += written;
        if (offset >= (int)sizeof(payload))
        {
            return;
        }
    }

    int64_t ts_ms = esp_timer_get_time() / 1000;
    int written = snprintf(payload + offset, sizeof(payload) - (size_t)offset,
                           "],\"mileage\":%lu,\"ts_ms\":%lld}",
                           (unsigned long)s_mileage,
                           (long long)ts_ms);
    if (written < 0 || offset + written >= (int)sizeof(payload))
    {
        return;
    }

    esp_err_t err = mqtt_module_publish_dtc(s_vin, payload);
    if (err != ESP_OK)
    {
        ESP_LOGW(TAG, "Failed to publish DTC payload: %s", esp_err_to_name(err));
    }
    else
    {
        ESP_LOGI(TAG, "Published DTC payload: %s", payload);
    }
}

static void dtc_send_requests(void)
{
    uint8_t obd_req[] = {OBD_SERVICE_DTC};
    uint8_t obd_odometer_req[] = {OBD_SERVICE_CURRENT_DATA, OBD_PID_ODOMETER};
    uint8_t obd_vin_req[] = {OBD_SERVICE_VEHICLE_INFO, OBD_PID_VIN};
    uint8_t uds_req[] = {UDS_SERVICE_READ_DTC, UDS_SUBFUNC_REPORT_BY_STATUS, 0xFF};

    esp_err_t err = esp_isotp_send(s_isotp, obd_req, sizeof(obd_req));
    if (err != ESP_OK && err != ESP_ERR_NOT_FINISHED)
    {
        ESP_LOGW(TAG, "Failed to send OBD DTC request: %s", esp_err_to_name(err));
    }

    err = esp_isotp_send(s_isotp, uds_req, sizeof(uds_req));
    if (err != ESP_OK && err != ESP_ERR_NOT_FINISHED)
    {
        ESP_LOGW(TAG, "Failed to send UDS DTC request: %s", esp_err_to_name(err));
    }

    err = esp_isotp_send(s_isotp, obd_odometer_req, sizeof(obd_odometer_req));
    if (err != ESP_OK && err != ESP_ERR_NOT_FINISHED)
    {
        ESP_LOGW(TAG, "Failed to send OBD odometer request: %s", esp_err_to_name(err));
    }

    err = esp_isotp_send(s_isotp, obd_vin_req, sizeof(obd_vin_req));
    if (err != ESP_OK && err != ESP_ERR_NOT_FINISHED)
    {
        ESP_LOGW(TAG, "Failed to send OBD VIN request: %s", esp_err_to_name(err));
    }
}

static void dtc_reporter_task(void *arg)
{
    (void)arg;

    while (true)
    {
        if (!s_ready)
        {
            vTaskDelay(pdMS_TO_TICKS(DTC_POLL_PERIOD_MS));
            continue;
        }

        esp_isotp_poll(s_isotp);

        uint64_t now = esp_timer_get_time();
        if (!s_waiting_for_response && (now - s_last_request_us) >= DTC_POLL_INTERVAL_US)
        {
            dtc_reset_list();
            dtc_send_requests();
            s_last_request_us = now;
            s_request_start_us = now;
            s_waiting_for_response = true;
        }

        if (s_waiting_for_response)
        {
            dtc_check_receive();
            if ((now - s_request_start_us) >= DTC_RESPONSE_WINDOW_US)
            {
                dtc_publish();
                s_waiting_for_response = false;
            }
        }

        vTaskDelay(pdMS_TO_TICKS(DTC_POLL_PERIOD_MS));
    }
}

esp_err_t dtc_reporter_init(void)
{
    if (s_ready)
    {
        return ESP_OK;
    }

    twai_node_handle_t node = canmodule_get_twai_handle();
    if (!node)
    {
        return ESP_ERR_INVALID_STATE;
    }

    esp_isotp_config_t config = {
        .tx_id = OBD_FUNCTIONAL_REQ_ID,
        .rx_id = OBD_ENGINE_RESP_ID,
        .tx_buffer_size = DTC_TX_BUFFER_SIZE,
        .rx_buffer_size = DTC_RX_BUFFER_SIZE,
    };

    esp_err_t err = esp_isotp_new_transport_ex(node, &config, &s_isotp, false);
    if (err != ESP_OK)
    {
        return err;
    }

    s_ready = true;
    return ESP_OK;
}

void dtc_reporter_start_task(void)
{
    xTaskCreate(dtc_reporter_task, "dtc_reporter_task", 4096, NULL, 5, NULL);
}

void dtc_reporter_can_rx_isr(const twai_frame_t *rx_frame)
{
    if (!s_ready || !s_isotp)
    {
        return;
    }

    (void)esp_isotp_process_frame(s_isotp, rx_frame);
}
