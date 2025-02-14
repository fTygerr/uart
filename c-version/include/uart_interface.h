#ifndef UART_INTERFACE_H
#define UART_INTERFACE_H

#include "lvgl.h"

// Constants
#define KEY_PRESS_DURATION "1000"
#define DISPLAY_UPDATE_INTERVAL 750  // milliseconds
#define MAX_ERRORS 3

// Function declarations
void create_ui(void);
void init_uart(void);
void send_display_command(int n);
void send_key_command(int key_number);
void periodic_display_update(lv_timer_t *timer);

#endif // UART_INTERFACE_H