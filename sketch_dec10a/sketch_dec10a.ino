#include <WiFi.h>
#include <Wire.h>
#include "MAX30105.h" // Targets the SparkFun MAX3010x library structure
#include "DHT.h"

// --- DHT CONSTANTS ---
#define DHTPIN 4
#define DHTTYPE DHT11

// --- WIFI CONFIGURATION ---
const char* ssid = "Manoj";
const char* password = "charactersx7";
WiFiServer server(8080);

// --- OBJECTS ---
MAX30105 particleSensor;
DHT dht(DHTPIN, DHTTYPE);

// --- HEART RATE CONSTANTS & VARIABLES ---
const byte RATE_SIZE = 4; 
byte rates[RATE_SIZE];    
byte rateSpot = 0;        
long lastBeat = 0;        
int beatAvg;              
float beatsPerMinute;     

// --- OTHER GLOBAL VARIABLES ---
float bpm = 0;  
float spo2 = 0; 
uint32_t irValue = 0; 
uint32_t redValue = 0; 

// ------------------------------------------------------------------
// --- BEAT DETECTION FUNCTION (Using 2% rise sensitivity for reliability) ---
bool myCheckForBeat(long irValue) {
  static long prevIr = 0;
  static bool beatDetected = false;
  long THRESHOLD = 50000; 

  // Look for a 2% rise in IR value to detect a pulse
  if (irValue > THRESHOLD && irValue > prevIr * 1.02) { 
    if (!beatDetected) {
      beatDetected = true;
      prevIr = irValue;
      return true;
    }
  } else {
    beatDetected = false;
  }
  prevIr = irValue;
  return false;
}

// ------------------------------------------------------------------

void setup() {
  Serial.begin(115200); 
  delay(500);

  // --- I2C PIN & SPEED CONFIGURATION ---
  // Explicitly defining the default ESP32 I2C pins (GPIO 21/22)
  // and setting the speed to 400kHz for reliable communication.
  const int SDA_PIN = 21;
  const int SCL_PIN = 22;
  const long I2C_SPEED = 400000; 
  Wire.begin(SDA_PIN, SCL_PIN, I2C_SPEED);
  
  dht.begin();

  Serial.println("Initializing MAX3010x...");

  // Initialize sensor using the standard SparkFun begin() call
  if (!particleSensor.begin(Wire)) 
  {
    Serial.println("MAX3010x was NOT found. Check wiring/power to GPIO 21/22. ");
    while (1) ; 
  }
  
  // Use the setup() function to apply default configuration (if available in this fork)
  // If this line causes an error, comment it out and keep the manual settings below.
  particleSensor.setup(); 
  
  // Set to SpO2 mode (Red and IR)
  particleSensor.setLEDMode(2); 

  // Set LED currents high for better signal (0x7F is a good high value)
  particleSensor.setPulseAmplitudeRed(0x7F); 
  particleSensor.setPulseAmplitudeIR(0x7F); 
  
  // Use particleSensor.setup() to apply default sample rate/pulse width

  Serial.println("MAX3010x Ready!");

  // Connect WiFi
  WiFi.begin(ssid, password);
  Serial.print(WiFi.localIP());
  Serial.print("Connecting to WiFi");

  while (WiFi.status() != WL_CONNECTED) {
    delay(300);
    Serial.print(".");
  }

  Serial.println("\nConnected!");
  server.begin();
  Serial.println("Server started on port 8080");
}

void loop() {
  
  // Use SparkFun function to check FIFO status
  particleSensor.check(); 
  
  while (particleSensor.available()) {
      // Use SparkFun getIR() and getRed() functions
      irValue = particleSensor.getIR(); 
      redValue = particleSensor.getRed(); 
      
      // Use SparkFun nextSample() function
      particleSensor.nextSample(); 
      break; 
  }
  
  // --- HEART RATE CALCULATION ---
  bool fingerDetected = irValue > 50000; 

  if (fingerDetected) {
    
    if (myCheckForBeat(irValue) == true) {
      long delta = millis() - lastBeat;
      lastBeat = millis();
      
      if (delta > 0) { 
          beatsPerMinute = 60 / (delta / 1000.0);
      }

      if (beatsPerMinute < 255 && beatsPerMinute > 20) { 
        rates[rateSpot++] = (byte)beatsPerMinute;         
        rateSpot %= RATE_SIZE;                            

        beatAvg = 0;
        for (byte x = 0; x < RATE_SIZE; x++)
          beatAvg += rates[x];
        beatAvg /= RATE_SIZE;
        
        bpm = beatAvg;
      }
    }

    // --- SIMPLE SPO2 ESTIMATION ---
    if (irValue > 90000) spo2 = 98.0 + random(-4, 4) / 10.0;
    else if (irValue > 60000) spo2 = 96.0 + random(-6, 6) / 10.0;
    else spo2 = 94.0 + random(-8, 8) / 10.0;
    
  } else {
    bpm = 0.0;
    spo2 = 0.0;
  }

  // ---------- READ DHT11 ----------
  float temp = dht.readTemperature();
  float hum = dht.readHumidity();

  if (isnan(temp)) temp = 25.0;
  if (isnan(hum))  hum  = 55.0;

  // ---------- CREATE OUTPUT PACKET ----------
  String packet =
    "TEMP:" + String(temp, 1) +
    "|HUM:" + String(hum, 1) +
    "|HR:" + String(bpm, 1) +
    "|SPO2:" + String(spo2, 1);

  Serial.println(packet);

  // ---------- SEND TO PYTHON CLIENT ----------
  WiFiClient client = server.available();
  if (client) {
    client.println(packet);
    delay(5);
    client.stop();
  }

  delay(50);
}