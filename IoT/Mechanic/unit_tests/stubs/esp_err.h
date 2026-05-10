#ifndef ESP_ERR_H
#define ESP_ERR_H

#include <stdint.h>

typedef int32_t esp_err_t;

#define ESP_OK 0
#define ESP_FAIL (-1)
#define ESP_ERR_INVALID_ARG (-2)
#define ESP_ERR_INVALID_STATE (-3)
#define ESP_ERR_NOT_FINISHED (-4)
#define ESP_ERR_INVALID_SIZE (-5)
#define ESP_ERR_NO_MEM (-6)
#define ESP_ERR_NVS_NOT_FOUND (-7)

static inline const char *esp_err_to_name(esp_err_t err)
{
    (void)err;
    return "stub";
}

#define ESP_ERROR_CHECK(x)          \
    do                              \
    {                               \
        esp_err_t __err = (x);      \
        (void)__err;                \
    } while (0)

#endif
