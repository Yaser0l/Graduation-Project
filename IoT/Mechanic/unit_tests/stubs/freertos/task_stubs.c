#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

int32_t xTaskCreate(void (*task)(void*), const char* name, uint32_t stack_depth,
                    void* parameters, uint32_t priority, void* created_task) {
    (void)task; (void)name; (void)stack_depth;
    (void)parameters; (void)priority;
    if (created_task) *(void**)created_task = (void*)0x1000;
    return pdPASS;
}

void vTaskDelay(uint32_t ticks) {
    (void)ticks;
}
