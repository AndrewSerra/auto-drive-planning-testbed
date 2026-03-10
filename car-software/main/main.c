#include <stdio.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "driver/gpio.h"
#include "driver/gptimer.h"
#include "esp_log.h"
#include "esp_wifi.h"
#include "nvs_flash.h"
#include "esp_netif.h"
#include "esp_event.h"
#include "freertos/event_groups.h"

#define GREEN_LED_PIN GPIO_NUM_23
#define RED_LED_PIN   GPIO_NUM_22

#define WIFI_SSID    "Andrew Iphone" // "UPK713"
#define WIFI_PASSWD  "andrewserra"   // "favor9-fig-soft"

static const char* TAG = "Agent";

typedef enum {
    CONNECTING_WIFI,
    SETUP_COMPLETE,
    REGISTERING_SERVER,
    IDLE,
    RUNNING,
    STOPPED,
    ERROR,
    WIFI_RECONNECTING,
} state_t;

static const char* state_strs[] = {
    [CONNECTING_WIFI] = "CONNECTING_WIFI",
    [SETUP_COMPLETE]  = "SETUP_COMPLETE",
    [REGISTERING_SERVER] = "REGISTERING_SERVER",
    [IDLE] = "IDLE",
    [RUNNING] = "RUNNING",
    [STOPPED] = "STOPPED",
    [ERROR] = "ERROR",
    [WIFI_RECONNECTING] = "WIFI_RECONNECTING",
};

// ISR reads this — must be volatile and file-scope
static volatile state_t current_state_ = CONNECTING_WIFI;

static gptimer_handle_t gptimer_ = NULL;

bool green_led_level_ = 0, red_led_level_ = 0;

// Blink config table: 0=off, -1=solid on, N=toggle every N*100ms ticks
typedef struct {
    int green_ticks;
    int red_ticks;
} blink_cfg_t;

static const blink_cfg_t blink_table[] = {
    [CONNECTING_WIFI]    = {  5,  0 }, // green 2 Hz,  red off
    [SETUP_COMPLETE]     = { -1,  0 }, // green solid, red off
    [REGISTERING_SERVER] = {  2,  0 }, // green 5 Hz,  red off
    [IDLE]               = { 10,  0 }, // green 1 Hz,  red off
    [RUNNING]            = { -1,  0 }, // green solid, red off
    [STOPPED]            = {  0, 10 }, // green off,   red 1 Hz
    [ERROR]              = {  0, -1 }, // green off, solid red
    [WIFI_RECONNECTING]  = {  5, -1 }, // green 0.5 Hz, solid red
};

#define WIFI_MAX_RETRIES 3

typedef struct {
    bool connected;
    int retry_count;
} wifi_state_t;

static wifi_state_t wifi_state_ = { .connected = false, .retry_count = 0 };
static EventGroupHandle_t wifi_event_group_;
#define WIFI_CONNECTED_BIT BIT0
#define WIFI_FAIL_BIT      BIT1

static void wifi_event_handler(void *arg, esp_event_base_t base,
                               int32_t event_id, void *event_data) {
    if (base == WIFI_EVENT && event_id == WIFI_EVENT_STA_START) {
        esp_wifi_connect();
    } else if (base == WIFI_EVENT && event_id == WIFI_EVENT_STA_DISCONNECTED) {
        wifi_state_.connected = false;
        wifi_event_sta_disconnected_t *event = (wifi_event_sta_disconnected_t *) event_data;
        ESP_LOGE(TAG, "Disconnect reason: %d", event->reason);
        ESP_LOGI(TAG, "WiFi disconnected. Attempting to reconnect... Retry count: %d", wifi_state_.retry_count);
        if (wifi_state_.retry_count < WIFI_MAX_RETRIES) {
            wifi_state_.retry_count++;
            esp_wifi_connect();
        } else {
            xEventGroupSetBits(wifi_event_group_, WIFI_FAIL_BIT);
        }
    } else if (base == IP_EVENT && event_id == IP_EVENT_STA_GOT_IP) {
        wifi_state_.connected = true;
        wifi_state_.retry_count = 0;
        xEventGroupSetBits(wifi_event_group_, WIFI_CONNECTED_BIT);
    }
}

static bool IRAM_ATTR timer_isr_handler(gptimer_handle_t timer,
                                        const gptimer_alarm_event_data_t *edata,
                                        void *user_ctx) {
    static int tick = 0;
    tick++;

    const blink_cfg_t *cfg = &blink_table[current_state_];

    // Green LED
    if (cfg->green_ticks == -1) {
        gpio_set_level(GREEN_LED_PIN, 1);
    } else if (cfg->green_ticks == 0) {
        gpio_set_level(GREEN_LED_PIN, 0);
    } else if (tick % cfg->green_ticks == 0) {
        green_led_level_ ^= 1;
        gpio_set_level(GREEN_LED_PIN, green_led_level_);
    }

    // Red LED
    if (cfg->red_ticks == -1) {
        gpio_set_level(RED_LED_PIN, 1);
    } else if (cfg->red_ticks == 0) {
        gpio_set_level(RED_LED_PIN, 0);
    } else if (tick % cfg->red_ticks == 0) {
        red_led_level_ ^= 1;
        gpio_set_level(RED_LED_PIN, red_led_level_);
    }

    return false; // no high-priority task woken
}


