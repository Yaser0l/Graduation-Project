#include <math.h>
#include <string.h>

#include "unity.h"
#include "toyota_prius_2010_pt.h"
#include "canmodule.h"
#include "esp_twai_stubs.h"

#include "canmodule.c"

static int s_dtc_isr_calls = 0;

void dtc_reporter_can_rx_isr(const twai_frame_t *rx_frame)
{
    (void)rx_frame;
    s_dtc_isr_calls++;
}

static void canmodule_test_reset(void)
{
    s_node_hdl = NULL;
    memset(&s_signals, 0, sizeof(s_signals));
    s_signals_lock = portMUX_INITIALIZER_UNLOCKED;
    s_dtc_isr_calls = 0;
}

void setUp(void)
{
    twai_stub_reset();
    canmodule_test_reset();
}

void tearDown(void)
{
}

void test_canmodule_init_success_registers_callback(void)
{
    twai_stub_set_results(ESP_OK, ESP_OK, ESP_OK, ESP_OK);

    TEST_ASSERT_EQUAL(ESP_OK, canmodule_init());
    TEST_ASSERT_NOT_NULL(canmodule_get_twai_handle());

    TEST_ASSERT_EQUAL_INT(1, twai_stub_get_new_node_calls());
    TEST_ASSERT_EQUAL_INT(1, twai_stub_get_register_calls());
    TEST_ASSERT_EQUAL_INT(1, twai_stub_get_enable_calls());

    const twai_event_callbacks_t *cbs = twai_stub_get_callbacks();
    TEST_ASSERT_NOT_NULL(cbs);
    TEST_ASSERT_NOT_NULL(cbs->on_rx_done);
}

void test_canmodule_init_is_idempotent(void)
{
    twai_stub_set_results(ESP_OK, ESP_OK, ESP_OK, ESP_OK);

    TEST_ASSERT_EQUAL(ESP_OK, canmodule_init());
    TEST_ASSERT_EQUAL(ESP_OK, canmodule_init());

    TEST_ASSERT_EQUAL_INT(1, twai_stub_get_new_node_calls());
    TEST_ASSERT_EQUAL_INT(1, twai_stub_get_register_calls());
    TEST_ASSERT_EQUAL_INT(1, twai_stub_get_enable_calls());
}

void test_canmodule_get_latest_signals_null(void)
{
    TEST_ASSERT_EQUAL(ESP_ERR_INVALID_ARG, canmodule_get_latest_signals(NULL));
}

void test_canmodule_rx_speed_updates_signals(void)
{
    twai_stub_set_results(ESP_OK, ESP_OK, ESP_OK, ESP_OK);
    TEST_ASSERT_EQUAL(ESP_OK, canmodule_init());

    struct toyota_prius_2010_pt_speed_t speed = {
        .encoder = 1,
        .speed = 10000,
        .checksum = 0x5A,
    };
    uint8_t payload[TOYOTA_PRIUS_2010_PT_SPEED_LENGTH] = {0};

    TEST_ASSERT_EQUAL_INT(TOYOTA_PRIUS_2010_PT_SPEED_LENGTH,
                          toyota_prius_2010_pt_speed_pack(payload, &speed, sizeof(payload)));

    twai_stub_set_next_frame(TOYOTA_PRIUS_2010_PT_SPEED_FRAME_ID, payload, sizeof(payload));

    const twai_event_callbacks_t *cbs = twai_stub_get_callbacks();
    TEST_ASSERT_NOT_NULL(cbs->on_rx_done);

    cbs->on_rx_done(twai_stub_get_handle(), NULL, NULL);

    can_decoded_signals_t signals = {0};
    TEST_ASSERT_EQUAL(ESP_OK, canmodule_get_latest_signals(&signals));

    float expected = (float)toyota_prius_2010_pt_speed_speed_decode(speed.speed);
    TEST_ASSERT_FLOAT_WITHIN(0.01f, expected, signals.vehicle_speed_mph);
    TEST_ASSERT_EQUAL_UINT32(1, signals.rx_frames);
    TEST_ASSERT_EQUAL_INT(1, s_dtc_isr_calls);
}

void test_canmodule_rx_wheel_speeds_updates_signals(void)
{
    twai_stub_set_results(ESP_OK, ESP_OK, ESP_OK, ESP_OK);
    TEST_ASSERT_EQUAL(ESP_OK, canmodule_init());

    struct toyota_prius_2010_pt_wheel_speeds_t ws = {
        .wheel_speed_fl = 21000,
        .wheel_speed_fr = 22000,
        .wheel_speed_rl = 23000,
        .wheel_speed_rr = 24000,
    };
    uint8_t payload[TOYOTA_PRIUS_2010_PT_WHEEL_SPEEDS_LENGTH] = {0};

    TEST_ASSERT_EQUAL_INT(TOYOTA_PRIUS_2010_PT_WHEEL_SPEEDS_LENGTH,
                          toyota_prius_2010_pt_wheel_speeds_pack(payload, &ws, sizeof(payload)));

    twai_stub_set_next_frame(TOYOTA_PRIUS_2010_PT_WHEEL_SPEEDS_FRAME_ID, payload, sizeof(payload));

    const twai_event_callbacks_t *cbs = twai_stub_get_callbacks();
    TEST_ASSERT_NOT_NULL(cbs->on_rx_done);

    cbs->on_rx_done(twai_stub_get_handle(), NULL, NULL);

    can_decoded_signals_t signals = {0};
    TEST_ASSERT_EQUAL(ESP_OK, canmodule_get_latest_signals(&signals));

    float fl = (float)toyota_prius_2010_pt_wheel_speeds_wheel_speed_fl_decode(ws.wheel_speed_fl);
    float fr = (float)toyota_prius_2010_pt_wheel_speeds_wheel_speed_fr_decode(ws.wheel_speed_fr);
    float rl = (float)toyota_prius_2010_pt_wheel_speeds_wheel_speed_rl_decode(ws.wheel_speed_rl);
    float rr = (float)toyota_prius_2010_pt_wheel_speeds_wheel_speed_rr_decode(ws.wheel_speed_rr);

    TEST_ASSERT_FLOAT_WITHIN(0.01f, fl, signals.wheel_speed_fl_mph);
    TEST_ASSERT_FLOAT_WITHIN(0.01f, fr, signals.wheel_speed_fr_mph);
    TEST_ASSERT_FLOAT_WITHIN(0.01f, rl, signals.wheel_speed_rl_mph);
    TEST_ASSERT_FLOAT_WITHIN(0.01f, rr, signals.wheel_speed_rr_mph);
    TEST_ASSERT_EQUAL_UINT32(1, signals.rx_frames);
    TEST_ASSERT_EQUAL_INT(1, s_dtc_isr_calls);
}

int main(void)
{
    UNITY_BEGIN();
    RUN_TEST(test_canmodule_init_success_registers_callback);
    RUN_TEST(test_canmodule_init_is_idempotent);
    RUN_TEST(test_canmodule_get_latest_signals_null);
    RUN_TEST(test_canmodule_rx_speed_updates_signals);
    RUN_TEST(test_canmodule_rx_wheel_speeds_updates_signals);
    return UNITY_END();
}
