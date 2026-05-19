#include "canmodule.h"

#include "dtc_reporter.h"
#include "esp_log.h"
#include "esp_rom_sys.h"
#include "esp_timer.h"
#include "esp_twai.h"
#include "esp_twai_onchip.h"
#include "freertos/FreeRTOS.h"
#include "freertos/queue.h"
#include "freertos/task.h"
#include "toyota_prius_2010_pt.h"
#include <string.h>

static volatile uint32_t s_rx_count = 0;
static volatile uint32_t s_rx_dropped = 0;
static volatile uint32_t s_rx_invalid_dlc = 0;
static const char *TAG = "canmodule";

static twai_node_handle_t s_node_hdl = NULL;
static can_decoded_signals_t s_signals = {0};
static portMUX_TYPE s_signals_lock = portMUX_INITIALIZER_UNLOCKED;
static volatile bool s_isotp_priority_only = false;

// Queue to hold CAN frames out of the ISR
static QueueHandle_t s_can_rx_queue = NULL;
static QueueHandle_t s_can_isotp_queue = NULL;

typedef struct {
  uint32_t id;
  uint8_t dlc;
  uint8_t data[8];
} can_queue_msg_t;

static const twai_onchip_node_config_t s_node_config = {
    .io_cfg.tx = 4,
    .io_cfg.rx = 5,
    .bit_timing.bitrate = 500000,
    .tx_queue_depth = 5,
    .flags.enable_self_test = 0,
};

#define CAN_RX_MAX_FRAMES_PER_ISR 16U
#define CAN_RX_LOG_INTERVAL_US 1000000ULL
#define CAN_RX_QUEUE_LEN 128U
#define CAN_ISOTP_QUEUE_LEN 32U
#define CAN_OBD_RESP_ID_MIN 0x7E8
#define CAN_OBD_RESP_ID_MAX 0x7EF

static bool is_isotp_response_id(uint32_t id) {
  return id >= CAN_OBD_RESP_ID_MIN && id <= CAN_OBD_RESP_ID_MAX;
}

// Safe decoding out of the ISR
static bool decode_prius_frame(const can_queue_msg_t *msg) {
  switch (msg->id) {
  case TOYOTA_PRIUS_2010_PT_SPEED_FRAME_ID: {
    struct toyota_prius_2010_pt_speed_t speed = {0};
    if (toyota_prius_2010_pt_speed_unpack(&speed, msg->data, msg->dlc) == 0) {
      s_signals.vehicle_speed_mph =
          (float)toyota_prius_2010_pt_speed_speed_decode(speed.speed);
    }
    return true;
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
    return true;
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
    return true;
  }

  case TOYOTA_PRIUS_2010_PT_POWERTRAIN_FRAME_ID: {
    struct toyota_prius_2010_pt_powertrain_t powertrain = {0};
    if (toyota_prius_2010_pt_powertrain_unpack(&powertrain, msg->data,
                                               msg->dlc) == 0) {
      s_signals.engine_rpm =
          (float)toyota_prius_2010_pt_powertrain_engine_rpm_decode(
              powertrain.engine_rpm);
    }
    return true;
  }

  case TOYOTA_PRIUS_2010_PT_GAS_PEDAL_FRAME_ID: {
    struct toyota_prius_2010_pt_gas_pedal_t gas = {0};
    if (toyota_prius_2010_pt_gas_pedal_unpack(&gas, msg->data, msg->dlc) == 0) {
      s_signals.gas_pedal =
          (float)toyota_prius_2010_pt_gas_pedal_gas_pedal_decode(gas.gas_pedal);
    }
    return true;
  }

  case TOYOTA_PRIUS_2010_PT_BRAKE_FRAME_ID: {
    struct toyota_prius_2010_pt_brake_t brake = {0};
    if (toyota_prius_2010_pt_brake_unpack(&brake, msg->data, msg->dlc) == 0) {
      s_signals.brake_pedal =
          (float)toyota_prius_2010_pt_brake_brake_pedal_decode(
              brake.brake_pedal);
    }
    return true;
  }

  case TOYOTA_PRIUS_2010_PT_GEAR_PACKET_FRAME_ID: {
    struct toyota_prius_2010_pt_gear_packet_t gear = {0};
    if (toyota_prius_2010_pt_gear_packet_unpack(&gear, msg->data, msg->dlc) ==
        0) {
      s_signals.gear = gear.gear;
    }
    return true;
  }

  default:
    return false;
  }
}