void print_new_state_msg(state_t state) {
    ESP_LOGI(TAG, "Entering new state: %s", state_strs[state]);
}

void setup_gpio(void) {
    // Configure LED pins
    gpio_reset_pin(GREEN_LED_PIN);
    gpio_reset_pin(RED_LED_PIN);

    // Set gpio pins as outputs
    gpio_set_direction(GREEN_LED_PIN, GPIO_MODE_OUTPUT);
    gpio_set_direction(RED_LED_PIN, GPIO_MODE_OUTPUT);

    // Clear pins to start LEDs as OFF
    gpio_set_level(GREEN_LED_PIN, 0);
    gpio_set_level(RED_LED_PIN, 0);
}

void setup_timers(void) {
    ESP_LOGI(TAG, "Setting up the timer.");
    gptimer_config_t timer_config = {
        .clk_src = GPTIMER_CLK_SRC_DEFAULT,
        .direction = GPTIMER_COUNT_UP,
        .resolution_hz = 1000000, // 1 MHz → 1 count = 1 µs
    };
    ESP_ERROR_CHECK(gptimer_new_timer(&timer_config, &gptimer_));

    gptimer_event_callbacks_t cbs = { .on_alarm = timer_isr_handler };
    ESP_ERROR_CHECK(gptimer_register_event_callbacks(gptimer_, &cbs, NULL));

    gptimer_alarm_config_t alarm_config = {
        .alarm_count = 100000,            // 100ms per tick
        .reload_count = 0,
        .flags.auto_reload_on_alarm = true,
    };
    ESP_ERROR_CHECK(gptimer_set_alarm_action(gptimer_, &alarm_config));

    ESP_LOGI(TAG, "Enable and start timer");
    ESP_ERROR_CHECK(gptimer_enable(gptimer_));
    ESP_ERROR_CHECK(gptimer_start(gptimer_));
}

bool connect_wifi(void) {
    wifi_state_.retry_count = 0;
    wifi_event_group_ = xEventGroupCreate();

    nvs_flash_init();
    esp_netif_init();
    esp_event_loop_create_default();
    esp_netif_create_default_wifi_sta();

    wifi_init_config_t cfg = WIFI_INIT_CONFIG_DEFAULT();
    esp_wifi_init(&cfg);

    esp_event_handler_register(WIFI_EVENT, ESP_EVENT_ANY_ID, &wifi_event_handler, NULL);
    esp_event_handler_register(IP_EVENT, IP_EVENT_STA_GOT_IP, &wifi_event_handler, NULL);

    wifi_config_t wifi_config = {
        .sta = {
            .ssid = WIFI_SSID,
            .password = WIFI_PASSWD,
        },
    };
    esp_wifi_set_mode(WIFI_MODE_STA);
    esp_wifi_set_config(WIFI_IF_STA, &wifi_config);
    esp_wifi_start();

    // Block until connected or max retries hit
    EventBits_t bits = xEventGroupWaitBits(wifi_event_group_,
        WIFI_CONNECTED_BIT | WIFI_FAIL_BIT, pdFALSE, pdFALSE, portMAX_DELAY);

    if (bits & WIFI_CONNECTED_BIT) {
        ESP_LOGI(TAG, "Connected to WiFi.");
        return true;
    }
    ESP_LOGE(TAG, "Failed to connect to WiFi after %d attempts.", WIFI_MAX_RETRIES);
    return false;
}

void app_main(void) {
    state_t prev_state = IDLE;
    ESP_LOGI(TAG, "Starting up program...");

    ESP_LOGD(TAG, "Setting up GPIO pins");
    setup_gpio();
    ESP_LOGD(TAG, "Setting up Hardware Timers");
    setup_timers();


    while (true) {
        if(prev_state != current_state_) {
            print_new_state_msg(current_state_);
            prev_state = current_state_;
        }

        switch (current_state_)
        {
        case CONNECTING_WIFI:
            if (connect_wifi()) {
                current_state_ = SETUP_COMPLETE;
            } else {
                current_state_ = ERROR;
            }
            break;
        case IDLE:
            break;
        case ERROR:
            break;
        case WIFI_RECONNECTING:
            wifi_state_.retry_count = 0;
            if (connect_wifi()) {
                current_state_ = IDLE;
            } else {
                current_state_ = ERROR;
            }
            break;
        default:
            break;
        }

        // LEDs are driven by the timer ISR; main loop just idles
        vTaskDelay(pdMS_TO_TICKS(1000));
    }
}
