#pragma once

#include <stdint.h>

typedef void *EventGroupHandle_t;
typedef uint32_t EventBits_t;

#define BIT0 (1U << 0)

EventGroupHandle_t xEventGroupCreate(void);
EventBits_t xEventGroupGetBits(EventGroupHandle_t event_group);
EventBits_t xEventGroupSetBits(EventGroupHandle_t event_group, EventBits_t bits_to_set);
EventBits_t xEventGroupClearBits(EventGroupHandle_t event_group, EventBits_t bits_to_clear);
EventBits_t xEventGroupWaitBits(EventGroupHandle_t event_group,
                                EventBits_t bits_to_wait_for,
                                int clear_on_exit,
                                int wait_for_all_bits,
                                unsigned int ticks_to_wait);

void event_group_stub_reset(void);
void event_group_stub_set_bits(EventBits_t bits);
void event_group_stub_set_wait_bits(EventBits_t bits);
EventBits_t event_group_stub_get_bits(void);
