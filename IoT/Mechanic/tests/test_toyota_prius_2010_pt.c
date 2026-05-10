#include <math.h>
#include <stdint.h>

#include "unity.h"
#include "toyota_prius_2010_pt.h"

void setUp(void)
{
}

void tearDown(void)
{
}

static void assert_double_close(double expected, double actual, double tol)
{
    TEST_ASSERT_TRUE(fabs(expected - actual) <= tol);
}

void test_kinematics_pack_unpack_roundtrip(void)
{
    struct toyota_prius_2010_pt_kinematics_t input = {
        .yaw_rate = 600,
        .steering_torque = 700,
        .accel_y = 800,
    };
    uint8_t payload[TOYOTA_PRIUS_2010_PT_KINEMATICS_LENGTH] = {0};

    TEST_ASSERT_EQUAL_INT(TOYOTA_PRIUS_2010_PT_KINEMATICS_LENGTH,
                          toyota_prius_2010_pt_kinematics_pack(payload, &input, sizeof(payload)));

    struct toyota_prius_2010_pt_kinematics_t output = {0};
    TEST_ASSERT_EQUAL_INT(0,
                          toyota_prius_2010_pt_kinematics_unpack(&output, payload, sizeof(payload)));

    TEST_ASSERT_EQUAL_UINT16(input.yaw_rate, output.yaw_rate);
    TEST_ASSERT_EQUAL_UINT16(input.steering_torque, output.steering_torque);
    TEST_ASSERT_EQUAL_UINT16(input.accel_y, output.accel_y);
}

void test_wheel_speeds_pack_unpack_roundtrip(void)
{
    struct toyota_prius_2010_pt_wheel_speeds_t input = {
        .wheel_speed_fr = 20000,
        .wheel_speed_fl = 20100,
        .wheel_speed_rr = 20200,
        .wheel_speed_rl = 20300,
    };
    uint8_t payload[TOYOTA_PRIUS_2010_PT_WHEEL_SPEEDS_LENGTH] = {0};

    TEST_ASSERT_EQUAL_INT(TOYOTA_PRIUS_2010_PT_WHEEL_SPEEDS_LENGTH,
                          toyota_prius_2010_pt_wheel_speeds_pack(payload, &input, sizeof(payload)));

    struct toyota_prius_2010_pt_wheel_speeds_t output = {0};
    TEST_ASSERT_EQUAL_INT(0,
                          toyota_prius_2010_pt_wheel_speeds_unpack(&output, payload, sizeof(payload)));

    TEST_ASSERT_EQUAL_UINT16(input.wheel_speed_fr, output.wheel_speed_fr);
    TEST_ASSERT_EQUAL_UINT16(input.wheel_speed_fl, output.wheel_speed_fl);
    TEST_ASSERT_EQUAL_UINT16(input.wheel_speed_rr, output.wheel_speed_rr);
    TEST_ASSERT_EQUAL_UINT16(input.wheel_speed_rl, output.wheel_speed_rl);
}

void test_speed_pack_unpack_roundtrip(void)
{
    struct toyota_prius_2010_pt_speed_t input = {
        .encoder = 42,
        .speed = 12345,
        .checksum = 0xAA,
    };
    uint8_t payload[TOYOTA_PRIUS_2010_PT_SPEED_LENGTH] = {0};

    TEST_ASSERT_EQUAL_INT(TOYOTA_PRIUS_2010_PT_SPEED_LENGTH,
                          toyota_prius_2010_pt_speed_pack(payload, &input, sizeof(payload)));

    struct toyota_prius_2010_pt_speed_t output = {0};
    TEST_ASSERT_EQUAL_INT(0,
                          toyota_prius_2010_pt_speed_unpack(&output, payload, sizeof(payload)));

    TEST_ASSERT_EQUAL_UINT8(input.encoder, output.encoder);
    TEST_ASSERT_EQUAL_UINT16(input.speed, output.speed);
    TEST_ASSERT_EQUAL_UINT8(input.checksum, output.checksum);
}

void test_wheel_speed_encode_decode_phys(void)
{
    double mph = 55.55;
    uint16_t raw = toyota_prius_2010_pt_wheel_speeds_wheel_speed_fr_encode(mph);
    double decoded = toyota_prius_2010_pt_wheel_speeds_wheel_speed_fr_decode(raw);

    assert_double_close(mph, decoded, 0.01);
    TEST_ASSERT_TRUE(toyota_prius_2010_pt_wheel_speeds_wheel_speed_fr_is_in_range(raw));
}

int main(void)
{
    UNITY_BEGIN();
    RUN_TEST(test_kinematics_pack_unpack_roundtrip);
    RUN_TEST(test_wheel_speeds_pack_unpack_roundtrip);
    RUN_TEST(test_speed_pack_unpack_roundtrip);
    RUN_TEST(test_wheel_speed_encode_decode_phys);
    return UNITY_END();
}
