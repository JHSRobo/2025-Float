#include <WiFi.h>
#include <WebServer.h>
#include "ArrayList.h"

#include <Wire.h>
#include "MS5837.h"

struct DepthPacket {
  double depth;
  double pressure;
  unsigned long Time;
};
DepthPacket mySensorData;
ArrayList<DepthPacket> mySensorDataList;

struct PIDControl {
  unsigned long time;
  unsigned long prevTime;
  int timeStep;
  double depth;
  double error;
  double integral;
  double derivative;
  double control;
};

bool needCollectPIDData = true;
ArrayList<PIDControl> myPIDControlList;

//PIN assignment
const int MOTOR_IN1 = 33;
const int MOTOR_IN2 = 15;
const int SERVO_PIN = 32;
const int LED = 27;

MS5837 sensor;

unsigned long maxProfilingTime = 150*1000; //15seconds; 60*1000 milliseconds
int profilingCount = 0;
int pumpState; // down = 1, up = -1, idle = 0 
String ctrlCommand = "";
String msg;
String companyName = "EX01";

// Pids initialization
double p = 0.2;
double i = 0.0;
double d = 4;
double targetDepth = 2.5;
double targetDepthTolerance = 0.5;
double prevError = 0.0;
unsigned long prevTime = 0;
unsigned long prevLightMarker = 0;
int bagSize = 0;
int maxBagSize = 90;
int minBagSize = -30;
unsigned long dt;
double integral = 0.0;
double derivative = 0.0;
double error = 0.0;
double control = 0.0;
double depth = 0;
int secondsUpOrDown = 5;
double startDepth = 0.2;

// ESP32 as Access Point (AP), ie., its own local WiFi network
const char* ssid = "JHS_POD";  // Local network SSID
const char* password = "JHSRobo";        // Local network password
const int Wi_Fi_CHANNEL = 6; //1, 6, 11
String Wi_Fi_IP;

// Web Server to handle requests from clients to control the float
WebServer webServer(80);

// Task to run Light
TaskHandle_t Task1;

void setup() {
  // put your setup code here, to run once:
  Serial.begin(115200);
  Wire.begin();
  Wire.setClock(100000);
 
  // Initialize pressure sensor
  // Returns true if initialization was successful
  // We can't continue with the rest of the program unless we can initialize the sensor
  while (!sensor.init()) {
    Serial.println("Init failed!");
    Serial.println("Are SDA/SCL connected correctly?");
    Serial.println("Blue Robotics Bar02: White=SDA, Green=SCL");
    Serial.println("\n\n\n");
    delay(5000);
  }

  // .init sets the sensor model for us but we can override it if required.
  // Uncomment the next line to force the sensor model to the MS5837_30BA.
  sensor.setModel(MS5837::MS5837_02BA);
  sensor.setFluidDensity(1000); // kg/m^3 (freshwater, 1029 for seawater)

  pinMode(MOTOR_IN1, OUTPUT);
  pinMode(MOTOR_IN2, OUTPUT);
  pinMode(LED, OUTPUT);

  digitalWrite(MOTOR_IN1, LOW);
  digitalWrite(MOTOR_IN2, LOW);
  pumpState = 0;

  // Create WiFi network Access Point
  WiFi.softAP(ssid, password, Wi_Fi_CHANNEL);
  Serial.println("Wi-Fi Network Created");
  Wi_Fi_IP = WiFi.softAPIP().toString();
  Serial.println("IP Address: " + Wi_Fi_IP);

  // Configure Web Server Routes
  webServer.on("/data", handleDataRequest);
  webServer.on("/ctrl", handleControlRequest);
  webServer.on("/piddata", handlePIDDataRequest);
  webServer.begin();
  Serial.println("Web Server Started");
  xTaskCreatePinnedToCore(
                  runLight,   /* Task function. */
                  "Task1",     /* name of task. */
                  10000,       /* Stack size of task */
                  NULL,        /* parameter of the task */
                  1,           /* priority of the task */
                  &Task1,      /* Task handle to keep track of created task */
                  1);          /* pin task to core 1 */    
}

bool profilingStarted = false;
double timeStep;
unsigned long profilingStartTime = millis();
int totalTimeAtTarget = 0; //in seconds
unsigned long now;
double max_integral = 0;
bool goToSurface = false;

