#include "canmodule.h"

#include "esp_log.h"
#include "esp_twai.h"
#include "esp_twai_onchip.h"

#include "dtc_reporter.h"
#include "freertos/FreeRTOS.h"
#include "freertos/portmacro.h"
#include "toyota_prius_2010_pt.h"

static const char *TAG = "canmodule";

static twai_node_handle_t s_node_hdl = NULL;
static can_decoded_signals_t s_signals = {0};
static portMUX_TYPE s_signals_lock = portMUX_INITIALIZER_UNLOCKED;

static const twai_onchip_node_config_t s_node_config = {
    .io_cfg.tx = 43,
    .io_cfg.rx = 44,
    .bit_timing.bitrate = 200000,
    .tx_queue_depth = 5,
};

static void decode_prius_frame_from_isr(const twai_frame_t *rx_frame) {
  switch (rx_frame->header.id) {
  case TOYOTA_PRIUS_2010_PT_SPEED_FRAME_ID: {
    struct toyota_prius_2010_pt_speed_t speed = {0};
    if (toyota_prius_2010_pt_speed_unpack(&speed, rx_frame->buffer,
                                          rx_frame->buffer_len) == 0) {
      s_signals.vehicle_speed_mph =
          (float)toyota_prius_2010_pt_speed_speed_decode(speed.speed);
    }
    break;
  }

  case TOYOTA_PRIUS_2010_PT_WHEEL_SPEEDS_FRAME_ID: {
    struct toyota_prius_2010_pt_wheel_speeds_t ws = {0};
    if (toyota_prius_2010_pt_wheel_speeds_unpack(&ws, rx_frame->buffer,
                                                 rx_frame->buffer_len) == 0) {
      s_signals.wheel_speed_fl_mph =
          (float)toyota_prius_2010_pt_wheel_speeds_wheel_speed_fl_decode(
              ws.wheel_speed_fl);
      s_signals.wheel_speed_fr_mph =
          (float)toyota_prius_2010_pt_wheel_speeds_wheel_speed_fr_decode(
              ws.wheel_speed_fr);
      s_signals.wheel_speed_rl_mph =
          (float)toyota_prius_2010_pt_wheel_speeds_wheel_speed_rl_decode(
              ws.wheel_speed_rl);
      s_signals.wheel_speed_rr_mph =
          (float)toyota_prius_2010_pt_wheel_speeds_wheel_speed_rr_decode(
              ws.wheel_speed_rr);
    }
    break;
  }

  case TOYOTA_PRIUS_2010_PT_STEER_ANGLE_SENSOR_FRAME_ID: {
    struct toyota_prius_2010_pt_steer_angle_sensor_t steer = {0};
    if (toyota_prius_2010_pt_steer_angle_sensor_unpack(
            &steer, rx_frame->buffer, rx_frame->buffer_len) == 0) {
      s_signals.steer_angle_deg =
          (float)toyota_prius_2010_pt_steer_angle_sensor_steer_angle_decode(
              steer.steer_angle);
      s_signals.steer_rate_deg_s =
          (float)toyota_prius_2010_pt_steer_angle_sensor_steer_rate_decode(
              steer.steer_rate);
    }
    break;
  }

  case TOYOTA_PRIUS_2010_PT_POWERTRAIN_FRAME_ID: {
    struct toyota_prius_2010_pt_powertrain_t powertrain = {0};
    if (toyota_prius_2010_pt_powertrain_unpack(&powertrain, rx_frame->buffer,
                                               rx_frame->buffer_len) == 0) {
      s_signals.engine_rpm =
          (float)toyota_prius_2010_pt_powertrain_engine_rpm_decode(
              powertrain.engine_rpm);
    }
    break;
  }

  case TOYOTA_PRIUS_2010_PT_GAS_PEDAL_FRAME_ID: {
    struct toyota_prius_2010_pt_gas_pedal_t gas = {0};
    if (toyota_prius_2010_pt_gas_pedal_unpack(&gas, rx_frame->buffer,
                                              rx_frame->buffer_len) == 0) {
      s_signals.gas_pedal =
          (float)toyota_prius_2010_pt_gas_pedal_gas_pedal_decode(gas.gas_pedal);
    }
    break;
  }

  case TOYOTA_PRIUS_2010_PT_BRAKE_FRAME_ID: {
    struct toyota_prius_2010_pt_brake_t brake = {0};
    if (toyota_prius_2010_pt_brake_unpack(&brake, rx_frame->buffer,
                                          rx_frame->buffer_len) == 0) {
      s_signals.brake_pedal =
          (float)toyota_prius_2010_pt_brake_brake_pedal_decode(
              brake.brake_pedal);
    }
    break;
  }

  case TOYOTA_PRIUS_2010_PT_GEAR_PACKET_FRAME_ID: {
    struct toyota_prius_2010_pt_gear_packet_t gear = {0};
    if (toyota_prius_2010_pt_gear_packet_unpack(&gear, rx_frame->buffer,
                                                rx_frame->buffer_len) == 0) {
      s_signals.gear = gear.gear;
    }
    break;
  }

  default:
    break;
  }
}

