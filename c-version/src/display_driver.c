#include "lvgl.h"
#include <SDL2/SDL.h>
#include <stdbool.h>

#define DISP_HOR_RES 480
#define DISP_VER_RES 800
#define BUFFER_SIZE (DISP_HOR_RES * DISP_VER_RES)

static SDL_Window *window;
static SDL_Renderer *renderer;
static SDL_Texture *texture;
static uint32_t *pixel_buffer;

static void flush_cb(lv_disp_drv_t *disp_drv, const lv_area_t *area, lv_color_t *color_p);
static void sdl_event_handler(lv_timer_t *t);
static void mouse_read_cb(lv_indev_drv_t *indev_drv, lv_indev_data_t *data);

bool init_display_driver(lv_disp_drv_t *disp_drv) {
    // Initialize SDL
    if (SDL_Init(SDL_INIT_VIDEO) != 0) {
        printf("SDL initialization failed: %s\n", SDL_GetError());
        return false;
    }

    window = SDL_CreateWindow("UART Interface",
                            SDL_WINDOWPOS_UNDEFINED, SDL_WINDOWPOS_UNDEFINED,
                            DISP_HOR_RES, DISP_VER_RES, 0);
    if (!window) {
        printf("Window creation failed: %s\n", SDL_GetError());
        return false;
    }

    renderer = SDL_CreateRenderer(window, -1, SDL_RENDERER_ACCELERATED);
    if (!renderer) {
        printf("Renderer creation failed: %s\n", SDL_GetError());
        return false;
    }

    texture = SDL_CreateTexture(renderer,
                              SDL_PIXELFORMAT_ARGB8888,
                              SDL_TEXTUREACCESS_STATIC,
                              DISP_HOR_RES, DISP_VER_RES);
    if (!texture) {
        printf("Texture creation failed: %s\n", SDL_GetError());
        return false;
    }

    // Allocate buffer for drawing
    pixel_buffer = malloc(BUFFER_SIZE * sizeof(uint32_t));
    if (!pixel_buffer) {
        printf("Failed to allocate pixel buffer\n");
        return false;
    }

    // Initialize display driver
    static lv_disp_draw_buf_t draw_buf;
    static lv_color_t buf1[BUFFER_SIZE];
    static lv_color_t buf2[BUFFER_SIZE];
    
    lv_disp_draw_buf_init(&draw_buf, buf1, buf2, BUFFER_SIZE);
    lv_disp_drv_init(disp_drv);
    
    disp_drv->draw_buf = &draw_buf;
    disp_drv->flush_cb = flush_cb;
    disp_drv->hor_res = DISP_HOR_RES;
    disp_drv->ver_res = DISP_VER_RES;
    
    if (!lv_disp_drv_register(disp_drv)) {
        printf("Display driver registration failed\n");
        return false;
    }

    // Create SDL event handler timer
    lv_timer_create(sdl_event_handler, 10, NULL);

    return true;
}

bool init_input_driver(lv_indev_drv_t *indev_drv) {
    lv_indev_drv_init(indev_drv);
    
    indev_drv->type = LV_INDEV_TYPE_POINTER;
    indev_drv->read_cb = mouse_read_cb;
    
    if (!lv_indev_drv_register(indev_drv)) {
        printf("Input driver registration failed\n");
        return false;
    }
    
    return true;
}

static void flush_cb(lv_disp_drv_t *disp_drv, const lv_area_t *area, lv_color_t *color_p) {
    for (int y = area->y1; y <= area->y2; y++) {
        for (int x = area->x1; x <= area->x2; x++) {
            pixel_buffer[y * DISP_HOR_RES + x] = lv_color_to32(*color_p);
            color_p++;
        }
    }

    SDL_UpdateTexture(texture, NULL, pixel_buffer, DISP_HOR_RES * sizeof(uint32_t));
    SDL_RenderClear(renderer);
    SDL_RenderCopy(renderer, texture, NULL, NULL);
    SDL_RenderPresent(renderer);

    lv_disp_flush_ready(disp_drv);
}

static void sdl_event_handler(lv_timer_t *t) {
    SDL_Event event;
    while (SDL_PollEvent(&event)) {
        switch (event.type) {
            case SDL_QUIT:
                exit(0);
                break;
            default:
                break;
        }
    }
}

static void mouse_read_cb(lv_indev_drv_t *indev_drv, lv_indev_data_t *data) {
    int x, y;
    uint32_t buttons = SDL_GetMouseState(&x, &y);
    
    data->point.x = x;
    data->point.y = y;
    data->state = (buttons & SDL_BUTTON_LEFT) ? LV_INDEV_STATE_PRESSED : LV_INDEV_STATE_RELEASED;
}

void cleanup_display_driver(void) {
    free(pixel_buffer);
    SDL_DestroyTexture(texture);
    SDL_DestroyRenderer(renderer);
    SDL_DestroyWindow(window);
    SDL_Quit();
}