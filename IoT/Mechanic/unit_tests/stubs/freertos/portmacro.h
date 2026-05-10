#ifndef PORTMACRO_H
#define PORTMACRO_H

typedef int portMUX_TYPE;

#define portMUX_INITIALIZER_UNLOCKED 0

#define taskENTER_CRITICAL_ISR(mux) (void)(mux)
#define taskEXIT_CRITICAL_ISR(mux) (void)(mux)
#define taskENTER_CRITICAL(mux) (void)(mux)
#define taskEXIT_CRITICAL(mux) (void)(mux)

#endif
