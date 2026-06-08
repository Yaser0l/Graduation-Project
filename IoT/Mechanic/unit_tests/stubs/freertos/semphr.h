#pragma once

#include "FreeRTOS.h"
#include <stdint.h>

typedef void* SemaphoreHandle_t;

SemaphoreHandle_t xSemaphoreCreateMutex(void);
int32_t xSemaphoreTake(SemaphoreHandle_t sem, uint32_t ticks_to_wait);
int32_t xSemaphoreGive(SemaphoreHandle_t sem);
