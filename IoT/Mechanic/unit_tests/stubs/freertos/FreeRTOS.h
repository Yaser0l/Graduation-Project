#pragma once

#include <stdbool.h>
#include <stdint.h>

#define pdFALSE ((int32_t)0)
#define pdTRUE  ((int32_t)1)
#define pdPASS  pdTRUE
#define pdFAIL  pdFALSE
#define pdMS_TO_TICKS(ms) ((uint32_t)(ms))

#define portMUX_INITIALIZER_UNLOCKED 0
#define portMAX_DELAY 0xFFFFFFFFu

typedef int32_t BaseType_t;
typedef uint32_t portMUX_TYPE;

#define taskENTER_CRITICAL(mux)  do { (void)(mux); } while (0)
#define taskEXIT_CRITICAL(mux)   do { (void)(mux); } while (0)
