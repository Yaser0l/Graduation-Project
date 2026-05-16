#include "sdkconfig.h"

#if CONFIG_ETHERNET_QEMU_CONNECT

#include "ethernet_qemu.h"

#include <stdbool.h>
#include <string.h>

#include "esp_eth.h"
#include "esp_eth_mac.h"
#include "esp_event.h"
#include "esp_log.h"
#include "esp_netif.h"
#include "freertos/FreeRTOS.h"
#include "freertos/event_groups.h"

#include "network_events.h"

static const char *TAG = "ethernet_qemu";

static EventGroupHandle_t s_eth_event_group;
static const int ETH_CONNECTED_BIT = BIT0;
static esp_eth_handle_t s_eth_handle = NULL;
static esp_netif_t *s_eth_netif = NULL;
static bool s_should_connect = false;

/* ── Event handlers ─────────────────────────────────────────────────── */

static void eth_event_handler(void *arg, esp_event_base_t event_base,
                              int32_t event_id, void *event_data) {
  (void)arg;

  switch (event_id) {
  case ETHERNET_EVENT_CONNECTED:
    ESP_LOGI(TAG, "Ethernet link up");
    break;
  case ETHERNET_EVENT_DISCONNECTED:
    ESP_LOGW(TAG, "Ethernet link down");
    xEventGroupClearBits(s_eth_event_group, ETH_CONNECTED_BIT);
    network_events_post(NETWORK_EVENT_DOWN, NULL, 0);
#if CONFIG_ETHERNET_QEMU_AUTO_RECONNECT
    s_should_connect = true;
#endif
    break;
  case ETHERNET_EVENT_START:
    ESP_LOGI(TAG, "Ethernet driver started");
    break;
  case ETHERNET_EVENT_STOP:
    ESP_LOGI(TAG, "Ethernet driver stopped");
    break;
  default:
    break;
  }
}

static void got_ip_event_handler(void *arg, esp_event_base_t event_base,
                                 int32_t event_id, void *event_data) {
  (void)arg;

  const ip_event_got_ip_t *event = (const ip_event_got_ip_t *)event_data;

  ESP_LOGI(TAG, "Got IP: " IPSTR, IP2STR(&event->ip_info.ip));
  xEventGroupSetBits(s_eth_event_group, ETH_CONNECTED_BIT);
  network_events_post(NETWORK_EVENT_UP, NULL, 0);
  s_should_connect = false;
}

#if CONFIG_ETHERNET_QEMU_CONNECT_IPV6 ||                                       \
    CONFIG_ETHERNET_QEMU_CONNECT_UNSPECIFIED
static void got_ip6_event_handler(void *arg, esp_event_base_t event_base,
                                  int32_t event_id, void *event_data) {
  (void)arg;

  const ip_event_got_ip6_t *event = (const ip_event_got_ip6_t *)event_data;

  if (s_eth_netif && event->esp_netif == s_eth_netif) {
    ESP_LOGI(TAG, "Got IPv6: " IPV6STR, IPV62STR(event->ip6_info.ip));
    xEventGroupSetBits(s_eth_event_group, ETH_CONNECTED_BIT);
    network_events_post(NETWORK_EVENT_UP, NULL, 0);
    s_should_connect = false;
  }
}
#endif

static void network_request_handler(void *arg, esp_event_base_t event_base,
                                    int32_t event_id, void *event_data) {
  (void)arg;
  (void)event_base;
  (void)event_id;
  (void)event_data;

  ethernet_qemu_request_connect();
}

/* ── Driver initialisation ──────────────────────────────────────────── */

static esp_err_t ethernet_qemu_driver_init(void) {
  /* MAC – OpenCores Ethernet for QEMU */
  eth_mac_config_t mac_config = ETH_MAC_DEFAULT_CONFIG();
  esp_eth_mac_t *mac = esp_eth_mac_new_openeth(&mac_config);
  if (mac == NULL) {
    ESP_LOGE(TAG, "Failed to create OpenETH MAC");
    return ESP_FAIL;
  }

  /* PHY – use the generic one (not really relevant in QEMU) */
  eth_phy_config_t phy_config = ETH_PHY_DEFAULT_CONFIG();
  phy_config.autonego_timeout_ms = 100;
  esp_eth_phy_t *phy = esp_eth_phy_new_generic(&phy_config);
  if (phy == NULL) {
    ESP_LOGE(TAG, "Failed to create PHY");
    return ESP_FAIL;
  }

  /* Glue layer */
  esp_eth_config_t eth_config = ETH_DEFAULT_CONFIG(mac, phy);
  esp_err_t ret = esp_eth_driver_install(&eth_config, &s_eth_handle);
  if (ret != ESP_OK) {
    ESP_LOGE(TAG, "Ethernet driver install failed: %s", esp_err_to_name(ret));
    return ret;
  }

  /* Netif */
  esp_netif_config_t netif_cfg = ESP_NETIF_DEFAULT_ETH();
  s_eth_netif = esp_netif_new(&netif_cfg);
  if (s_eth_netif == NULL) {
    ESP_LOGE(TAG, "Failed to create ETH netif");
    return ESP_FAIL;
  }

  /* Attach the driver to the TCP/IP stack */
  esp_eth_netif_glue_handle_t glue = esp_eth_new_netif_glue(s_eth_handle);
  ret = esp_netif_attach(s_eth_netif, glue);
  if (ret != ESP_OK) {
    ESP_LOGE(TAG, "Netif attach failed: %s", esp_err_to_name(ret));
    return ret;
  }

  return ESP_OK;
}