static bool twai_rx_cb(twai_node_handle_t handle,
                       const twai_rx_done_event_data_t *edata, void *user_ctx) {
  (void)edata;
  (void)user_ctx;

  uint8_t recv_buff[8] = {0};
  twai_frame_t rx_frame = {
      .buffer = recv_buff,
      .buffer_len = sizeof(recv_buff),
  };

  if (twai_node_receive_from_isr(handle, &rx_frame) == ESP_OK) {
    taskENTER_CRITICAL_ISR(&s_signals_lock);
    dtc_reporter_can_rx_isr(&rx_frame);
    decode_prius_frame_from_isr(&rx_frame);
    s_signals.rx_frames++;
    taskEXIT_CRITICAL_ISR(&s_signals_lock);
  }

  return false;
}

esp_err_t canmodule_init(void) {
  if (s_node_hdl != NULL) {
    return ESP_OK;
  }

  esp_err_t err = twai_new_node_onchip(&s_node_config, &s_node_hdl);
  if (err != ESP_OK) {
    ESP_LOGE(TAG, "twai_new_node_onchip failed: %s", esp_err_to_name(err));
    return err;
  }

  const twai_event_callbacks_t user_cbs = {
      .on_rx_done = twai_rx_cb,
  };

  err = twai_node_register_event_callbacks(s_node_hdl, &user_cbs, NULL);
  if (err != ESP_OK) {
    ESP_LOGE(TAG, "twai_node_register_event_callbacks failed: %s",
             esp_err_to_name(err));
    return err;
  }

  // REMOVED twai_node_enable() FROM HERE

  ESP_LOGI(TAG, "TWAI initialized (Not yet started)");
  return ESP_OK;
}

esp_err_t canmodule_start(void) {
  if (s_node_hdl == NULL) {
    return ESP_ERR_INVALID_STATE;
  }

  esp_err_t err = twai_node_enable(s_node_hdl);

  // If the node is already running, twai_node_enable returns
  // ESP_ERR_INVALID_STATE. Since esp_isotp automatically starts the node, we
  // can safely treat this as a success.
  if (err == ESP_ERR_INVALID_STATE) {
    ESP_LOGI(TAG,
             "TWAI node is already enabled (likely by ISO-TP). Proceeding.");
    return ESP_OK;
  } else if (err != ESP_OK) {
    ESP_LOGE(TAG, "twai_node_enable failed: %s", esp_err_to_name(err));
    return err;
  }

  ESP_LOGI(TAG, "TWAI started and DBC decoding enabled");
  return ESP_OK;
}
esp_err_t canmodule_get_latest_signals(can_decoded_signals_t *out_signals) {
  if (out_signals == NULL) {
    return ESP_ERR_INVALID_ARG;
  }

  taskENTER_CRITICAL(&s_signals_lock);
  *out_signals = s_signals;
  taskEXIT_CRITICAL(&s_signals_lock);

  return ESP_OK;
}

twai_node_handle_t canmodule_get_twai_handle(void) { return s_node_hdl; }
