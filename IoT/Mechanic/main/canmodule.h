#ifndef CANMODULE_H
#define CANMODULE_H

#include "esp_err.h"
#include <stdint.h>

typedef struct
{
    float vehicle_speed_mph;
    float wheel_speed_fl_mph;
    float wheel_speed_fr_mph;
    float wheel_speed_rl_mph;
    float wheel_speed_rr_mph;
    float steer_angle_deg;
    float steer_rate_deg_s;
    float engine_rpm;
    float gas_pedal;
    float brake_pedal;
    uint8_t gear;
    uint32_t rx_frames;
} can_decoded_signals_t;

esp_err_t canmodule_init(void);
esp_err_t canmodule_get_latest_signals(can_decoded_signals_t *out_signals);

#endif
