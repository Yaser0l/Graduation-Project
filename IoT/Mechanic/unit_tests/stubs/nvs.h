#pragma once

#include "esp_err.h"
#include <stddef.h>
#include <stdint.h>

#define NVS_READONLY  1
#define NVS_READWRITE 2

typedef int nvs_handle_t;

esp_err_t nvs_open(const char* name, int open_mode, nvs_handle_t* out_handle);
void nvs_close(nvs_handle_t handle);
esp_err_t nvs_get_str(nvs_handle_t handle, const char* key, char* out_value, size_t* length);
esp_err_t nvs_set_str(nvs_handle_t handle, const char* key, const char* value);
esp_err_t nvs_get_blob(nvs_handle_t handle, const char* key, void* out_value, size_t* length);
esp_err_t nvs_set_blob(nvs_handle_t handle, const char* key, const void* data, size_t size);
esp_err_t nvs_commit(nvs_handle_t handle);
