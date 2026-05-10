#ifndef ESP_ERR_H
#define ESP_ERR_H

#include <stdint.h>

typedef int32_t esp_err_t;

#define ESP_OK 0
#define ESP_FAIL (-1)
#define ESP_ERR_INVALID_ARG (-2)

static inline const char *esp_err_to_name(esp_err_t err)
{
    (void)err;
    return "stub";
}

#endif
