#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "cJSON.h"
#include "esp_event.h"
#include "esp_http_server.h"
#include "esp_log.h"
#include "esp_netif.h"
#include "esp_system.h"
#include "esp_wifi.h"
#include "freertos/FreeRTOS.h"
#include "freertos/event_groups.h"
#include "freertos/task.h"
#include "nvs.h"
#include "nvs_flash.h"

#define MAX_SAVED_APS 10
#define NVS_NAMESPACE "wifi_mgr"
#define NVS_KEY_AP_LIST "ap_list"
#define WIFI_CONNECT_TIMEOUT_MS 10000
#define WIFI_RETRY_LOOP_DELAY_MS 2000

typedef struct
{
    char ssid[33];
    char passphrase[65];
} saved_ap_t;

typedef struct
{
    uint8_t count;
    saved_ap_t entries[MAX_SAVED_APS];
} saved_ap_store_t;

static const char *TAG = "wifi_manager";
static EventGroupHandle_t s_wifi_event_group;
static const int WIFI_CONNECTED_BIT = BIT0;

static saved_ap_store_t s_ap_store = {0};
static bool s_config_ap = false;
static bool s_should_connect = false;
static httpd_handle_t s_http_server = NULL;

extern const uint8_t index_html_start[] asm("_binary_index_html_start");
extern const uint8_t index_html_end[] asm("_binary_index_html_end");

static void start_config_ap(void);
static esp_err_t save_ap_store_to_nvs(void);

static void send_json(httpd_req_t *req, int status_code, const char *json_body)
{
    httpd_resp_set_type(req, "application/json");
    httpd_resp_set_status(req, status_code == 200 ? "200 OK" : status_code == 400 ? "400 Bad Request"
                                                           : status_code == 405   ? "405 Method Not Allowed"
                                                           : status_code == 500   ? "500 Internal Server Error"
                                                                                  : "200 OK");
    httpd_resp_sendstr(req, json_body);
}

static void url_decode(char *dst, const char *src, size_t dst_len)
{
    size_t di = 0;
    for (size_t si = 0; src[si] != '\0' && di + 1 < dst_len; ++si)
    {
        if (src[si] == '+')
        {
            dst[di++] = ' ';
        }
        else if (src[si] == '%' && src[si + 1] && src[si + 2])
        {
            char hex[3] = {src[si + 1], src[si + 2], '\0'};
            dst[di++] = (char)strtol(hex, NULL, 16);
            si += 2;
        }
        else
        {
            dst[di++] = src[si];
        }
    }
    dst[di] = '\0';
}

static bool read_form_value(const char *body, const char *key, char *out, size_t out_len)
{
    char pattern[32];
    snprintf(pattern, sizeof(pattern), "%s=", key);

    const char *start = strstr(body, pattern);
    if (!start)
    {
        return false;
    }
    start += strlen(pattern);

    const char *end = strchr(start, '&');
    size_t raw_len = end ? (size_t)(end - start) : strlen(start);

    char raw[256];
    if (raw_len >= sizeof(raw))
    {
        return false;
    }
    memcpy(raw, start, raw_len);
    raw[raw_len] = '\0';

    url_decode(out, raw, out_len);
    return true;
}

static esp_err_t load_ap_store_from_nvs(void)
{
    nvs_handle_t nvs;
    esp_err_t err = nvs_open(NVS_NAMESPACE, NVS_READONLY, &nvs);
    if (err != ESP_OK)
    {
        ESP_LOGI(TAG, "NVS namespace not found, starting with empty AP list");
        memset(&s_ap_store, 0, sizeof(s_ap_store));
        return ESP_OK;
    }

    size_t required_size = sizeof(s_ap_store);
    err = nvs_get_blob(nvs, NVS_KEY_AP_LIST, &s_ap_store, &required_size);
    nvs_close(nvs);

    if (err == ESP_ERR_NVS_NOT_FOUND)
    {
        memset(&s_ap_store, 0, sizeof(s_ap_store));
        return ESP_OK;
    }

    if (err != ESP_OK || required_size != sizeof(s_ap_store) || s_ap_store.count > MAX_SAVED_APS)
    {
        ESP_LOGW(TAG, "Invalid AP store in NVS, resetting");
        memset(&s_ap_store, 0, sizeof(s_ap_store));
        return ESP_FAIL;
    }

    return ESP_OK;
}

