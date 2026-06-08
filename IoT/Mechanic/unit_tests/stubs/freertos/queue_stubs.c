#include "freertos/FreeRTOS.h"
#include "freertos/queue.h"

QueueHandle_t xQueueCreate(uint32_t queue_length, uint32_t item_size) {
    (void)queue_length; (void)item_size;
    return (QueueHandle_t)0x2000;
}

int32_t xQueueSendFromISR(QueueHandle_t queue, const void* item,
                           int32_t* higher_prio_woken) {
    (void)queue; (void)item;
    if (higher_prio_woken) *higher_prio_woken = pdFALSE;
    return pdTRUE;
}

int32_t xQueueReceive(QueueHandle_t queue, void* buffer, uint32_t ticks_to_wait) {
    (void)queue; (void)buffer; (void)ticks_to_wait;
    return pdFAIL;
}
