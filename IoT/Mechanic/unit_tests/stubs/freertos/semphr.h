#pragma once

#include "FreeRTOS.h"

typedef void *SemaphoreHandle_t;

#define pdTRUE 1
#define pdFALSE 0
#define portMAX_DELAY 0xffffffffu

static inline SemaphoreHandle_t xSemaphoreCreateMutex(void)
{
    static int dummy;
    return &dummy;
}

static inline int xSemaphoreTake(SemaphoreHandle_t sem, unsigned int ticks)
{
    (void)sem;
    (void)ticks;
    return pdTRUE;
}

static inline int xSemaphoreGive(SemaphoreHandle_t sem)
{
    (void)sem;
    return pdTRUE;
}