static esp_err_t save_ap_store_to_nvs(void)
{
    nvs_handle_t nvs;
    esp_err_t err = nvs_open(NVS_NAMESPACE, NVS_READWRITE, &nvs);
    if (err != ESP_OK)
    {
        return err;
    }

    err = nvs_set_blob(nvs, NVS_KEY_AP_LIST, &s_ap_store, sizeof(s_ap_store));
    if (err == ESP_OK)
    {
        err = nvs_commit(nvs);
    }
    nvs_close(nvs);
    return err;
}

static bool is_wifi_connected(void)
{
    EventBits_t bits = xEventGroupGetBits(s_wifi_event_group);
    return (bits & WIFI_CONNECTED_BIT) != 0;
}

static void stop_config_ap(void)
{
    if (!s_config_ap)
    {
        return;
    }

    ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_STA));
    s_config_ap = false;
    ESP_LOGI(TAG, "Configuration AP stopped");
}

static void start_config_ap(void)
{
    if (s_config_ap)
    {
        return;
    }

    wifi_config_t ap_config = {
        .ap = {
            .ssid = "ESP32_Config",
            .ssid_len = 0,
            .channel = 1,
            .password = "",
            .max_connection = 4,
            .authmode = WIFI_AUTH_OPEN,
        },
    };

    ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_APSTA));
    ESP_ERROR_CHECK(esp_wifi_set_config(WIFI_IF_AP, &ap_config));
    s_config_ap = true;
    ESP_LOGI(TAG, "Configuration AP started: ESP32_Config");
}

static esp_err_t homepage_handler(httpd_req_t *req)
{
    httpd_resp_set_type(req, "text/html");
    httpd_resp_send(req, (const char *)index_html_start, index_html_end - index_html_start);
    return ESP_OK;
}

static esp_err_t ap_adder_handler(httpd_req_t *req)
{
    if (req->method != HTTP_POST)
    {
        send_json(req, 405, "{\"status\":\"error\",\"message\":\"Method not allowed\"}");
        return ESP_OK;
    }

    if (req->content_len <= 0 || req->content_len >= 1024)
    {
        send_json(req, 400, "{\"status\":\"error\",\"message\":\"Invalid payload\"}");
        return ESP_OK;
    }

    char body[1024];
    int received = httpd_req_recv(req, body, req->content_len);
    if (received <= 0)
    {
        send_json(req, 400, "{\"status\":\"error\",\"message\":\"Failed to read body\"}");
        return ESP_OK;
    }
    body[received] = '\0';

    char ssid[33] = {0};
    char passphrase[65] = {0};

    cJSON *json = cJSON_Parse(body);
    if (json)
    {
        cJSON *ssid_json = cJSON_GetObjectItemCaseSensitive(json, "ssid");
        cJSON *pass_json = cJSON_GetObjectItemCaseSensitive(json, "passphrase");

        if (cJSON_IsString(ssid_json) && ssid_json->valuestring)
        {
            strncpy(ssid, ssid_json->valuestring, sizeof(ssid) - 1);
        }
        if (cJSON_IsString(pass_json) && pass_json->valuestring)
        {
            strncpy(passphrase, pass_json->valuestring, sizeof(passphrase) - 1);
        }
        cJSON_Delete(json);
    }
    else
    {
        read_form_value(body, "ssid", ssid, sizeof(ssid));
        read_form_value(body, "passphrase", passphrase, sizeof(passphrase));
    }

    if (strlen(ssid) == 0)
    {
        send_json(req, 400, "{\"status\":\"error\",\"message\":\"SSID is required\"}");
        return ESP_OK;
    }
    if (strlen(ssid) > 32 || strlen(passphrase) > 64)
    {
        send_json(req, 400, "{\"status\":\"error\",\"message\":\"Input too long\"}");
        return ESP_OK;
    }

    for (uint8_t i = 0; i < s_ap_store.count; ++i)
    {
        if (strcmp(s_ap_store.entries[i].ssid, ssid) == 0)
        {
            strncpy(s_ap_store.entries[i].passphrase, passphrase, sizeof(s_ap_store.entries[i].passphrase) - 1);
            if (save_ap_store_to_nvs() == ESP_OK)
            {
                send_json(req, 200, "{\"status\":\"success\"}");
            }
            else
            {
                send_json(req, 500, "{\"status\":\"error\",\"message\":\"Failed to save AP\"}");
            }
            return ESP_OK;
        }
    }

    if (s_ap_store.count >= MAX_SAVED_APS)
    {
        send_json(req, 400, "{\"status\":\"error\",\"message\":\"AP list is full\"}");
        return ESP_OK;
    }

    strncpy(s_ap_store.entries[s_ap_store.count].ssid, ssid, sizeof(s_ap_store.entries[s_ap_store.count].ssid) - 1);
    strncpy(s_ap_store.entries[s_ap_store.count].passphrase, passphrase, sizeof(s_ap_store.entries[s_ap_store.count].passphrase) - 1);
    s_ap_store.count++;

    if (save_ap_store_to_nvs() == ESP_OK)
    {
        send_json(req, 200, "{\"status\":\"success\"}");
    }
    else
    {
        send_json(req, 500, "{\"status\":\"error\",\"message\":\"Failed to add AP\"}");
    }
    return ESP_OK;
}

