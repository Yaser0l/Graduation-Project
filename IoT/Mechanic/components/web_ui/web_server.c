#include "web_server.h"

#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "cJSON.h"
#include "esp_http_server.h"
#include "esp_log.h"
#include "esp_wifi.h"

#include "local_mqtt.h"
#include "wifi_manager.h"
#include "wifi_store.h"

static const char *TAG = "web_server";
static httpd_handle_t s_http_server = NULL;
static saved_ap_store_t *s_ap_store = NULL;

extern const uint8_t index_html_start[] asm("_binary_index_html_start");
extern const uint8_t index_html_end[] asm("_binary_index_html_end");

static void send_json(httpd_req_t *req, int status_code, const char *json_body)
{
    httpd_resp_set_type(req, "application/json");
    httpd_resp_set_status(req, status_code == 200   ? "200 OK"
                               : status_code == 400 ? "400 Bad Request"
                               : status_code == 405 ? "405 Method Not Allowed"
                               : status_code == 500 ? "500 Internal Server Error"
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

static esp_err_t homepage_handler(httpd_req_t *req)
{
    httpd_resp_set_type(req, "text/html");
    httpd_resp_send(req, (const char *)index_html_start, index_html_end - index_html_start);
    return ESP_OK;
}

static esp_err_t ap_adder_handler(httpd_req_t *req)
{
    if (!s_ap_store)
    {
        send_json(req, 500, "{\"status\":\"error\",\"message\":\"Server not initialized\"}");
        return ESP_OK;
    }

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

    bool updated_existing = false;
    if (!wifi_store_add_or_update(s_ap_store, ssid, passphrase, &updated_existing))
    {
        send_json(req, 400, "{\"status\":\"error\",\"message\":\"AP list is full\"}");
        return ESP_OK;
    }

    if (wifi_store_persist(s_ap_store) != ESP_OK)
    {
        send_json(req, 500, "{\"status\":\"error\",\"message\":\"Failed to save AP\"}");
        return ESP_OK;
    }

    wifi_manager_notify_store_changed(s_ap_store);
    send_json(req, 200, "{\"status\":\"success\"}");
    return ESP_OK;
}

static esp_err_t ap_getter_handler(httpd_req_t *req)
{
    if (!s_ap_store)
    {
        send_json(req, 500, "{\"status\":\"error\",\"message\":\"Server not initialized\"}");
        return ESP_OK;
    }

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

    for (uint8_t i = 0; i < s_ap_store->count; ++i)
    {
        cJSON_AddItemToArray(arr, cJSON_CreateString(s_ap_store->entries[i].ssid));
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
    if (!s_ap_store)
    {
        send_json(req, 500, "{\"status\":\"error\",\"message\":\"Server not initialized\"}");
        return ESP_OK;
    }

    if (req->method != HTTP_POST)
    {
        send_json(req, 405, "{\"status\":\"error\",\"message\":\"Method not allowed\"}");
        return ESP_OK;
    }

    wifi_store_clear(s_ap_store);
    if (wifi_store_persist(s_ap_store) != ESP_OK)
    {
        send_json(req, 500, "{\"status\":\"error\",\"message\":\"Failed to reset AP list\"}");
        return ESP_OK;
    }

    wifi_manager_notify_store_changed(s_ap_store);
    wifi_manager_start_config_ap();
    send_json(req, 200, "{\"status\":\"success\"}");
    return ESP_OK;
}

static esp_err_t connect_endpoint_handler(httpd_req_t *req)
{
    wifi_manager_request_connect();
    send_json(req, 200, "{\"status\":\"connecting\"}");
    return ESP_OK;
}

static esp_err_t internet_check_handler(httpd_req_t *req)
{
    if (wifi_manager_is_connected())
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

static esp_err_t mqtt_broker_handler(httpd_req_t *req)
{
    if (req->method != HTTP_POST)
    {
        send_json(req, 405, "{\"status\":\"error\",\"message\":\"Method not allowed\"}");
        return ESP_OK;
    }

    if (req->content_len <= 0 || req->content_len >= 512)
    {
        send_json(req, 400, "{\"status\":\"error\",\"message\":\"Invalid payload\"}");
        return ESP_OK;
    }

    char body[512];
    int received = httpd_req_recv(req, body, req->content_len);
    if (received <= 0)
    {
        send_json(req, 400, "{\"status\":\"error\",\"message\":\"Failed to read body\"}");
        return ESP_OK;
    }
    body[received] = '\0';

    char broker_uri[MQTT_BROKER_URI_MAX_LEN] = {0};
    cJSON *json = cJSON_Parse(body);
    if (json)
    {
        cJSON *broker_json = cJSON_GetObjectItemCaseSensitive(json, "broker_uri");
        if (cJSON_IsString(broker_json) && broker_json->valuestring)
        {
            strncpy(broker_uri, broker_json->valuestring, sizeof(broker_uri) - 1);
        }
        cJSON_Delete(json);
    }
    else
    {
        read_form_value(body, "broker_uri", broker_uri, sizeof(broker_uri));
    }

    if (broker_uri[0] == '\0')
    {
        send_json(req, 400, "{\"status\":\"error\",\"message\":\"broker_uri is required\"}");
        return ESP_OK;
    }

    if (mqtt_module_set_broker_uri(broker_uri) != ESP_OK)
    {
        send_json(req, 500, "{\"status\":\"error\",\"message\":\"Failed to save broker URI\"}");
        return ESP_OK;
    }

    send_json(req, 200, "{\"status\":\"success\"}");
    return ESP_OK;
}

static esp_err_t mqtt_broker_get_handler(httpd_req_t *req)
{
    if (req->method != HTTP_GET)
    {
        send_json(req, 405, "{\"status\":\"error\",\"message\":\"Method not allowed\"}");
        return ESP_OK;
    }

    char broker_uri[MQTT_BROKER_URI_MAX_LEN] = {0};
    if (!mqtt_module_get_broker_uri(broker_uri, sizeof(broker_uri)))
    {
        send_json(req, 500, "{\"status\":\"error\",\"message\":\"Failed to load broker URI\"}");
        return ESP_OK;
    }

    cJSON *response_json = cJSON_CreateObject();
    if (!response_json)
    {
        send_json(req, 500, "{\"status\":\"error\",\"message\":\"Out of memory\"}");
        return ESP_OK;
    }

    cJSON_AddStringToObject(response_json, "broker_uri", broker_uri);
    char *response = cJSON_PrintUnformatted(response_json);
    cJSON_Delete(response_json);

    if (!response)
    {
        send_json(req, 500, "{\"status\":\"error\",\"message\":\"Out of memory\"}");
        return ESP_OK;
    }

    send_json(req, 200, response);
    free(response);
    return ESP_OK;
}

void web_server_start(saved_ap_store_t *store)
{
    if (!store)
    {
        ESP_LOGE(TAG, "Cannot start server without AP store");
        return;
    }

    s_ap_store = store;

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
    httpd_uri_t mqtt_broker_post_uri = {
        .uri = "/mqtt/broker",
        .method = HTTP_POST,
        .handler = mqtt_broker_handler,
        .user_ctx = NULL,
    };
    httpd_uri_t mqtt_broker_get_uri = {
        .uri = "/mqtt/broker",
        .method = HTTP_GET,
        .handler = mqtt_broker_get_handler,
        .user_ctx = NULL,
    };

    httpd_register_uri_handler(s_http_server, &homepage_uri);
    httpd_register_uri_handler(s_http_server, &save_uri);
    httpd_register_uri_handler(s_http_server, &saved_uri);
    httpd_register_uri_handler(s_http_server, &internet_uri);
    httpd_register_uri_handler(s_http_server, &connect_uri);
    httpd_register_uri_handler(s_http_server, &reset_uri);
    httpd_register_uri_handler(s_http_server, &scan_uri);
    httpd_register_uri_handler(s_http_server, &mqtt_broker_post_uri);
    httpd_register_uri_handler(s_http_server, &mqtt_broker_get_uri);
}
