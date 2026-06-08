#include "freertos/FreeRTOS.h"
#include "freertos/semphr.h"

SemaphoreHandle_t xSemaphoreCreateMutex(void) {
    return (SemaphoreHandle_t)0x3000;
}

int32_t xSemaphoreTake(SemaphoreHandle_t sem, uint32_t ticks_to_wait) {
    (void)sem; (void)ticks_to_wait;
    return pdTRUE;
}

int32_t xSemaphoreGive(SemaphoreHandle_t sem) {
    (void)sem;
    return pdTRUE;
}