void loop() {
  //check if any control command
  webServer.handleClient();
  delay(1000);

  if (ctrlCommand == "START"){
    mySensorData = readDepthSensor();
    depth = mySensorData.depth;

    if (depth < -1.0 || depth > 5.0) {
      digitalWrite(MOTOR_IN1, LOW);
      digitalWrite(MOTOR_IN2, LOW);
      pumpState = 2;
      return; //exit the current loop iteration if bad depth reading
    }
    else {
      mySensorDataList.add(mySensorData);
    }

    //initialize profiling vars
    if (!profilingStarted) {
      startDepth = depth;
      profilingStartTime = millis();
      totalTimeAtTarget = 0;      
      integral = 0;
      prevError = 0;
      prevTime = millis();    
      prevLightMarker = prevTime;  
      bagSize = 0;
      if (i != 0)
        max_integral = 0.5 / i; //based on i parameter

      profilingStarted = true;
    }
 
    if (!goToSurface) {        
      // fail safes
      if ((millis() - profilingStartTime > maxProfilingTime) || (bagSize > maxBagSize)) {
        ctrlCommand = "";
        abortProfiling();
        return;
      }

      Serial.println(bagSize);

      now = millis();
      timeStep = (now - prevTime)/1000.0; //in seconds
      error = targetDepth - depth;
      if (abs(2.5 - depth) <= targetDepthTolerance) {
        totalTimeAtTarget += timeStep;
        if (totalTimeAtTarget >= 60) {
          goToSurface = true;
          return;
        }
      }
     
      //PID control
      integral += error * timeStep;
      integral = constrain(integral, -1*max_integral, max_integral);
      if (timeStep > 0)
        derivative = (error - prevError) / timeStep;
      else
        derivative = 0;
      control = p * error + i * integral + d * derivative;
      control = constrain(control, -1, 1);
     
      if (needCollectPIDData)
        collectPIDControlData(now, prevTime, timeStep, depth, error, integral, derivative, control);

      prevError = error;
      prevTime = now;

      // the derivative equals the velocity, so we are checking if the float is traveling at less than 0.01 m/s (idling)
      if ((abs(derivative) <= 0.01) && (depth > 2.25 && depth < 2.75)) {
        digitalWrite(MOTOR_IN1, LOW);
        digitalWrite(MOTOR_IN2, LOW);
        pumpState = 0;
        return;
      }

      if (control > 0.05) { // adjustment going down
        digitalWrite(MOTOR_IN2, LOW);
        digitalWrite(MOTOR_IN1, HIGH);
        pumpState = 1;
        bagSize += 1;
      }
      else if (control < -0.05) {
        digitalWrite(MOTOR_IN1, LOW);  
        digitalWrite(MOTOR_IN2, HIGH);    
        pumpState = -1;     
        bagSize -= 1; 
      }
      else {
        if (pumpState == 1 || pumpState == -1){
          Serial.println("THIS IS THE DIRECTION: " + String(pumpState));
          slow_to_idle(pumpState);
          pumpState = 0;
        }
        else {
          digitalWrite(MOTOR_IN1, LOW);
          digitalWrite(MOTOR_IN2, LOW);
          pumpState = 0;
        }
      }
    }
    else {
      //after 45 second maintaining at target depth, go up
      if (depth >= startDepth + 1.0) {
        digitalWrite(MOTOR_IN1, LOW);
        digitalWrite(MOTOR_IN2, HIGH);
        pumpState = 3;
      }
      else {//coasting
        digitalWrite(MOTOR_IN2, LOW);
      }
      //reset profiling control vars when depth is close to starting depth (+0.2 m tolerance)
      if (depth <= startDepth + 0.2) {
        ctrlCommand = "";
        profilingStarted = false;
        goToSurface = false;
        pumpState = 0;
      }
    }
  }
  else {
    mySensorData = readDepthSensor();
  }
}

// Send Sensor Data as plain text
void handleDataRequest() {
  Serial.println("Preparing data payload to be sent ...");
 
  //multiple lines format
  String dataPayload = "";
  for (int i = 0; i < mySensorDataList.size(); i++) {
    if (i != 0)
      dataPayload += "\n";
    DepthPacket data = mySensorDataList.get(i);
    dataPayload += getDataPacketString(data);
  }
  webServer.send(200, "text/plain", dataPayload);
  Serial.println("Data payload is sent.");
};

