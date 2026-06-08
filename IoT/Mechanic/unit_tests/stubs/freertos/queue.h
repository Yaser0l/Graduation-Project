#pragma once

#include "FreeRTOS.h"
#include <stdbool.h>
#include <stdint.h>

typedef void* QueueHandle_t;

QueueHandle_t xQueueCreate(uint32_t queue_length, uint32_t item_size);
int32_t xQueueSendFromISR(QueueHandle_t queue, const void* item, int32_t* higher_prio_woken);
int32_t xQueueReceive(QueueHandle_t queue, void* buffer, uint32_t ticks_to_wait);
