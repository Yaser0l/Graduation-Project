#include "event_groups_stubs.h"

static EventGroupHandle_t s_group = (EventGroupHandle_t)0x1;
static EventBits_t s_bits = 0;
static EventBits_t s_wait_return_bits = 0;
static int s_wait_calls = 0;

void event_group_stub_reset(void) {
    s_group = (EventGroupHandle_t)0x1;
    s_bits = 0;
    s_wait_return_bits = 0;
    s_wait_calls = 0;
}

void event_group_stub_set_bits(EventBits_t bits) { s_bits = bits; }
void event_group_stub_set_wait_bits(EventBits_t bits) { s_wait_return_bits = bits; }
EventBits_t event_group_stub_get_bits(void) { return s_bits; }
int event_group_stub_get_wait_calls(void) { return s_wait_calls; }

EventGroupHandle_t xEventGroupCreate(void) { return s_group; }

EventBits_t xEventGroupGetBits(EventGroupHandle_t group) {
    (void)group;
    return s_bits;
}

EventBits_t xEventGroupSetBits(EventGroupHandle_t group, EventBits_t bits) {
    (void)group;
    s_bits |= bits;
    return s_bits;
}

EventBits_t xEventGroupClearBits(EventGroupHandle_t group, EventBits_t bits) {
    (void)group;
    s_bits &= ~bits;
    return s_bits;
}

EventBits_t xEventGroupWaitBits(EventGroupHandle_t group, EventBits_t bits,
                                 int32_t clear_on_exit, int32_t wait_for_all_bits,
                                 uint32_t ticks_to_wait) {
    (void)group; (void)bits; (void)clear_on_exit; (void)wait_for_all_bits; (void)ticks_to_wait;
    s_wait_calls++;
    return s_wait_return_bits;
}
