#pragma once

#include <stdarg.h>
#include <stdio.h>

#define ESP_LOG_INFO 3
#define ESP_LOG_WARN 2
#define ESP_LOG_ERROR 1
#define ESP_LOG_DEBUG 4

#define ESP_LOGI(tag, fmt, ...)  ((void)(tag), (void)(fmt))
#define ESP_LOGW(tag, fmt, ...)  ((void)(tag), (void)(fmt))
#define ESP_LOGE(tag, fmt, ...)  ((void)(tag), (void)(fmt))
#define ESP_LOGD(tag, fmt, ...)  ((void)(tag), (void)(fmt))

static inline const char* esp_err_to_name(int err) { (void)err; return "ERR"; }

static inline void esp_log_writev(int level, const char* tag, const char* fmt, va_list args) {
    (void)level; (void)tag; (void)fmt; (void)args;
}
