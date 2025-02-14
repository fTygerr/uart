#include "lvgl.h"
#include "uart_interface.h"
#include <stdio.h>

static lv_disp_drv_t disp_drv;
static lv_indev_drv_t indev_drv;

int main(void) {
    // Initialize LVGL
    lv_init();
    
    // Initialize display and input device drivers
    // Note: You'll need to implement these based on your hardware
    init_display_driver(&disp_drv);
    init_input_driver(&indev_drv);
    
    // Initialize UART
    init_uart();
    
    // Create the UI
    create_ui();
    
    // Create a periodic timer for display updates
    lv_timer_create(periodic_display_update, DISPLAY_UPDATE_INTERVAL, NULL);
    
    // Main loop
    while(1) {
        lv_timer_handler();
        usleep(5000);    // 5 ms delay
    }
    
    return 0;
}