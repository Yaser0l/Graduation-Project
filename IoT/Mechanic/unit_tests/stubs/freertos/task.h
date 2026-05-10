#pragma once

#include "FreeRTOS.h"

typedef void *TaskHandle_t;

typedef void (*TaskFunction_t)(void *);

#define pdPASS 1
#define pdMS_TO_TICKS(x) (x)

static inline void vTaskDelay(unsigned int ticks)
{
    (void)ticks;
}

static inline BaseType_t xTaskCreate(TaskFunction_t task_code,
                                    const char *name,
                                    unsigned int stack_depth,
                                    void *params,
                                    unsigned int priority,
                                    TaskHandle_t *task_handle)
{
    (void)task_code;
    (void)name;
    (void)stack_depth;
    (void)params;
    (void)priority;
    (void)task_handle;
    return pdPASS;
}