static esp_err_t ap_getter_handler(httpd_req_t *req)
{
    if (req->method != HTTP_GET)
    {
        send_json(req, 405, "{\"status\":\"error\",\"message\":\"Method not allowed\"}");
        return ESP_OK;
    }

    cJSON *arr = cJSON_CreateArray();
    if (!arr)
    {
        send_json(req, 500, "{\"status\":\"error\",\"message\":\"Out of memory\"}");
        return ESP_OK;
    }

    for (uint8_t i = 0; i < s_ap_store.count; ++i)
    {
        cJSON_AddItemToArray(arr, cJSON_CreateString(s_ap_store.entries[i].ssid));
    }

    char *response = cJSON_PrintUnformatted(arr);
    cJSON_Delete(arr);

    if (!response)
    {
        send_json(req, 500, "{\"status\":\"error\",\"message\":\"Out of memory\"}");
        return ESP_OK;
    }

    send_json(req, 200, response);
    free(response);
    return ESP_OK;
}

static esp_err_t ap_reset_handler(httpd_req_t *req)
{
    if (req->method != HTTP_POST)
    {
        send_json(req, 405, "{\"status\":\"error\",\"message\":\"Method not allowed\"}");
        return ESP_OK;
    }

    memset(&s_ap_store, 0, sizeof(s_ap_store));
    if (save_ap_store_to_nvs() != ESP_OK)
    {
        send_json(req, 500, "{\"status\":\"error\",\"message\":\"Failed to reset AP list\"}");
        return ESP_OK;
    }

    start_config_ap();
    send_json(req, 200, "{\"status\":\"success\"}");
    return ESP_OK;
}

static esp_err_t connect_endpoint_handler(httpd_req_t *req)
{
    s_should_connect = true;
    send_json(req, 200, "{\"status\":\"connecting\"}");
    return ESP_OK;
}

static esp_err_t internet_check_handler(httpd_req_t *req)
{
    if (is_wifi_connected())
    {
        send_json(req, 200, "{\"status\":\"connected\"}");
    }
    else
    {
        send_json(req, 200, "{\"status\":\"disconnected\"}");
    }
    return ESP_OK;
}

