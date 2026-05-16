#include "canmodule.h"

#include "esp_log.h"
#include "esp_twai.h"
#include "esp_twai_onchip.h"
#include <string.h>

#include "dtc_reporter.h"
#include "freertos/FreeRTOS.h"
#include "freertos/queue.h"
#include "freertos/task.h"
#include "toyota_prius_2010_pt.h"

static const char *TAG = "canmodule";

static twai_node_handle_t s_node_hdl = NULL;
static can_decoded_signals_t s_signals = {0};
static portMUX_TYPE s_signals_lock = portMUX_INITIALIZER_UNLOCKED;

// Queue to hold CAN frames out of the ISR
static QueueHandle_t s_can_rx_queue = NULL;

typedef struct {
  uint32_t id;
  uint8_t dlc;
  uint8_t data[8];
} can_queue_msg_t;

static const twai_onchip_node_config_t s_node_config = {
    .io_cfg.tx = 43,
    .io_cfg.rx = 44,
    .bit_timing.bitrate = 200000,
    .tx_queue_depth = 5,
};

// Safe decoding out of the ISR
static void decode_prius_frame(const can_queue_msg_t *msg) {
  switch (msg->id) {
  case TOYOTA_PRIUS_2010_PT_SPEED_FRAME_ID: {
    struct toyota_prius_2010_pt_speed_t speed = {0};
    if (toyota_prius_2010_pt_speed_unpack(&speed, msg->data, msg->dlc) == 0) {
      s_signals.vehicle_speed_mph =
          (float)toyota_prius_2010_pt_speed_speed_decode(speed.speed);
    }
    break;
  }

  case TOYOTA_PRIUS_2010_PT_WHEEL_SPEEDS_FRAME_ID: {
    struct toyota_prius_2010_pt_wheel_speeds_t ws = {0};
    if (toyota_prius_2010_pt_wheel_speeds_unpack(&ws, msg->data, msg->dlc) ==
        0) {
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
    if (toyota_prius_2010_pt_steer_angle_sensor_unpack(&steer, msg->data,
                                                       msg->dlc) == 0) {
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
    if (toyota_prius_2010_pt_powertrain_unpack(&powertrain, msg->data,
                                               msg->dlc) == 0) {
      s_signals.engine_rpm =
          (float)toyota_prius_2010_pt_powertrain_engine_rpm_decode(
              powertrain.engine_rpm);
    }
    break;
  }

  case TOYOTA_PRIUS_2010_PT_GAS_PEDAL_FRAME_ID: {
    struct toyota_prius_2010_pt_gas_pedal_t gas = {0};
    if (toyota_prius_2010_pt_gas_pedal_unpack(&gas, msg->data, msg->dlc) == 0) {
      s_signals.gas_pedal =
          (float)toyota_prius_2010_pt_gas_pedal_gas_pedal_decode(gas.gas_pedal);
    }
    break;
  }

  case TOYOTA_PRIUS_2010_PT_BRAKE_FRAME_ID: {
    struct toyota_prius_2010_pt_brake_t brake = {0};
    if (toyota_prius_2010_pt_brake_unpack(&brake, msg->data, msg->dlc) == 0) {
      s_signals.brake_pedal =
          (float)toyota_prius_2010_pt_brake_brake_pedal_decode(
              brake.brake_pedal);
    }
    break;
  }

  case TOYOTA_PRIUS_2010_PT_GEAR_PACKET_FRAME_ID: {
    struct toyota_prius_2010_pt_gear_packet_t gear = {0};
    if (toyota_prius_2010_pt_gear_packet_unpack(&gear, msg->data, msg->dlc) ==
        0) {
      s_signals.gear = gear.gear;
    }
    break;
  }

  default:
    break;
  }
}

// Keep the ISR fast: copy data and yield.
static bool twai_rx_cb(twai_node_handle_t handle,
                       const twai_rx_done_event_data_t *edata, void *user_ctx) {
  (void)edata;
  (void)user_ctx;

  uint8_t recv_buff[8] = {0};
  twai_frame_t rx_frame = {
      .buffer = recv_buff,
      .buffer_len = sizeof(recv_buff),
  };

  bool higher_priority_task_woken = false;

  if (twai_node_receive_from_isr(handle, &rx_frame) == ESP_OK) {
    if (s_can_rx_queue) {
      can_queue_msg_t q_msg;
      q_msg.id = rx_frame.header.id;
      q_msg.dlc = rx_frame.buffer_len;
      memcpy(q_msg.data, rx_frame.buffer, rx_frame.buffer_len);

      xQueueSendFromISR(s_can_rx_queue, &q_msg,
                        (BaseType_t *)&higher_priority_task_woken);
    }
  }

  return higher_priority_task_woken;
}

// The Central Dispatcher Task
static void can_rx_router_task(void *arg) {
  can_queue_msg_t q_msg;

  while (1) {
    // Wait indefinitely for a frame from the ISR
    if (xQueueReceive(s_can_rx_queue, &q_msg, portMAX_DELAY) == pdTRUE) {

      // 1. Send frame to dtc_reporter for ISO-TP inspection
      dtc_reporter_feed_frame(q_msg.id, q_msg.data, q_msg.dlc);

      // 2. Decode native telemetry variables
      taskENTER_CRITICAL(&s_signals_lock);
      decode_prius_frame(&q_msg);
      s_signals.rx_frames++;
      taskEXIT_CRITICAL(&s_signals_lock);
    }
  }
}

esp_err_t canmodule_init(void) {
  if (s_node_hdl != NULL) {
    return ESP_OK;
  }

  // Initialize queue and task
  s_can_rx_queue = xQueueCreate(32, sizeof(can_queue_msg_t));
  xTaskCreate(can_rx_router_task, "can_rx_router", 4096, NULL, 5, NULL);

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

  ESP_LOGI(TAG, "TWAI initialized (Not yet started)");
  return ESP_OK;
}

esp_err_t canmodule_start(void) {
  if (s_node_hdl == NULL) {
    return ESP_ERR_INVALID_STATE;
  }

  esp_err_t err = twai_node_enable(s_node_hdl);

  if (err == ESP_ERR_INVALID_STATE) {
    ESP_LOGI(TAG, "TWAI node is already enabled. Proceeding.");
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