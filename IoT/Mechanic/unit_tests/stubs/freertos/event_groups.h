#pragma once

#include <stdint.h>

typedef void* EventGroupHandle_t;
typedef uint32_t EventBits_t;

#define BIT0 (1u << 0)

EventGroupHandle_t xEventGroupCreate(void);
EventBits_t xEventGroupGetBits(EventGroupHandle_t group);
EventBits_t xEventGroupSetBits(EventGroupHandle_t group, EventBits_t bits);
EventBits_t xEventGroupClearBits(EventGroupHandle_t group, EventBits_t bits);
EventBits_t xEventGroupWaitBits(EventGroupHandle_t group, EventBits_t bits,
                                 int32_t clear_on_exit, int32_t wait_for_all_bits,
                                 uint32_t ticks_to_wait);
