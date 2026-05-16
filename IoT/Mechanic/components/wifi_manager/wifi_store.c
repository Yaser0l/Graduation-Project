#include "wifi_store.h"

#include <string.h>

#include "esp_log.h"
#include "nvs.h"
#include "sdkconfig.h"

#define NVS_NAMESPACE CONFIG_WIFI_MANAGER_NVS_NAMESPACE
#define NVS_KEY_AP_LIST CONFIG_WIFI_MANAGER_NVS_KEY_AP_LIST

static const char *TAG = "wifi_store";

esp_err_t wifi_store_load(saved_ap_store_t *store) {
  if (!store) {
    return ESP_ERR_INVALID_ARG;
  }

  nvs_handle_t nvs;
  esp_err_t err = nvs_open(NVS_NAMESPACE, NVS_READONLY, &nvs);
  if (err != ESP_OK) {
    ESP_LOGI(TAG, "NVS namespace not found, starting with empty AP list");
    memset(store, 0, sizeof(*store));
    return ESP_OK;
  }

  size_t required_size = sizeof(*store);
  err = nvs_get_blob(nvs, NVS_KEY_AP_LIST, store, &required_size);
  nvs_close(nvs);

  if (err == ESP_ERR_NVS_NOT_FOUND) {
    memset(store, 0, sizeof(*store));
    return ESP_OK;
  }

  if (err != ESP_OK || required_size != sizeof(*store) ||
      store->count > MAX_SAVED_APS) {
    ESP_LOGW(TAG, "Invalid AP store in NVS, resetting");
    memset(store, 0, sizeof(*store));
    return ESP_FAIL;
  }

  return ESP_OK;
}

esp_err_t wifi_store_persist(const saved_ap_store_t *store) {
  if (!store) {
    return ESP_ERR_INVALID_ARG;
  }

  nvs_handle_t nvs;
  esp_err_t err = nvs_open(NVS_NAMESPACE, NVS_READWRITE, &nvs);
  if (err != ESP_OK) {
    return err;
  }

  err = nvs_set_blob(nvs, NVS_KEY_AP_LIST, store, sizeof(*store));
  if (err == ESP_OK) {
    err = nvs_commit(nvs);
  }

  nvs_close(nvs);
  return err;
}

bool wifi_store_find_index(const saved_ap_store_t *store, const char *ssid,
                           uint8_t *index) {
  if (!store || !ssid) {
    return false;
  }

  for (uint8_t i = 0; i < store->count; ++i) {
    if (strcmp(store->entries[i].ssid, ssid) == 0) {
      if (index) {
        *index = i;
      }
      return true;
    }
  }

  return false;
}

bool wifi_store_add_or_update(saved_ap_store_t *store, const char *ssid,
                              const char *passphrase, bool *updated_existing) {
  if (!store || !ssid || !passphrase) {
    return false;
  }

  uint8_t index = 0;
  if (wifi_store_find_index(store, ssid, &index)) {
    strncpy(store->entries[index].passphrase, passphrase,
            sizeof(store->entries[index].passphrase) - 1);
    store->entries[index]
        .passphrase[sizeof(store->entries[index].passphrase) - 1] = '\0';
    if (updated_existing) {
      *updated_existing = true;
    }
    return true;
  }

  if (store->count >= MAX_SAVED_APS) {
    return false;
  }

  strncpy(store->entries[store->count].ssid, ssid,
          sizeof(store->entries[store->count].ssid) - 1);
  store->entries[store->count]
      .ssid[sizeof(store->entries[store->count].ssid) - 1] = '\0';

  strncpy(store->entries[store->count].passphrase, passphrase,
          sizeof(store->entries[store->count].passphrase) - 1);
  store->entries[store->count]
      .passphrase[sizeof(store->entries[store->count].passphrase) - 1] = '\0';

  store->count++;

  if (updated_existing) {
    *updated_existing = false;
  }

  return true;
}

void wifi_store_clear(saved_ap_store_t *store) {
  if (!store) {
    return;
  }

  memset(store, 0, sizeof(*store));
}
