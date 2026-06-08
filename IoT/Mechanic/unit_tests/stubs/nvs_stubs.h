#pragma once

#include "nvs.h"
#include <string.h>

void nvs_stub_reset(void);
void nvs_stub_set_open_result(int32_t result);
void nvs_stub_set_get_str_result(int32_t result);
void nvs_stub_set_get_blob_result(int32_t result);
void nvs_stub_set_set_blob_result(int32_t result);
void nvs_stub_set_commit_result(int32_t result);
void nvs_stub_set_blob_data(const void* data, size_t size);
esp_err_t nvs_set_str(nvs_handle_t handle, const char* key, const char* value);
const char* nvs_stub_get_last_set_value(void);