static esp_err_t scan_endpoint_handler(httpd_req_t *req)
{
    if (req->method != HTTP_GET)
    {
        send_json(req, 405, "{\"status\":\"error\",\"message\":\"Method not allowed\"}");
        return ESP_OK;
    }

    wifi_scan_config_t scan_cfg = {
        .ssid = NULL,
        .bssid = NULL,
        .channel = 0,
        .show_hidden = false,
    };

    esp_err_t err = esp_wifi_scan_start(&scan_cfg, true);
    if (err != ESP_OK)
    {
        send_json(req, 500, "{\"status\":\"error\",\"message\":\"Scan failed\"}");
        return ESP_OK;
    }

    uint16_t ap_count = 0;
    err = esp_wifi_scan_get_ap_num(&ap_count);
    if (err != ESP_OK || ap_count == 0)
    {
        send_json(req, 200, "[]");
        return ESP_OK;
    }

    wifi_ap_record_t *records = calloc(ap_count, sizeof(wifi_ap_record_t));
    if (!records)
    {
        send_json(req, 500, "{\"status\":\"error\",\"message\":\"Out of memory\"}");
        return ESP_OK;
    }

    err = esp_wifi_scan_get_ap_records(&ap_count, records);
    if (err != ESP_OK)
    {
        free(records);
        send_json(req, 500, "{\"status\":\"error\",\"message\":\"Failed to read scan results\"}");
        return ESP_OK;
    }

    cJSON *arr = cJSON_CreateArray();
    if (!arr)
    {
        free(records);
        send_json(req, 500, "{\"status\":\"error\",\"message\":\"Out of memory\"}");
        return ESP_OK;
    }

    for (uint16_t i = 0; i < ap_count; ++i)
    {
        if (records[i].ssid[0] != '\0')
        {
            cJSON_AddItemToArray(arr, cJSON_CreateString((const char *)records[i].ssid));
        }
    }

    char *response = cJSON_PrintUnformatted(arr);
    cJSON_Delete(arr);
    free(records);

    if (!response)
    {
        send_json(req, 500, "{\"status\":\"error\",\"message\":\"Out of memory\"}");
        return ESP_OK;
    }

    send_json(req, 200, response);
    free(response);
    return ESP_OK;
}

static void try_connect_saved_aps(void)
{
    if (s_ap_store.count == 0)
    {
        start_config_ap();
        return;
    }

    for (uint8_t i = 0; i < s_ap_store.count; ++i)
    {
        wifi_config_t sta_config = {0};
        strncpy((char *)sta_config.sta.ssid, s_ap_store.entries[i].ssid, sizeof(sta_config.sta.ssid) - 1);
        strncpy((char *)sta_config.sta.password, s_ap_store.entries[i].passphrase, sizeof(sta_config.sta.password) - 1);
        sta_config.sta.threshold.authmode = WIFI_AUTH_WPA2_PSK;
        sta_config.sta.pmf_cfg.capable = true;
        sta_config.sta.pmf_cfg.required = false;

        ESP_LOGI(TAG, "Trying AP: %s", s_ap_store.entries[i].ssid);
        ESP_ERROR_CHECK(esp_wifi_set_config(WIFI_IF_STA, &sta_config));
        ESP_ERROR_CHECK(esp_wifi_connect());

        EventBits_t bits = xEventGroupWaitBits(
            s_wifi_event_group,
            WIFI_CONNECTED_BIT,
            pdFALSE,
            pdFALSE,
            pdMS_TO_TICKS(WIFI_CONNECT_TIMEOUT_MS));

        if (bits & WIFI_CONNECTED_BIT)
        {
            ESP_LOGI(TAG, "Connected to: %s", s_ap_store.entries[i].ssid);
            stop_config_ap();
            s_should_connect = false;
            return;
        }

        ESP_LOGW(TAG, "Connection failed for: %s", s_ap_store.entries[i].ssid);
        esp_wifi_disconnect();
    }

    start_config_ap();
}

static void wifi_manager_task(void *arg)
{
    (void)arg;
    while (true)
    {
        if (s_should_connect && !is_wifi_connected())
        {
            try_connect_saved_aps();
        }

        if (is_wifi_connected())
        {
            stop_config_ap();
        }
        else if (s_ap_store.count == 0)
        {
            start_config_ap();
        }

        vTaskDelay(pdMS_TO_TICKS(WIFI_RETRY_LOOP_DELAY_MS));
    }
}

static void wifi_event_handler(void *arg, esp_event_base_t event_base,
                               int32_t event_id, void *event_data)
{
    (void)arg;
    (void)event_data;

    if (event_base == WIFI_EVENT && event_id == WIFI_EVENT_STA_DISCONNECTED)
    {
        xEventGroupClearBits(s_wifi_event_group, WIFI_CONNECTED_BIT);
        if (s_ap_store.count > 0)
        {
            s_should_connect = true;
        }
    }
    else if (event_base == IP_EVENT && event_id == IP_EVENT_STA_GOT_IP)
    {
        xEventGroupSetBits(s_wifi_event_group, WIFI_CONNECTED_BIT);
        s_should_connect = false;
    }
}

