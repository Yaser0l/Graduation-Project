#pragma once

#include <stdint.h>

#include "freertos/event_groups.h"

void event_group_stub_reset(void);
void event_group_stub_set_bits(EventBits_t bits);
void event_group_stub_set_wait_bits(EventBits_t bits);
EventBits_t event_group_stub_get_bits(void);
int event_group_stub_get_wait_calls(void);
