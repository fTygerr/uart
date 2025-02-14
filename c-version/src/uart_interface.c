#include "uart_interface.h"
#include <stdio.h>
#include <string.h>
#include <termios.h>
#include <fcntl.h>
#include <unistd.h>

static lv_obj_t *display_label_upper;
static lv_obj_t *display_label_lower;
static lv_obj_t *buttons[8];
static int uart_fd = -1;
static int error_counter = 0;

void init_uart(void) {
    uart_fd = open("/dev/serial0", O_RDWR);
    if (uart_fd < 0) {
        printf("[ERROR] Failed to open UART\n");
        return;
    }

    struct termios options;
    tcgetattr(uart_fd, &options);
    cfsetispeed(&options, B9600);
    cfsetospeed(&options, B9600);
    options.c_cflag |= (CLOCAL | CREAD);
    options.c_cflag &= ~PARENB;
    options.c_cflag &= ~CSTOPB;
    options.c_cflag &= ~CSIZE;
    options.c_cflag |= CS8;
    tcsetattr(uart_fd, TCSANOW, &options);
}

static void button_event_cb(lv_event_t *e) {
    int key_num = (int)lv_event_get_user_data(e);
    send_key_command(key_num);
}

void create_ui(void) {
    // Create main container
    lv_obj_t *main_cont = lv_obj_create(lv_scr_act());
    lv_obj_set_size(main_cont, 480, 800);
    lv_obj_set_style_bg_color(main_cont, lv_color_hex(0x01331A), 0);

    // Create display area
    lv_obj_t *display_cont = lv_obj_create(main_cont);
    lv_obj_set_size(display_cont, 400, 100);
    lv_obj_align(display_cont, LV_ALIGN_TOP_MID, 0, 20);
    lv_obj_set_style_bg_color(display_cont, lv_color_black(), 0);
    lv_obj_set_style_border_color(display_cont, lv_color_white(), 0);
    lv_obj_set_style_border_width(display_cont, 2, 0);

    // Create display labels
    display_label_upper = lv_label_create(display_cont);
    display_label_lower = lv_label_create(display_cont);
    
    lv_obj_align(display_label_upper, LV_ALIGN_TOP_MID, 0, 10);
    lv_obj_align(display_label_lower, LV_ALIGN_BOTTOM_MID, 0, -10);
    
    // Create buttons
    for(int i = 0; i < 8; i++) {
        int row = i / 2;
        int col = i % 2;
        
        buttons[i] = lv_btn_create(main_cont);
        lv_obj_set_size(buttons[i], 180, 80);
        lv_obj_align(buttons[i], LV_ALIGN_TOP_LEFT, 
                    60 + col * 240, 
                    150 + row * 120);
        
        lv_obj_t *label = lv_label_create(buttons[i]);
        lv_label_set_text_fmt(label, "Key %d", i);
        lv_obj_center(label);
        
        lv_obj_add_event_cb(buttons[i], button_event_cb, 
                           LV_EVENT_CLICKED, (void*)(intptr_t)i);
    }
}

void send_display_command(int n) {
    if (uart_fd < 0) return;
    
    char cmd[32];
    snprintf(cmd, sizeof(cmd), "DISP %d\r", n);
    
    ssize_t bytes_written = write(uart_fd, cmd, strlen(cmd));
    if (bytes_written < 0) {
        error_counter++;
        printf("[ERROR] Failed to write to UART\n");
        if (error_counter >= MAX_ERRORS) {
            // Attempt to reinitialize UART
            close(uart_fd);
            init_uart();
            error_counter = 0;
        }
    }
}

void send_key_command(int key_number) {
    if (uart_fd < 0) return;
    
    char cmd[32];
    snprintf(cmd, sizeof(cmd), "KEY %d %s\r", key_number, KEY_PRESS_DURATION);
    
    ssize_t bytes_written = write(uart_fd, cmd, strlen(cmd));
    if (bytes_written < 0) {
        error_counter++;
        printf("[ERROR] Failed to write to UART\n");
        if (error_counter >= MAX_ERRORS) {
            close(uart_fd);
            init_uart();
            error_counter = 0;
        }
    }
}

void periodic_display_update(lv_timer_t *timer) {
    static int current_display = 0;
    
    // Read from UART
    if (uart_fd < 0) return;
    
    char buffer[256];
    ssize_t bytes_read = read(uart_fd, buffer, sizeof(buffer) - 1);
    
    if (bytes_read > 0) {
        buffer[bytes_read] = '\0';
        
        // Parse the response and update display
        char *upper_text = strtok(buffer, "\n");
        char *lower_text = strtok(NULL, "\n");
        
        if (upper_text) {
            lv_label_set_text(display_label_upper, upper_text);
        }
        if (lower_text) {
            lv_label_set_text(display_label_lower, lower_text);
        }
        
        error_counter = 0;
    } else {
        error_counter++;
        if (error_counter >= MAX_ERRORS) {
            lv_label_set_text(display_label_upper, "ERROR: No Response");
            lv_label_set_text(display_label_lower, "Check Connection");
            close(uart_fd);
            init_uart();
            error_counter = 0;
        }
    }
    
    // Request next display update
    current_display = (current_display + 1) % 2;
    send_display_command(current_display);
}

// ... More functions to be continued ...