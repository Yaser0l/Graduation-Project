#include "freertos/event_groups.h"

static EventBits_t s_bits = 0;
static EventBits_t s_wait_bits = 0;
static int s_dummy_group = 0;

void event_group_stub_reset(void)
{
    s_bits = 0;
    s_wait_bits = 0;
}

void event_group_stub_set_bits(EventBits_t bits)
{
    s_bits = bits;
}

void event_group_stub_set_wait_bits(EventBits_t bits)
{
    s_wait_bits = bits;
}

EventBits_t event_group_stub_get_bits(void)
{
    return s_bits;
}

EventGroupHandle_t xEventGroupCreate(void)
{
    return &s_dummy_group;
}

EventBits_t xEventGroupGetBits(EventGroupHandle_t event_group)
{
    (void)event_group;
    return s_bits;
}

EventBits_t xEventGroupSetBits(EventGroupHandle_t event_group, EventBits_t bits_to_set)
{
    (void)event_group;
    s_bits |= bits_to_set;
    return s_bits;
}

EventBits_t xEventGroupClearBits(EventGroupHandle_t event_group, EventBits_t bits_to_clear)
{
    (void)event_group;
    s_bits &= ~bits_to_clear;
    return s_bits;
}

EventBits_t xEventGroupWaitBits(EventGroupHandle_t event_group,
                                EventBits_t bits_to_wait_for,
                                int clear_on_exit,
                                int wait_for_all_bits,
                                unsigned int ticks_to_wait)
{
    (void)event_group;
    (void)bits_to_wait_for;
    (void)clear_on_exit;
    (void)wait_for_all_bits;
    (void)ticks_to_wait;
    return s_wait_bits;
}
