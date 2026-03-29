#include <WiFi.h>
#include <ESP32Servo.h>

#define WIFI_SSID        "UPK713"
#define WIFI_PASSWORD    "favor9-fig-soft"
#define WIFI_TIMEOUT_MS  10000
#define WIFI_MAX_RETRIES 3

#define STEERING_PIN     18
#define ESC_PIN          19
#define ESC_NEUTRAL      90
#define ESC_FORWARD      94
#define ESC_BACKWARD     87

Servo steeringServo;
Servo esc;

int servoPosition = 0;

enum CarState {
  WIFI_CONNECTING,
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

void steerCenter() {
  steeringServo.write(90);
  delay(500);
}

void steerLeft() {
  for (servoPosition = 90; servoPosition >= 0; servoPosition -= 1) {
    steeringServo.write(servoPosition);
    delay(15);
  }
}

void steerRight() {
  for (servoPosition = 90; servoPosition <= 180; servoPosition += 1) {
    steeringServo.write(servoPosition);
    delay(15);
  }
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

  steeringServo.attach(STEERING_PIN);
  esc.attach(ESC_PIN);
  driveStop();  // arm ESC with neutral signal
  delay(2000);
}

volatile CarState prevState = (CarState)-1;

void loop() {
  switch (currentState) {
    case WIFI_CONNECTING:
      if (prevState != currentState) {
        wifiRetries = 0;
      }
      if (connectWiFi()) {
        transitionTo(OPERATING);
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
      delay(10);
      break;
    case OPERATING:
      if (prevState != currentState) {
        // one-time on-entry code here
      }
      driveForward();
      delay(1500);
      driveStop();
      delay(100);
      driveBackward();
      delay(1500);
      driveStop();
      transitionTo(IDLE);
      break;
  }
  prevState = currentState;
}