// Keep the ISR fast: copy data and yield.
static bool twai_rx_cb(twai_node_handle_t handle,
                       const twai_rx_done_event_data_t *edata, void *user_ctx) {
  (void)edata;
  (void)user_ctx;

  BaseType_t higher_priority_task_woken = pdFALSE;

  // Limit per-ISR work to avoid starving other tasks.
  for (uint32_t i = 0; i < CAN_RX_MAX_FRAMES_PER_ISR; ++i) {
    // CRITICAL: Initialize this INSIDE the loop.
    // The driver dynamically shrinks buffer_len, so it must be reset to 8 every
    // iteration!
    uint8_t recv_buff[8] = {0};
    twai_frame_t rx_frame = {
        .buffer = recv_buff,
        .buffer_len = sizeof(recv_buff),
    };

    // If it doesn't return ESP_OK, the hardware queue is empty. Break the loop.
    if (twai_node_receive_from_isr(handle, &rx_frame) != ESP_OK) {
      break;
    }
    if (rx_frame.header.dlc > 8) {
      s_rx_invalid_dlc++;
      continue;
    }

    if (s_isotp_priority_only && !is_isotp_response_id(rx_frame.header.id)) {
      continue;
    }

    if (s_can_rx_queue || s_can_isotp_queue) {
      can_queue_msg_t q_msg;
      q_msg.id = rx_frame.header.id;
      size_t data_len = rx_frame.buffer_len;
      if (data_len > sizeof(q_msg.data)) {
        data_len = sizeof(q_msg.data);
      }
      q_msg.dlc = (uint8_t)data_len;
      memcpy(q_msg.data, rx_frame.buffer, data_len);

      QueueHandle_t target_queue = s_can_rx_queue;
      if (is_isotp_response_id(q_msg.id) && s_can_isotp_queue) {
        target_queue = s_can_isotp_queue;
      }

      if (target_queue &&
          xQueueSendFromISR(target_queue, &q_msg,
                            &higher_priority_task_woken) != pdTRUE) {
        if (target_queue == s_can_isotp_queue && s_can_rx_queue) {
          if (xQueueSendFromISR(s_can_rx_queue, &q_msg,
                                &higher_priority_task_woken) != pdTRUE) {
            s_rx_dropped++;
          }
        } else {
          s_rx_dropped++;
        }
      }
    }
  }

  return higher_priority_task_woken == pdTRUE;
}