void slow_to_idle(int dir) {
  if (dir == -1) {
    for (int i = 250; i > 0; i-=5){
      analogWrite(MOTOR_IN2, i);
      delay(10);
    }
  }
  else if (dir == 1) {
    for (int i = 250; i > 0; i-=5){
      analogWrite(MOTOR_IN1, i);
      delay(10);
    }
  }

  pinMode(MOTOR_IN1, OUTPUT);
  pinMode(MOTOR_IN2, OUTPUT);
  digitalWrite(MOTOR_IN1, LOW);
  digitalWrite(MOTOR_IN2, LOW);
}

// Send Sensor Data as JSON
void handleControlRequest() {
  String msg;
  Serial.println("Processing control request...");

  if (webServer.hasArg("command"))
  {
    ctrlCommand = webServer.arg("command");
    Serial.println(ctrlCommand);

    if (ctrlCommand == "START") {  
      profilingCount++;
      mySensorDataList.clear();
      myPIDControlList.clear();
      p = webServer.arg("p").toDouble();
      i = webServer.arg("i").toDouble();
      d = webServer.arg("d").toDouble();
      prevTime = millis();
      msg = "Received START command with pid(" + webServer.arg("p") + ", " + webServer.arg("i") + ", " + webServer.arg("d") + "). Profiling " + String(profilingCount) + " starts...";
      Serial.println(msg);
      webServer.send(200, "text/plain", msg);
      //msg = "Profiling is finished."; //may have error for send response the 2nd time at the end of this function. TODO - test
    }
    else if (ctrlCommand == "STATUS") {
      mySensorData = readDepthSensor();
      msg = getDataPacketString(mySensorData) + " p " + String(p) + " i " + String(i) + " d " + String(d);
    }
    else if (ctrlCommand == "UP") {
      secondsUpOrDown = webServer.arg("seconds").toDouble();
      digitalWrite(MOTOR_IN2, HIGH);
      digitalWrite(MOTOR_IN1, LOW);
      pumpState = -1;
      delay(secondsUpOrDown * 1000);
      digitalWrite(MOTOR_IN2, LOW);
      pumpState = 0;
      msg = "Going UP for " + String(secondsUpOrDown) + " seconds.";
    }
    else if (ctrlCommand == "DOWN") {
      secondsUpOrDown = webServer.arg("seconds").toDouble();
      digitalWrite(MOTOR_IN1, HIGH);
      digitalWrite(MOTOR_IN2, LOW);
      pumpState = 1;
      delay(secondsUpOrDown * 1000);
      digitalWrite(MOTOR_IN1, LOW);
      pumpState = 0;
      msg = "Going DOWN for " + String(secondsUpOrDown) + " seconds.";
    }
    else if (ctrlCommand == "STOP"){
      digitalWrite(MOTOR_IN1, LOW);
      digitalWrite(MOTOR_IN2, LOW);
      msg = "Stopped pump.";
    }
    else if (ctrlCommand == "RESET"){
      Serial.println("Reset starting now...");
      ESP.restart();
    }
    else if (ctrlCommand == "GETCONFIG"){
      mySensorData = readDepthSensor();
      msg = "{" + getQuotedFieldName("Company Name") + getQuotedString(companyName)
        + ", " + getQuotedFieldName("Max Profiling Time") + String(maxProfilingTime / 1000)
        + ", " + getQuotedFieldName("Target Depth") + String(targetDepth)
        + ", " + getQuotedFieldName("Target Depth Tolerance") + String(targetDepthTolerance)
        + ", " + getQuotedFieldName("Current Depth") + String(mySensorData.depth)
        + ", " + getQuotedFieldName("Float ESP32 IP") + getQuotedString(Wi_Fi_IP)
        + "}";
    }
    else if (ctrlCommand == "SETCONFIG"){
      if (webServer.arg("Company Name") != "" &&
        webServer.arg("Max Profiling Time").toInt() != 0 &&
        webServer.arg("Target Depth Tolerance").toDouble() != 0
        ) {
        companyName = webServer.arg("Company Name");
        maxProfilingTime = webServer.arg("Max Profiling Time").toInt() * 1000;
        targetDepth = webServer.arg("Target Depth").toDouble();
        targetDepthTolerance = webServer.arg("Target Depth Tolerance").toDouble();
        Serial.print(companyName + " " + String(maxProfilingTime) + " " + String(targetDepthTolerance));
        msg = "Config settings are updated.";
      }
      else
        msg = "Invalid values in sent config settings.";
    }
    else {
      msg = "Command " + ctrlCommand + " received. But it is not coded yet.";
    }
    webServer.send(200, "text/plain", msg);
    Serial.println(msg);
  }
};

