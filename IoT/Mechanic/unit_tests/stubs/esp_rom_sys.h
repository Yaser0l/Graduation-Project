#pragma once

#define IRAM_ATTR

static inline void esp_rom_printf(const char* fmt, ...) { (void)fmt; }
