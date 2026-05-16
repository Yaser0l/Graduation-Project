#pragma once

#include <stdbool.h>
#include <stdint.h>

#include "esp_err.h"
#include "sdkconfig.h"

#ifndef CONFIG_WIFI_MANAGER_MAX_SAVED_APS
#define CONFIG_WIFI_MANAGER_MAX_SAVED_APS 10
#endif

#define MAX_SAVED_APS CONFIG_WIFI_MANAGER_MAX_SAVED_APS

typedef struct {
  char ssid[33];
  char passphrase[65];
} saved_ap_t;

typedef struct saved_ap_store {
  uint8_t count;
  saved_ap_t entries[MAX_SAVED_APS];
} saved_ap_store_t;

esp_err_t wifi_store_load(saved_ap_store_t *store);
esp_err_t wifi_store_persist(const saved_ap_store_t *store);
bool wifi_store_find_index(const saved_ap_store_t *store, const char *ssid,
                           uint8_t *index);
bool wifi_store_add_or_update(saved_ap_store_t *store, const char *ssid,
                              const char *passphrase, bool *updated_existing);
void wifi_store_clear(saved_ap_store_t *store);
