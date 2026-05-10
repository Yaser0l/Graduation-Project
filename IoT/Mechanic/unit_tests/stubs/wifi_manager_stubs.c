#include "wifi_manager.h"

static bool s_connected = false;

void wifi_stub_reset(void)
{
    s_connected = false;
}

void wifi_stub_set_connected(bool connected)
{
    s_connected = connected;
}

bool wifi_manager_is_connected(void)
{
    return s_connected;
}
