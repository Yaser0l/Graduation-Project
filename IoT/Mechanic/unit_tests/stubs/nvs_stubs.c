#include "nvs.h"

#include <string.h>

static esp_err_t s_open_result = ESP_OK;
static esp_err_t s_get_str_result = ESP_OK;
static esp_err_t s_commit_result = ESP_OK;
static char s_value[128] = {0};

void nvs_stub_reset(void)
{
    s_open_result = ESP_OK;
    s_get_str_result = ESP_OK;
    s_commit_result = ESP_OK;
    memset(s_value, 0, sizeof(s_value));
}

void nvs_stub_set_open_result(esp_err_t result)
{
    s_open_result = result;
}

void nvs_stub_set_get_str_result(esp_err_t result)
{
    s_get_str_result = result;
}

void nvs_stub_set_commit_result(esp_err_t result)
{
    s_commit_result = result;
}

const char *nvs_stub_get_last_set_value(void)
{
    return s_value;
}

esp_err_t nvs_open(const char *name, int open_mode, nvs_handle_t *out_handle)
{
    (void)name;
    (void)open_mode;
    if (out_handle)
    {
        *out_handle = 1;
    }
    return s_open_result;
}

esp_err_t nvs_set_str(nvs_handle_t handle, const char *key, const char *value)
{
    (void)handle;
    (void)key;
    if (!value)
    {
        return ESP_ERR_INVALID_ARG;
    }
    strncpy(s_value, value, sizeof(s_value) - 1);
    s_value[sizeof(s_value) - 1] = '\0';
    return ESP_OK;
}

esp_err_t nvs_get_str(nvs_handle_t handle, const char *key, char *out_value, size_t *length)
{
    (void)handle;
    (void)key;

    if (s_get_str_result != ESP_OK)
    {
        return s_get_str_result;
    }

    size_t value_len = strnlen(s_value, sizeof(s_value));
    if (!out_value || !length)
    {
        return ESP_ERR_INVALID_ARG;
    }
    if (*length <= value_len)
    {
        return ESP_ERR_INVALID_SIZE;
    }

    memcpy(out_value, s_value, value_len + 1);
    *length = value_len + 1;
    return ESP_OK;
}

esp_err_t nvs_commit(nvs_handle_t handle)
{
    (void)handle;
    return s_commit_result;
}

void nvs_close(nvs_handle_t handle)
{
    (void)handle;
}
