#pragma once

#include <stdbool.h>

bool wifi_manager_is_connected(void);

void wifi_stub_reset(void);
void wifi_stub_set_connected(bool connected);
