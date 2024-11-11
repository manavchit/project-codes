#include <WiFiNINA.h>
#include <ArduinoMqttClient.h>

const int IN1 = 2; 
const int irSensor = 3;

// WiFi credentials
const char* ssid = "oplus_co_apdmkd";
const char* password = "tohm3279";

// MQTT settings
const char* mqtt_broker = "broker.hivemq.com";
const int mqtt_port = 1883;
const char* subTopic = "Manav/Attendance"; // Topic to subscribe to

// WiFi and MQTT client objects
WiFiClient wifiClient;
MqttClient mqttClient(wifiClient);

void setup() {
  Serial.begin(9600);

  pinMode(IN1, OUTPUT);
  pinMode(irSensor, INPUT);

  // Connect to WiFi
  connectWiFi();

  // Connect to MQTT broker
  connectMQTT();

  // Set message handler for incoming messages
  mqttClient.onMessage(onMessageReceived);

  digitalWrite(IN1, LOW);

  // Subscribe to the topic
  mqttClient.subscribe(subTopic);
}

void connectWiFi() {
  Serial.print("Connecting to WiFi...");
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nConnected to WiFi");
}

void connectMQTT() {
  Serial.print("Connecting to MQTT broker...");
  while (!mqttClient.connect(mqtt_broker, mqtt_port)) {
    delay(1000);
    Serial.print(".");
  }
  Serial.println("\nConnected to MQTT broker");
}

// Callback function to handle received messages
void onMessageReceived(int messageSize) {
  Serial.print("Received a message: ");

  // Read and print the message
  String message;
  while (mqttClient.available()) {
    char c = mqttClient.read();
    
    message += c;
  }
  digitalWrite(IN1, HIGH);
  // Display the message content in the serial monitor
  Serial.println(message);

  // Optional: Additional handling if specific actions are needed based on the message content
}

void loop() {
  // Poll for incoming messages
  mqttClient.poll();

  int irVal = digitalRead(irSensor);

  if(irVal == LOW){
    digitalWrite(IN1, LOW);
  }

}
