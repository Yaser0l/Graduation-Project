#pragma once

#include "FreeRTOS.h"
#include <stdint.h>

int32_t xTaskCreate(void (*task)(void*), const char* name, uint32_t stack_depth,
                    void* parameters, uint32_t priority, void* created_task);

void vTaskDelay(uint32_t ticks);
