#include <WiFi.h>
#include <PubSubClient.h>
#include "soc/soc.h"           
#include "soc/rtc_cntl_reg.h"  

//I FOUND IT LOOKS CUTE TO COMMENT IN CAPITALS:) BY EJ

// ==========================================
// 1. SETTING OF WI-FI AND MQTT
// ==========================================
//const char* ssid        = "xxxxx";      //EJ'S HOME #SHOULD BE REMOVE WHEN SUBMIT THE CODE!!!!!
//const char* password    = "12345678";
const char* ssid = "ooooo";      //EJ'S PHONE
const char* password = "87654321";
//const char* mqtt_server = "192.xxx.x.xxx";       // EJ'S HOME
const char* mqtt_server = "xx.xx.xxx.xxx";    //EJ'S PHONE
const int   mqtt_port   = 1883;                

// MQTT TOPIC
const char* mqtt_client_id = "ESP32_Patrol_Car";
const char* topic_mode       = "patrol/car/mode";  //CC->ARDUINO: MOVING MODE OF ESP32 CAR (AUTO PATROL, MANUAL, FOLLOW) *SUB
const char* topic_manual_cmd = "patrol/car/manual_cmd";  //CC->ARDUINO: MANUAL MODE'S COMMANDS (RECEIVE SPEED, TURN) *SUB
const char* topic_follow_cmd = "patrol/car/follow_cmd";  //PYTHON->ARDUINO: RECEIVE DIRECTION OF MOVEMENTS IN FOLLOW MODE *SUB
//const char* topic_alert      = "patrol/car/alert";  //PYTHON->CC: IMAGE DETECT PERSON WHO LYING DOWN
//const char* topic_drone_cmd      = "patrol/drone/cmd"; //CC->PYTHON: DISPATCH DRONE (IF SOMEONE LYING DOWN. AFTER PYTHON PUBLISH AN ALERT->CC SHOULD PUBLISH DISPATCH MESSAGE AND COORDINATES ON-SITE)
//const char* topic_temi_cmd      = "patrol/TEMI/cmd"; //CC->PYTHON: SAME AS ABOVE
//const char* topic_coordinate = "patrol/car/coordinate"; //PYTHON->CC: RANDOMLY SEND FAKE COORDINATE AS SIMULATION TEMPORAILY

// ==========================================
// 2. PIN DEFINE
// ==========================================
// --- RIGHT WHEEL ---
const byte RIGHT1    = 32;  // IN1
const byte RIGHT2    = 33;  // IN2
const byte RIGHT_PWM = 27;  // ENA (SPEED)

// --- LEFT WHEEL ---
const byte LEFT1     = 25;  // IN3
const byte LEFT2     = 26;  // IN4
const byte LEFT_PWM  = 14;  // ENB (SPEED)

// ==========================================
// 3. PARAMETERS
// ==========================================
// PWM SETTING
const int freq = 30000;
const int resolution = 8;
const int rightChannel = 0;
const int leftChannel = 1;

// FINITE STATE MACHINE
#define MODE_MANUAL 0
#define MODE_PATROL 1
#define MODE_FOLLOW 2
int currentMode = MODE_MANUAL; // DEFAULT: MANUAL

// PATROL LOGIC DEFINE
unsigned long patrolTimer = 0;
unsigned long actionDuration = 0;
int patrolState = 0; 
#define P_STOP 0
#define P_MOVE 1
#define P_TURN 2

// OBJECT ANNOUNCE
WiFiClient espClient;
PubSubClient client(espClient);

// ==========================================================
// MOTORS DRIVEN CORE FUNCTION
// ==========================================================
void driveMotor(int l, int r) {
  // --- RIGHT WHEEL ---
  if (r > 0) {
    digitalWrite(RIGHT1, LOW); digitalWrite(RIGHT2, HIGH);
    ledcWrite(rightChannel, r);
  } else {
    digitalWrite(RIGHT1, HIGH); digitalWrite(RIGHT2, LOW);
    ledcWrite(rightChannel, abs(r)); // IT MIGHT BE MINUS IN MANUAL MODE FROM NODE-RED
  }

  // --- LEFT WHEEL ---
  if (l > 0) {
    digitalWrite(LEFT1, HIGH); digitalWrite(LEFT2, LOW);
    ledcWrite(leftChannel, l);
  } else {
    digitalWrite(LEFT1, LOW); digitalWrite(LEFT2, HIGH);
    ledcWrite(leftChannel, abs(l)); // IT MIGHT BE MINUS IN MANUAL MODE FROM NODE-RED
  }
}

void stopMotor() {
  digitalWrite(RIGHT1, LOW); digitalWrite(RIGHT2, LOW);
  digitalWrite(LEFT1, LOW); digitalWrite(LEFT2, LOW);
  ledcWrite(rightChannel, 0);
  ledcWrite(leftChannel, 0);
}

// BASIC MOVEMENT
void forward() { driveMotor(190, 190); }     
void backward() { driveMotor(-190, -190); }
void turnLeft() { driveMotor(-180, 180); }   
void turnRight() { driveMotor(180, -180); } 

