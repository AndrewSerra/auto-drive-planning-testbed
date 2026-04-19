#include <WiFi.h>
#include <ESP32Servo.h>
#include <WebSocketsClient.h>

#define WIFI_SSID        "UPK713"
#define WIFI_PASSWORD    "favor9-fig-soft"
#define WIFI_TIMEOUT_MS  10000
#define WIFI_MAX_RETRIES 3

#define WS_HOST  "192.168.1.160"
#define WS_PORT  8765
#define CAR_ID   "car_1"

#define STEERING_PIN     18
#define ESC_PIN          19
#define ESC_NEUTRAL      90
#define ESC_FORWARD      94
#define ESC_BACKWARD     87

WebSocketsClient webSocket;

Servo steeringServo;
Servo esc;

enum CarState {
  WIFI_CONNECTING,
  WEBSOCKET_CONNECTING,
  ERROR,
  IDLE,
  OPERATING,
};

volatile CarState currentState = WIFI_CONNECTING;

void transitionTo(CarState newState) {
  Serial.print("[STATE] ");
  Serial.print(currentState);
  Serial.print(" -> ");
  Serial.println(newState);
  currentState = newState;
}

void onWiFiDisconnect(arduino_event_id_t event) {
  webSocket.disconnect();
  currentState = WIFI_CONNECTING;
}

int wifiRetries = 0;

bool connectWiFi() {
  Serial.print("[WiFi] Connecting to ");
  Serial.println(WIFI_SSID);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  unsigned long startTime = millis();
  while ((WiFi.status() != WL_CONNECTED || WiFi.localIP() == IPAddress(0, 0, 0, 0))
         && millis() - startTime < WIFI_TIMEOUT_MS) {
    delay(500);
    Serial.print(".");
  }
  Serial.println();

  if (WiFi.status() == WL_CONNECTED && WiFi.localIP() != IPAddress(0, 0, 0, 0)) {
    Serial.print("[WiFi] Connected. IP: ");
    Serial.println(WiFi.localIP());
    return true;
  }
  Serial.println("[WiFi] Attempt timed out.");
  return false;
}

void webSocketEvent(WStype_t type, uint8_t* payload, size_t length) {
  switch (type) {
    case WStype_CONNECTED:
      Serial.println("[WS] Connected. Sending registration.");
      webSocket.sendTXT("{\"id\":\"" CAR_ID "\",\"connection_type\":\"agent\"}");
      break;
    case WStype_TEXT:
      Serial.printf("[WS] Message: %s\n", payload);
      if (strstr((char*)payload, "\"is_success\"") != NULL) {
        if (strstr((char*)payload, "\"is_success\":true") != NULL) {
          transitionTo(OPERATING);
        } else {
          Serial.println("[WS] Registration rejected.");
          transitionTo(ERROR);
        }
      } else if (strstr((char*)payload, "\"forward\"") != NULL) {
        if (currentState == OPERATING) {
          handleCommand((char*)payload);
        }
      }
      break;
    case WStype_ERROR:
      Serial.println("[WS] Error.");
      transitionTo(ERROR);
      break;
    case WStype_DISCONNECTED:
      Serial.println("[WS] Disconnected.");
      if (currentState != WEBSOCKET_CONNECTING) {
        transitionTo(IDLE);
      }
      break;
    default:
      break;
  }
}

void steer(float steering) {
  // Map [-1.0, 1.0] → [0, 180] degrees; 0.0 = center (90°)
  int angle = constrain((int)(90.0f + steering * 90.0f), 0, 180);
  steeringServo.write(angle);
}

void handleCommand(const char* payload) {
  if (strstr(payload, CAR_ID) == NULL) return;

  bool forward = strstr(payload, "\"forward\":true") != NULL;

  float steering = 0.0f;
  const char* ptr = strstr(payload, "\"steering\":");
  if (ptr != NULL) {
    sscanf(ptr + 11, "%f", &steering);
  }

  steer(steering);

  if (forward) {
    driveForward();
  } else {
    driveStop();
    steeringServo.write(90);  // recenter on stop
  }

  Serial.printf("[CMD] forward=%s steering=%.2f\n", forward ? "true" : "false", steering);
}

void driveForward() {
  Serial.println("[ESC] Forward");
  esc.write(ESC_FORWARD);
}

void driveBackward() {
  Serial.println("[ESC] Backward");
  esc.write(ESC_BACKWARD);
}

void driveStop() {
  Serial.println("[ESC] Stop");
  esc.write(ESC_NEUTRAL);
}

void setup() {
  Serial.begin(115200);
  Serial.println("[Boot] Car system starting.");
  WiFi.onEvent(onWiFiDisconnect, ARDUINO_EVENT_WIFI_STA_DISCONNECTED);
  webSocket.onEvent(webSocketEvent);

  steeringServo.attach(STEERING_PIN);
  esc.attach(ESC_PIN);
  driveStop();  // arm ESC with neutral signal
  delay(2000);
}

volatile CarState prevState = (CarState)-1;

void loop() {
  CarState thisIterState = currentState;
  switch (currentState) {
    case WIFI_CONNECTING:
      if (prevState != currentState) {
        wifiRetries = 0;
      }
      if (connectWiFi()) {
        transitionTo(WEBSOCKET_CONNECTING);
      } else {
        wifiRetries++;
        Serial.print("[WiFi] Attempt ");
        Serial.print(wifiRetries);
        Serial.print("/");
        Serial.println(WIFI_MAX_RETRIES);
        if (wifiRetries >= WIFI_MAX_RETRIES) {
          Serial.println("[WiFi] Max retries reached.");
          transitionTo(ERROR);
        }
      }
      break;
    case WEBSOCKET_CONNECTING:
      if (prevState != currentState) {
        Serial.println("[WS] Connecting...");
        webSocket.begin(WS_HOST, WS_PORT, "/");
      }
      webSocket.loop();
      break;
    case ERROR:
      if (prevState != currentState) {
        // one-time on-entry code here
      }
      delay(10);
      break;
    case IDLE:
      if (prevState != currentState) {
        // one-time on-entry code here
      }
      webSocket.loop();
      delay(10);
      break;
    case OPERATING:
      if (prevState != currentState) {
        // one-time on-entry code here
      }
      webSocket.loop();
      break;
  }
  prevState = thisIterState;
}
