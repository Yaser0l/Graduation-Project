#pragma once

#include <stddef.h>

#include "esp_err.h"

typedef int nvs_handle_t;

#define NVS_READONLY 0
#define NVS_READWRITE 1

esp_err_t nvs_open(const char *name, int open_mode, nvs_handle_t *out_handle);
esp_err_t nvs_set_str(nvs_handle_t handle, const char *key, const char *value);
esp_err_t nvs_get_str(nvs_handle_t handle, const char *key, char *out_value, size_t *length);
esp_err_t nvs_commit(nvs_handle_t handle);
void nvs_close(nvs_handle_t handle);

void nvs_stub_reset(void);
void nvs_stub_set_open_result(esp_err_t result);
void nvs_stub_set_get_str_result(esp_err_t result);
void nvs_stub_set_commit_result(esp_err_t result);
const char *nvs_stub_get_last_set_value(void);