// ==========================================================
// AUTO PATROL
// ==========================================================
void patrolLogic() {
  unsigned long currentMillis = millis();

  // TO CHECK IS THE TIME UP FOR THE MOVEMENT?
  if (currentMillis - patrolTimer > actionDuration) {
    patrolTimer = currentMillis; // RESET

    switch (patrolState) {
      
      case P_STOP:
        // AFTER BREAK IT SHOULD DECIDE WHAT'S NEXT STEP (ONIY SET A SHORT MOVEMENT AS EXPERIMENT)
        // 60% FORWARD; 40% TURN
        if (random(0, 10) < 6) { 
          Serial.println("[Auto] Moving Forward");
          forward();
          patrolState = P_MOVE;
          // MOVE 1s TO 2.5s
          actionDuration = random(1000, 2500); 
        } else { 
          Serial.println("[Auto] Turning");
          if (random(0, 2) == 0) turnLeft(); else turnRight();
          patrolState = P_TURN;
          actionDuration = random(600, 1200); 
        }
        break;

      case P_MOVE:
      case P_TURN:
        // AFTER EVERY MOVEMENT SHOULD TAKE A BREAK:)
        Serial.println("[Auto] Pausing");
        stopMotor();
        patrolState = P_STOP;
        actionDuration = 1000; // TAKE A REST FOR 1s
        break;
    }
  }
}

// ==========================================================
// MQTT RECEIVE MESSAGES
// ==========================================================
void callback(char* topic, byte* payload, unsigned int length) {
  String msg = "";
  for (int i = 0; i < length; i++) msg += (char)payload[i];
  

  // --- 1. SWITCH MODE ---
  if (String(topic) == topic_mode) {
    stopMotor(); 
    if (msg == "manual") {
      currentMode = MODE_MANUAL;
      Serial.println("Mode: Manual");
    } 
    else if (msg == "patrol") {
      currentMode = MODE_PATROL;
      patrolState = P_STOP; 
      Serial.println("Mode: Patrol");
    }
    else if (msg == "follow") {
      currentMode = MODE_FOLLOW;
      Serial.println("Mode: Follow");
    }
  }

  // --- 2. MANUAL MODE(FT. SLIDERS FROM NODE-RED) ---
  if (String(topic) == topic_manual_cmd && currentMode == MODE_MANUAL) {
    int commaIndex = msg.indexOf(',');
    if (commaIndex > 0) {
      int leftPWM = msg.substring(0, commaIndex).toInt();
      int rightPWM = msg.substring(commaIndex + 1).toInt();
      driveMotor(leftPWM, rightPWM);
    } 
  }
  
  // --- 3. FOLLOW MODE(FT. PYTHON'S INSTRUCTION)---
  if (String(topic) == topic_follow_cmd && currentMode == MODE_FOLLOW) {
    int commaIndex = msg.indexOf(',');   
    if (commaIndex > 0) {
      int leftPWM = msg.substring(0, commaIndex).toInt();
      int rightPWM = msg.substring(commaIndex + 1).toInt();
      driveMotor(leftPWM, rightPWM);
    } 
  }
}

void reconnect() {
  while (!client.connected()) {
    Serial.print("Trying to connect with MQTT...");
    if (client.connect("mqtt_client_id")) {
      Serial.println("Connected!");
      // SUBSCRIBE ALL THE TOPICS I(WHO AM I? I'm ESP32.) NEED
      client.subscribe(topic_mode);
      client.subscribe(topic_manual_cmd);
      client.subscribe(topic_follow_cmd);
    } else {
      Serial.print("FAIL, rc=");
      Serial.print(client.state());
      Serial.println(" Reconnect after 5s");
      delay(5000);
    }
  }
}

// ==========================================================
// Setup & Loop
// ==========================================================
void setup() {
  WRITE_PERI_REG(RTC_CNTL_BROWN_OUT_REG, 0); 
  
  Serial.begin(115200);
  
  // 1. PIN INITIALIZE
  pinMode(RIGHT1, OUTPUT); pinMode(RIGHT2, OUTPUT);
  pinMode(LEFT1, OUTPUT); pinMode(LEFT2, OUTPUT);

  // 2. PWM INITIALIZE
  ledcSetup(rightChannel, freq, resolution);
  ledcAttachPin(RIGHT_PWM, rightChannel);
  ledcSetup(leftChannel, freq, resolution);
  ledcAttachPin(LEFT_PWM, leftChannel);
  
  stopMotor(); 

  // 3. Wi-Fi
  Serial.print("Connecting to WiFi");
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500); Serial.print(".");
  }
  Serial.println("\nWiFi Connected!");

  // 4. MQTT
  client.setServer(mqtt_server, mqtt_port);
  client.setCallback(callback);
}

void loop() {
  if (!client.connected()) reconnect();
  client.loop(); // KEEP MQTT WORKING

  // ONLY IN PATROL MODE CAN EXCUTE PATROL LOGIC
  if (currentMode == MODE_PATROL) {
    patrolLogic();
  }
}