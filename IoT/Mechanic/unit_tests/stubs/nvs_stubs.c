#include "nvs_stubs.h"

#include "nvs.h"

static int32_t s_open_result = 0;
static int32_t s_get_str_result = 0;
static int32_t s_get_blob_result = 0;
static int32_t s_set_blob_result = 0;
static int32_t s_commit_result = 0;

static uint8_t s_blob_data[2048] = {0};
static size_t s_blob_data_size = 0;

static char s_stored_strs[8][256] = {{0}};
static int s_str_count = 0;
static char s_last_set_value[256] = {0};

void nvs_stub_reset(void) {
    s_open_result = 0;
    s_get_str_result = 0;
    s_get_blob_result = 0;
    s_set_blob_result = 0;
    s_commit_result = 0;
    s_blob_data_size = 0;
    memset(s_blob_data, 0, sizeof(s_blob_data));
    s_str_count = 0;
    memset(s_stored_strs, 0, sizeof(s_stored_strs));
    memset(s_last_set_value, 0, sizeof(s_last_set_value));
}

void nvs_stub_set_open_result(int32_t result) { s_open_result = result; }
void nvs_stub_set_get_str_result(int32_t result) { s_get_str_result = result; }
void nvs_stub_set_get_blob_result(int32_t result) { s_get_blob_result = result; }
void nvs_stub_set_set_blob_result(int32_t result) { s_set_blob_result = result; }
void nvs_stub_set_commit_result(int32_t result) { s_commit_result = result; }

void nvs_stub_set_blob_data(const void* data, size_t size) {
    if (data && size <= sizeof(s_blob_data)) {
        memcpy(s_blob_data, data, size);
        s_blob_data_size = size;
    }
}

esp_err_t nvs_set_str(nvs_handle_t handle, const char* key, const char* value) {
    (void)handle; (void)key;
    if (value) {
        strncpy(s_last_set_value, value, 255);
        s_last_set_value[255] = '\0';
        if (s_str_count < 8) {
            strncpy(s_stored_strs[s_str_count], value, 255);
            s_stored_strs[s_str_count][255] = '\0';
            s_str_count++;
        }
    }
    return s_set_blob_result;
}

const char* nvs_stub_get_last_set_value(void) {
    if (s_str_count > 0) {
        return s_stored_strs[s_str_count - 1];
    }
    return s_last_set_value;
}

esp_err_t nvs_open(const char* name, int open_mode, nvs_handle_t* out_handle) {
    (void)name; (void)open_mode;
    if (out_handle) *out_handle = 1;
    return s_open_result;
}

void nvs_close(nvs_handle_t handle) { (void)handle; }

esp_err_t nvs_get_str(nvs_handle_t handle, const char* key, char* out_value,
                       size_t* length) {
    (void)handle; (void)key;
    if (s_get_str_result != 0) return s_get_str_result;
    if (s_str_count > 0 && out_value && length) {
        strncpy(out_value, s_stored_strs[s_str_count - 1], *length - 1);
        out_value[*length - 1] = '\0';
        *length = strlen(out_value);
        return 0;
    }
    return ESP_ERR_NVS_NOT_FOUND;
}

esp_err_t nvs_get_blob(nvs_handle_t handle, const char* key, void* out_value,
                        size_t* length) {
    (void)handle; (void)key;
    if (s_get_blob_result != 0) return s_get_blob_result;
    if (out_value && length && s_blob_data_size > 0) {
        memcpy(out_value, s_blob_data,
               s_blob_data_size < *length ? s_blob_data_size : *length);
        *length = s_blob_data_size;
        return 0;
    }
    return ESP_ERR_NVS_NOT_FOUND;
}

esp_err_t nvs_set_blob(nvs_handle_t handle, const char* key, const void* data,
                        size_t size) {
    (void)handle; (void)key; (void)data; (void)size;
    return s_set_blob_result;
}

esp_err_t nvs_commit(nvs_handle_t handle) {
    (void)handle;
    return s_commit_result;
}