static void start_web_server(void)
{
    httpd_config_t config = HTTPD_DEFAULT_CONFIG();
    if (httpd_start(&s_http_server, &config) != ESP_OK)
    {
        ESP_LOGE(TAG, "Failed to start HTTP server");
        return;
    }

    httpd_uri_t homepage_uri = {
        .uri = "/",
        .method = HTTP_GET,
        .handler = homepage_handler,
        .user_ctx = NULL,
    };
    httpd_uri_t save_uri = {
        .uri = "/wifi/save",
        .method = HTTP_POST,
        .handler = ap_adder_handler,
        .user_ctx = NULL,
    };
    httpd_uri_t saved_uri = {
        .uri = "/wifi/saved",
        .method = HTTP_GET,
        .handler = ap_getter_handler,
        .user_ctx = NULL,
    };
    httpd_uri_t internet_uri = {
        .uri = "/wifi/internet",
        .method = HTTP_GET,
        .handler = internet_check_handler,
        .user_ctx = NULL,
    };
    httpd_uri_t connect_uri = {
        .uri = "/wifi/connect",
        .method = HTTP_GET,
        .handler = connect_endpoint_handler,
        .user_ctx = NULL,
    };
    httpd_uri_t reset_uri = {
        .uri = "/wifi/reset",
        .method = HTTP_POST,
        .handler = ap_reset_handler,
        .user_ctx = NULL,
    };
    httpd_uri_t scan_uri = {
        .uri = "/wifi/scan",
        .method = HTTP_GET,
        .handler = scan_endpoint_handler,
        .user_ctx = NULL,
    };

    httpd_register_uri_handler(s_http_server, &homepage_uri);
    httpd_register_uri_handler(s_http_server, &save_uri);
    httpd_register_uri_handler(s_http_server, &saved_uri);
    httpd_register_uri_handler(s_http_server, &internet_uri);
    httpd_register_uri_handler(s_http_server, &connect_uri);
    httpd_register_uri_handler(s_http_server, &reset_uri);
    httpd_register_uri_handler(s_http_server, &scan_uri);
}

void app_main(void)
{
    esp_err_t ret = nvs_flash_init();
    if (ret == ESP_ERR_NVS_NO_FREE_PAGES || ret == ESP_ERR_NVS_NEW_VERSION_FOUND)
    {
        ESP_ERROR_CHECK(nvs_flash_erase());
        ret = nvs_flash_init();
    }
    ESP_ERROR_CHECK(ret);

    ESP_ERROR_CHECK(esp_netif_init());
    ESP_ERROR_CHECK(esp_event_loop_create_default());
    esp_netif_create_default_wifi_sta();
    esp_netif_create_default_wifi_ap();

    wifi_init_config_t cfg = WIFI_INIT_CONFIG_DEFAULT();
    ESP_ERROR_CHECK(esp_wifi_init(&cfg));

    s_wifi_event_group = xEventGroupCreate();

    ESP_ERROR_CHECK(esp_event_handler_instance_register(
        WIFI_EVENT, ESP_EVENT_ANY_ID, &wifi_event_handler, NULL, NULL));
    ESP_ERROR_CHECK(esp_event_handler_instance_register(
        IP_EVENT, IP_EVENT_STA_GOT_IP, &wifi_event_handler, NULL, NULL));

    ESP_ERROR_CHECK(load_ap_store_from_nvs());

    ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_APSTA));
    ESP_ERROR_CHECK(esp_wifi_start());

    if (s_ap_store.count == 0)
    {
        ESP_LOGI(TAG, "No saved APs found. Starting configuration AP...");
        start_config_ap();
    }
    else
    {
        ESP_LOGI(TAG, "Saved APs found. Auto-connecting...");
        s_should_connect = true;
    }

    start_web_server();
    xTaskCreate(wifi_manager_task, "wifi_manager_task", 4096, NULL, 5, NULL);
}