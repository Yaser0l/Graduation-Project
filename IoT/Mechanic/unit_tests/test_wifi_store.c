#include <string.h>

#include "unity.h"

#include "nvs.h"

#include "wifi_store.h"

#include "wifi_store.c"

static void wifi_store_test_reset(void)
{
    nvs_stub_reset();
}

void setUp(void)
{
    wifi_store_test_reset();
}

void tearDown(void)
{
}

void test_wifi_store_load_null_store(void)
{
    TEST_ASSERT_EQUAL(ESP_ERR_INVALID_ARG, wifi_store_load(NULL));
}

void test_wifi_store_load_nvs_open_fail_clears_store(void)
{
    saved_ap_store_t store = {.count = 2};
    nvs_stub_set_open_result(ESP_FAIL);

    TEST_ASSERT_EQUAL(ESP_OK, wifi_store_load(&store));
    TEST_ASSERT_EQUAL_UINT8(0, store.count);
}

void test_wifi_store_load_not_found_clears_store(void)
{
    saved_ap_store_t store = {.count = 1};
    nvs_stub_set_get_blob_result(ESP_ERR_NVS_NOT_FOUND);

    TEST_ASSERT_EQUAL(ESP_OK, wifi_store_load(&store));
    TEST_ASSERT_EQUAL_UINT8(0, store.count);
}

void test_wifi_store_load_invalid_blob_resets(void)
{
    saved_ap_store_t store = {.count = 1};
    nvs_stub_set_blob_data(&store, sizeof(store));
    nvs_stub_set_get_blob_result(ESP_ERR_INVALID_SIZE);

    TEST_ASSERT_EQUAL(ESP_FAIL, wifi_store_load(&store));
    TEST_ASSERT_EQUAL_UINT8(0, store.count);
}

void test_wifi_store_load_rejects_large_count(void)
{
    saved_ap_store_t store = {0};
    store.count = MAX_SAVED_APS + 1;
    nvs_stub_set_blob_data(&store, sizeof(store));

    TEST_ASSERT_EQUAL(ESP_FAIL, wifi_store_load(&store));
    TEST_ASSERT_EQUAL_UINT8(0, store.count);
}

void test_wifi_store_load_success(void)
{
    saved_ap_store_t stored = {0};
    stored.count = 1;
    strncpy(stored.entries[0].ssid, "ssid", sizeof(stored.entries[0].ssid) - 1);
    strncpy(stored.entries[0].passphrase, "pass", sizeof(stored.entries[0].passphrase) - 1);
    nvs_stub_set_blob_data(&stored, sizeof(stored));

    saved_ap_store_t store = {0};
    TEST_ASSERT_EQUAL(ESP_OK, wifi_store_load(&store));
    TEST_ASSERT_EQUAL_UINT8(1, store.count);
    TEST_ASSERT_EQUAL_STRING("ssid", store.entries[0].ssid);
}

void test_wifi_store_persist_null_store(void)
{
    TEST_ASSERT_EQUAL(ESP_ERR_INVALID_ARG, wifi_store_persist(NULL));
}

void test_wifi_store_persist_open_fail(void)
{
    saved_ap_store_t store = {0};
    nvs_stub_set_open_result(ESP_FAIL);

    TEST_ASSERT_EQUAL(ESP_FAIL, wifi_store_persist(&store));
}

void test_wifi_store_persist_set_blob_fail(void)
{
    saved_ap_store_t store = {0};
    nvs_stub_set_set_blob_result(ESP_FAIL);

    TEST_ASSERT_EQUAL(ESP_FAIL, wifi_store_persist(&store));
}

void test_wifi_store_persist_commit_fail(void)
{
    saved_ap_store_t store = {0};
    nvs_stub_set_commit_result(ESP_FAIL);

    TEST_ASSERT_EQUAL(ESP_FAIL, wifi_store_persist(&store));
}

void test_wifi_store_find_index(void)
{
    saved_ap_store_t store = {0};
    store.count = 2;
    strncpy(store.entries[0].ssid, "a", sizeof(store.entries[0].ssid) - 1);
    strncpy(store.entries[1].ssid, "b", sizeof(store.entries[1].ssid) - 1);

    uint8_t idx = 0;
    TEST_ASSERT_TRUE(wifi_store_find_index(&store, "b", &idx));
    TEST_ASSERT_EQUAL_UINT8(1, idx);
    TEST_ASSERT_FALSE(wifi_store_find_index(&store, "c", &idx));
}

void test_wifi_store_add_or_update_adds_new(void)
{
    saved_ap_store_t store = {0};
    bool updated = true;

    TEST_ASSERT_TRUE(wifi_store_add_or_update(&store, "ssid", "pass", &updated));
    TEST_ASSERT_FALSE(updated);
    TEST_ASSERT_EQUAL_UINT8(1, store.count);
    TEST_ASSERT_EQUAL_STRING("ssid", store.entries[0].ssid);
    TEST_ASSERT_EQUAL_STRING("pass", store.entries[0].passphrase);
}

void test_wifi_store_add_or_update_updates_existing(void)
{
    saved_ap_store_t store = {0};
    store.count = 1;
    strncpy(store.entries[0].ssid, "ssid", sizeof(store.entries[0].ssid) - 1);

    bool updated = false;
    TEST_ASSERT_TRUE(wifi_store_add_or_update(&store, "ssid", "newpass", &updated));
    TEST_ASSERT_TRUE(updated);
    TEST_ASSERT_EQUAL_STRING("newpass", store.entries[0].passphrase);
    TEST_ASSERT_EQUAL_UINT8(1, store.count);
}

void test_wifi_store_add_or_update_rejects_full(void)
{
    saved_ap_store_t store = {0};
    store.count = MAX_SAVED_APS;

    TEST_ASSERT_FALSE(wifi_store_add_or_update(&store, "ssid", "pass", NULL));
}

void test_wifi_store_clear(void)
{
    saved_ap_store_t store = {0};
    store.count = 1;
    strncpy(store.entries[0].ssid, "ssid", sizeof(store.entries[0].ssid) - 1);

    wifi_store_clear(&store);

    TEST_ASSERT_EQUAL_UINT8(0, store.count);
    TEST_ASSERT_EQUAL_STRING("", store.entries[0].ssid);
}

int main(void)
{
    UNITY_BEGIN();

    RUN_TEST(test_wifi_store_load_null_store);
    RUN_TEST(test_wifi_store_load_nvs_open_fail_clears_store);
    RUN_TEST(test_wifi_store_load_not_found_clears_store);
    RUN_TEST(test_wifi_store_load_invalid_blob_resets);
    RUN_TEST(test_wifi_store_load_rejects_large_count);
    RUN_TEST(test_wifi_store_load_success);
    RUN_TEST(test_wifi_store_persist_null_store);
    RUN_TEST(test_wifi_store_persist_open_fail);
    RUN_TEST(test_wifi_store_persist_set_blob_fail);
    RUN_TEST(test_wifi_store_persist_commit_fail);
    RUN_TEST(test_wifi_store_find_index);
    RUN_TEST(test_wifi_store_add_or_update_adds_new);
    RUN_TEST(test_wifi_store_add_or_update_updates_existing);
    RUN_TEST(test_wifi_store_add_or_update_rejects_full);
    RUN_TEST(test_wifi_store_clear);

    return UNITY_END();
}