/* ── Public API (matches wifi_manager interface) ────────────────────── */

void ethernet_qemu_init(const struct saved_ap_store *initial_store) {
  (void)initial_store; /* Not applicable for Ethernet */

  s_eth_event_group = xEventGroupCreate();

  /* Register event handlers */
  ESP_ERROR_CHECK(esp_event_handler_instance_register(
      ETH_EVENT, ESP_EVENT_ANY_ID, &eth_event_handler, NULL, NULL));

#if CONFIG_ETHERNET_QEMU_CONNECT_IPV4 ||                                       \
    CONFIG_ETHERNET_QEMU_CONNECT_UNSPECIFIED
  ESP_ERROR_CHECK(esp_event_handler_instance_register(
      IP_EVENT, IP_EVENT_ETH_GOT_IP, &got_ip_event_handler, NULL, NULL));
#endif

#if CONFIG_ETHERNET_QEMU_CONNECT_IPV6 ||                                       \
    CONFIG_ETHERNET_QEMU_CONNECT_UNSPECIFIED
  ESP_ERROR_CHECK(esp_event_handler_instance_register(
      IP_EVENT, IP_EVENT_GOT_IP6, &got_ip6_event_handler, NULL, NULL));
#endif

  ESP_ERROR_CHECK(esp_event_handler_instance_register(
      NETWORK_EVENT, NETWORK_EVENT_REQUEST, &network_request_handler, NULL,
      NULL));

  /* Initialise the OpenETH driver and netif */
  ESP_ERROR_CHECK(ethernet_qemu_driver_init());

  ESP_LOGI(TAG, "Ethernet QEMU initialised");
}

void ethernet_qemu_start_task(void) {
  /* Start the ethernet driver – this is all that's needed; DHCP is
     handled automatically by the netif/LWIP layer.
     Guard against ESP_ERR_INVALID_STATE in case an earlier
     NETWORK_EVENT_REQUEST already started the driver. */
  esp_err_t err = esp_eth_start(s_eth_handle);
  if (err == ESP_ERR_INVALID_STATE) {
    ESP_LOGI(TAG, "Ethernet driver already started, skipping.");
  } else {
    ESP_ERROR_CHECK(err);
    ESP_LOGI(TAG, "Ethernet driver started, waiting for link...");
  }
}

void ethernet_qemu_notify_store_changed(const struct saved_ap_store *store) {
  (void)store; /* Not applicable for Ethernet */
}

void ethernet_qemu_request_connect(void) {
  if (s_eth_handle == NULL) {
    ESP_LOGW(TAG, "Ethernet driver not initialised");
    return;
  }

  /* If already connected, nothing to do */
  EventBits_t bits = xEventGroupGetBits(s_eth_event_group);
  if (bits & ETH_CONNECTED_BIT) {
    return;
  }

  /* Just (re)start the driver if it was stopped */
  s_should_connect = true;
  esp_err_t err = esp_eth_start(s_eth_handle);
  if (err == ESP_ERR_INVALID_STATE) {
    ESP_LOGI(TAG, "Ethernet driver already running.");
  } else if (err != ESP_OK) {
    ESP_LOGE(TAG, "esp_eth_start failed: %s", esp_err_to_name(err));
  }
}

bool ethernet_qemu_is_connected(void) {
  if (s_eth_event_group == NULL) {
    return false;
  }
  EventBits_t bits = xEventGroupGetBits(s_eth_event_group);
  return (bits & ETH_CONNECTED_BIT) != 0;
}

void ethernet_qemu_start_config_ap(void) {
  /* No configuration AP is available when running under QEMU Ethernet.
     Log a warning so the caller knows this is a no-op. */
  ESP_LOGW(TAG, "Config AP not available in QEMU Ethernet mode");
}

#endif /* CONFIG_ETHERNET_QEMU_CONNECT */