//go up without collecting data
void abortProfiling() {
  Serial.println("Aborting!");
  ctrlCommand = "";
  profilingStarted = false;
  goToSurface = false;

  digitalWrite(MOTOR_IN1, LOW);
  digitalWrite(MOTOR_IN2, HIGH);
  pumpState = 2;

  while (true) {
    delay(1000);
    mySensorData = readDepthSensor();
    depth = mySensorData.depth;
    if (depth < -1.0 || depth > 5.0){
      continue;
    }
    else 
    {
      mySensorDataList.add(mySensorData);    
      if (depth <= startDepth + 0.2) {
        break;
      }
    }
  }
  
  digitalWrite(MOTOR_IN2, LOW);
  pumpState = 0;

  Serial.println("Aborting is finished!");
}

DepthPacket readDepthSensor() {
  DepthPacket data;
  sensor.read();
  data.depth = sensor.depth();
  data.pressure = sensor.pressure();
  data.Time = millis()/1000;
  Serial.println(data.depth);
  return data;
};

String getDataPacketString(DepthPacket data){
  String s = companyName + " " + String(data.Time) + " s " + String(data.pressure) + " kpa " + String(data.depth) + " m";
  Serial.println(s);
  return s;
};

String getQuotedString(String s){
  return "\"" + s + "\"";
}

String getQuotedFieldName(String s) {
  return "\"" + s + "\":";
}

void collectPIDControlData(unsigned long now, unsigned long prevTime, int timeStep, double depth, double error, double integral, double derivative, double control){
  //time, timestep, depth, error, integral, derivative, control
  PIDControl myPIDControl;
  myPIDControl.time = now;
  myPIDControl.prevTime = prevTime;
  myPIDControl.timeStep = timeStep;
  myPIDControl.depth = depth;
  myPIDControl.error = error;
  myPIDControl.integral = integral;
  myPIDControl.derivative = derivative;
  myPIDControl.control = control;
  myPIDControlList.add(myPIDControl);
}

// Send Sensor Data as plain text
void handlePIDDataRequest() {
  Serial.println("Preparing data payload to be sent ...");
 
  //multiple lines format
  String dataPayload = "[";
  String record;
  for (int i = 0; i<myPIDControlList.size(); i++) {
    if (i != 0)
      dataPayload += ",";
    PIDControl data = myPIDControlList.get(i);
    record = "{" + getQuotedFieldName("Time") + String(data.time)
      +", " + getQuotedFieldName("Prev Time") + String(data.prevTime)
      +", " + getQuotedFieldName("Time Step") + String(data.timeStep)
      +", " + getQuotedFieldName("Depth") + String(data.depth)
      +", " + getQuotedFieldName("Error") + String(data.error)
      +", " + getQuotedFieldName("Integral") + String(data.integral)
      +", " + getQuotedFieldName("Derivative") + String(data.derivative)
      +", " + getQuotedFieldName("Control") + String(data.control)
      + "}";
    dataPayload += record;
  }
  dataPayload += "]";
  webServer.send(200, "text/plain", dataPayload);
  Serial.println("PID payload is sent.");
}

void runLight(void * pvParameters){
  while (true) {
    if (pumpState == -1){
      digitalWrite(LED, HIGH);
      delay(150);
      digitalWrite(LED, LOW);
      delay(150);
    }
    else if (pumpState == 0) {
      digitalWrite(LED, LOW);
      delay(200);
    }
    else if (pumpState == 1) {
      digitalWrite(LED, HIGH);
      delay(200);
      digitalWrite(LED, LOW);
      delay(800);
    }
    else if (pumpState = 2) {
      digitalWrite(LED, HIGH);
      delay(50);
      digitalWrite(LED, LOW);
      delay(50);
    }
    else {
      digitalWrite(LED, HIGH);
      delay(200);
    }
  }
}