// The Central Dispatcher Task
static void can_rx_router_task(void *arg) {
  can_queue_msg_t q_msg;
  uint64_t last_log_us = 0;

  while (1) {
    bool processed_isotp = false;
    while (s_can_isotp_queue &&
           xQueueReceive(s_can_isotp_queue, &q_msg, 0) == pdTRUE) {
      processed_isotp = true;

      // Send frame to dtc_reporter for ISO-TP inspection
      dtc_reporter_feed_frame(q_msg.id, q_msg.data, q_msg.dlc);

      s_rx_count++;
      uint64_t now_us = esp_timer_get_time();
      if ((now_us - last_log_us) >= CAN_RX_LOG_INTERVAL_US) {
        last_log_us = now_us;
        ESP_LOGI(
            TAG,
            "CAN RX: %lu frames (dropped=%lu invalid_dlc=%lu) last id=0x%lx",
            (unsigned long)s_rx_count, (unsigned long)s_rx_dropped,
            (unsigned long)s_rx_invalid_dlc, (unsigned long)q_msg.id);
      }
    }

    if (processed_isotp) {
      continue;
    }

    if (xQueueReceive(s_can_rx_queue, &q_msg, pdMS_TO_TICKS(10)) != pdTRUE) {
      continue;
    }

    // Send frame to dtc_reporter for ISO-TP inspection
    dtc_reporter_feed_frame(q_msg.id, q_msg.data, q_msg.dlc);

    s_rx_count++;
    uint64_t now_us = esp_timer_get_time();
    if ((now_us - last_log_us) >= CAN_RX_LOG_INTERVAL_US) {
      last_log_us = now_us;
      ESP_LOGI(TAG,
               "CAN RX: %lu frames (dropped=%lu invalid_dlc=%lu) last id=0x%lx",
               (unsigned long)s_rx_count, (unsigned long)s_rx_dropped,
               (unsigned long)s_rx_invalid_dlc, (unsigned long)q_msg.id);
    }

    // Decode native telemetry variables
    bool handled = false;

    taskENTER_CRITICAL(&s_signals_lock);
    handled = decode_prius_frame(&q_msg);
    s_signals.rx_frames++;
    taskEXIT_CRITICAL(&s_signals_lock);

    if (!handled) {
      if (is_isotp_response_id(q_msg.id)) {
        continue;
      }
      ESP_LOGW(TAG, "Unhandled CAN ID: 0x%lx", q_msg.id);
    }
  }
}
// Callback for when the TWAI controller changes state (e.g., Active -> Bus-Off)
static bool IRAM_ATTR twai_state_change_cb(
    twai_node_handle_t handle, const twai_state_change_event_data_t *edata,
    void *user_ctx) {

  esp_rom_printf("TWAI State Changed! Old: %d, New: %d\n", edata->old_sta,
                 edata->new_sta);

  // States: 0 = Active, 1 = Warning, 2 = Passive, 3 = Bus-Off
  if (edata->new_sta == TWAI_ERROR_BUS_OFF) {
    esp_rom_printf(
        "CRITICAL: TWAI entered BUS-OFF state! Disconnected from bus.\n");
    // NOTE: You cannot call twai_node_recover() here. You must signal a
    // FreeRTOS task to do it using xQueueSendFromISR or a Task Notification.
  }

  return false; // Return false since we didn't unblock a higher-priority task
}

// Callback for specific bus errors (e.g., missing ACK, stuff error, format
// error)
static bool IRAM_ATTR twai_error_cb(twai_node_handle_t handle,
                                    const twai_error_event_data_t *edata,
                                    void *user_ctx) {

  // Print the raw hex value of the error flag
  esp_rom_printf("TWAI Error Flag Triggered: 0x%lx\n", edata->err_flags.val);

  // You can check specific bitfields for granular debugging:
  if (edata->err_flags.ack_err) {
    esp_rom_printf(" -> ACK Error: Frame transmitted but no other node "
                   "acknowledged it.\n");
  }
  if (edata->err_flags.stuff_err) {
    esp_rom_printf(
        " -> Stuff Error: Physical bus interference or baud rate mismatch.\n");
  }

  return false;
}
esp_err_t canmodule_init(void) {
  if (s_node_hdl != NULL) {
    return ESP_OK;
  }

  // Initialize queue and task
  s_can_rx_queue = xQueueCreate(CAN_RX_QUEUE_LEN, sizeof(can_queue_msg_t));
  s_can_isotp_queue =
      xQueueCreate(CAN_ISOTP_QUEUE_LEN, sizeof(can_queue_msg_t));
  xTaskCreate(can_rx_router_task, "can_rx_router", 4096, NULL, 5, NULL);

  esp_err_t err = twai_new_node_onchip(&s_node_config, &s_node_hdl);
  if (err != ESP_OK) {
    ESP_LOGE(TAG, "twai_new_node_onchip failed: %s", esp_err_to_name(err));
    return err;
  }

  twai_mask_filter_config_t filter_cfg = {
      .id = 0,
      .mask = 0, // A mask of 0 means ignore the ID bits and accept everything
      .is_ext = false,
  };
  twai_node_config_mask_filter(s_node_hdl, 0, &filter_cfg);

  const twai_event_callbacks_t user_cbs = {.on_rx_done = twai_rx_cb,
                                           .on_state_change =
                                               twai_state_change_cb,
                                           .on_error = twai_error_cb};

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

void canmodule_set_isotp_priority(bool enable) {
  s_isotp_priority_only = enable;
}