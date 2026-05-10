#include "nvs.h"

#include <string.h>

static esp_err_t s_open_result = ESP_OK;
static esp_err_t s_get_str_result = ESP_OK;
static esp_err_t s_get_blob_result = ESP_OK;
static esp_err_t s_set_blob_result = ESP_OK;
static esp_err_t s_commit_result = ESP_OK;
static char s_value[128] = {0};
static uint8_t s_blob[2048];
static size_t s_blob_size = 0;

void nvs_stub_reset(void)
{
    s_open_result = ESP_OK;
    s_get_str_result = ESP_OK;
    s_get_blob_result = ESP_OK;
    s_set_blob_result = ESP_OK;
    s_commit_result = ESP_OK;
    memset(s_value, 0, sizeof(s_value));
    memset(s_blob, 0, sizeof(s_blob));
    s_blob_size = 0;
}

void nvs_stub_set_open_result(esp_err_t result)
{
    s_open_result = result;
}

void nvs_stub_set_get_str_result(esp_err_t result)
{
    s_get_str_result = result;
}

void nvs_stub_set_get_blob_result(esp_err_t result)
{
    s_get_blob_result = result;
}

void nvs_stub_set_set_blob_result(esp_err_t result)
{
    s_set_blob_result = result;
}

void nvs_stub_set_commit_result(esp_err_t result)
{
    s_commit_result = result;
}

const char *nvs_stub_get_last_set_value(void)
{
    return s_value;
}

void nvs_stub_set_blob_data(const void *data, size_t length)
{
    if (!data || length == 0)
    {
        s_blob_size = 0;
        return;
    }

    if (length > sizeof(s_blob))
    {
        length = sizeof(s_blob);
    }

    memcpy(s_blob, data, length);
    s_blob_size = length;
}

size_t nvs_stub_get_blob_size(void)
{
    return s_blob_size;
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

esp_err_t nvs_set_blob(nvs_handle_t handle, const char *key, const void *value, size_t length)
{
    (void)handle;
    (void)key;
    if (s_set_blob_result != ESP_OK)
    {
        return s_set_blob_result;
    }

    if (!value && length > 0)
    {
        return ESP_ERR_INVALID_ARG;
    }

    if (length > sizeof(s_blob))
    {
        length = sizeof(s_blob);
    }

    if (value && length > 0)
    {
        memcpy(s_blob, value, length);
        s_blob_size = length;
    }
    else
    {
        s_blob_size = 0;
    }

    return ESP_OK;
}

esp_err_t nvs_get_blob(nvs_handle_t handle, const char *key, void *out_value, size_t *length)
{
    (void)handle;
    (void)key;

    if (s_get_blob_result != ESP_OK)
    {
        return s_get_blob_result;
    }

    if (!out_value || !length)
    {
        return ESP_ERR_INVALID_ARG;
    }

    if (*length < s_blob_size)
    {
        *length = s_blob_size;
        return ESP_ERR_INVALID_SIZE;
    }

    if (s_blob_size > 0)
    {
        memcpy(out_value, s_blob, s_blob_size);
    }
    *length = s_blob_size;
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
