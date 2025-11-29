#include <WiFi.h>
#include <WebServer.h>

const char* ssid = "Abang Dias";
const char* password = "Qian1985";

bool useStaticIP = true;
IPAddress local_IP(192, 168, 1, 101);
IPAddress gateway(192, 168, 1, 1);
IPAddress subnet(255, 255, 255, 0);
IPAddress primaryDNS(8, 8, 8, 8);
IPAddress secondaryDNS(8, 8, 4, 4);

const int BUZZER_PIN = 5;
const int SHORT_BEEP = 200;
const int LONG_BEEP = 1000;
const int BEEP_PAUSE = 300;

// ============================================
// GLOBAL VARIABLES
// ============================================
WebServer server(80);

unsigned long lastReconnectAttempt = 0;
unsigned long lastAlertTime = 0;
int alertCount = 0;
bool buzzerActive = false;

// ============================================
// BUZZER CONTROL FUNCTIONS
// ============================================

void beep(int duration) {
  digitalWrite(BUZZER_PIN, HIGH);
  delay(duration);
  digitalWrite(BUZZER_PIN, LOW);
}

void shortBeep() {
  beep(SHORT_BEEP);
}

void longBeep() {
  beep(LONG_BEEP);
}

void alertPattern1() {
  for (int i = 0; i < 3; i++) {
    longBeep();
    if (i < 2) delay(BEEP_PAUSE);
  }
}

void alertPattern2() {
  unsigned long startTime = millis();
  while (millis() - startTime < 5000) {
    shortBeep();
    delay(200);
  }
}

void alertPattern3() {
  for (int i = 0; i < 5; i++) {
    shortBeep();
    delay(100);
  }
}

void testPattern() {
  shortBeep();
}

// ============================================
// WIFI CONNECTION
// ============================================
void connectWiFi() {
  Serial.println();
  Serial.print("Connecting to WiFi: ");
  Serial.println(ssid);

  if (useStaticIP) {
    if (!WiFi.config(local_IP, gateway, subnet, primaryDNS, secondaryDNS)) {
      Serial.println("Static IP configuration failed!");
    }
  }

  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);

  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 30) {
    delay(500);
    Serial.print(".");
    attempts++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println();
    Serial.println("WiFi connected!");
    Serial.print("IP Address: ");
    Serial.println(WiFi.localIP());
    
    shortBeep();
  } else {
    Serial.println();
    Serial.println("WiFi connection failed!");
  }
}

void checkWiFi() {
  if (WiFi.status() != WL_CONNECTED) {
    unsigned long currentMillis = millis();
    if (currentMillis - lastReconnectAttempt >= 10000) {
      Serial.println("WiFi disconnected. Reconnecting...");
      lastReconnectAttempt = currentMillis;
      connectWiFi();
    }
  }
}

// ============================================
// WEB SERVER HANDLERS
// ============================================

void handleRoot() {
  String html = "<!DOCTYPE html><html><head>";
  html += "<meta name='viewport' content='width=device-width, initial-scale=1'>";
  html += "<style>";
  html += "body { font-family: Arial; margin: 20px; background: #f0f0f0; }";
  html += ".container { background: white; padding: 20px; border-radius: 10px; max-width: 600px; margin: 0 auto; }";
  html += "h1 { color: #333; }";
  html += ".status { padding: 10px; background: #4CAF50; color: white; border-radius: 5px; margin: 10px 0; }";
  html += ".button { display: block; padding: 15px; background: #2196F3; color: white; text-decoration: none; border-radius: 5px; margin: 10px 0; text-align: center; border: none; font-size: 16px; cursor: pointer; }";
  html += ".button:hover { background: #0b7dda; }";
  html += ".button.red { background: #f44336; }";
  html += ".button.red:hover { background: #da190b; }";
  html += ".info { background: #f9f9f9; padding: 10px; border-left: 4px solid #2196F3; margin: 10px 0; }";
  html += "</style>";
  html += "<script>";
  html += "function triggerAlert(pattern) {";
  html += "  fetch('/alert?pattern=' + pattern).then(r => r.text()).then(d => alert(d));";
  html += "}";
  html += "function testBuzzer() {";
  html += "  fetch('/test').then(r => r.text()).then(d => alert(d));";
  html += "}";
  html += "</script>";
  html += "</head><body>";
  html += "<div class='container'>";
  html += "<h1>ESP32 Buzzer Control</h1>";
  html += "<div class='status'>System Online</div>";
  html += "<div class='info'><strong>IP Address:</strong> " + WiFi.localIP().toString() + "</div>";
  html += "<div class='info'><strong>Uptime:</strong> " + String(millis() / 1000) + " seconds</div>";
  html += "<div class='info'><strong>Alerts Today:</strong> " + String(alertCount) + "</div>";
  html += "<h3>Test Buzzer</h3>";
  html += "<button class='button' onclick='testBuzzer()'>Test Buzzer</button>";
  html += "<h3>Alert Patterns</h3>";
  html += "<button class='button red' onclick='triggerAlert(1)'>Pattern 1 (3 Long Beeps)</button>";
  html += "<button class='button red' onclick='triggerAlert(2)'>Pattern 2 (Continuous 5s)</button>";
  html += "<button class='button red' onclick='triggerAlert(3)'>Pattern 3 (5 Rapid Beeps)</button>";
  html += "<a href='/status' class='button'>View Status (JSON)</a>";
  html += "</div></body></html>";
  
  server.send(200, "text/html", html);
}

void handleAlert() {
  buzzerActive = true;
  int pattern = 1;
  if (server.hasArg("pattern")) {
    pattern = server.arg("pattern").toInt();
  }
  
  Serial.println("========================================");
  Serial.print("Alert received! Pattern: ");
  Serial.println(pattern);
  Serial.print("Time: ");
  Serial.println(millis());
  
  switch (pattern) {
    case 1:
      alertPattern1();
      break;
    case 2:
      alertPattern2();
      break;
    case 3:
      alertPattern3();
      break;
    default:
      alertPattern1();
  }
  
  lastAlertTime = millis();
  alertCount++;
  buzzerActive = false;
  
  Serial.println("Alert complete");
  Serial.println("========================================");
  
  String response = "{";
  response += "\"status\":\"success\",";
  response += "\"message\":\"Alert triggered\",";
  response += "\"pattern\":" + String(pattern) + ",";
  response += "\"timestamp\":" + String(millis()) + ",";
  response += "\"alert_count\":" + String(alertCount);
  response += "}";
  
  server.send(200, "application/json", response);
}

void handleTest() {
  Serial.println("Test buzzer triggered");
  testPattern();

  String response = "{";
  response += "\"status\":\"success\",";
  response += "\"message\":\"Test beep completed\"";
  response += "}";
  
  server.send(200, "application/json", response);
}

void handleStatus() {
  unsigned long uptime = millis() / 1000;
  unsigned long timeSinceLastAlert = (millis() - lastAlertTime) / 1000;
  
  String json = "{";
  json += "\"status\":\"online\",";
  json += "\"device\":\"ESP32-Buzzer\",";
  json += "\"ip\":\"" + WiFi.localIP().toString() + "\",";
  json += "\"uptime\":" + String(uptime) + ",";
  json += "\"wifi_rssi\":" + String(WiFi.RSSI()) + ",";
  json += "\"alert_count\":" + String(alertCount) + ",";
  json += "\"last_alert\":" + String(timeSinceLastAlert) + ",";
  json += "\"buzzer_active\":" + String(buzzerActive ? "true" : "false") + ",";
  json += "\"free_heap\":" + String(ESP.getFreeHeap());
  json += "}";

  server.send(200, "application/json", json);
}

void handlePing() {
  server.send(200, "text/plain", "pong");
}

void handleNotFound() {
  String message = "Not Found\n\n";
  message += "URI: " + server.uri() + "\n";
  message += "Method: " + String((server.method() == HTTP_GET) ? "GET" : "POST") + "\n";
  message += "\nAvailable endpoints:\n";
  message += "  GET  /          - Control panel\n";
  message += "  GET  /alert     - Trigger alert (add ?pattern=1-3)\n";
  message += "  GET  /test      - Test buzzer\n";
  message += "  GET  /status    - System status (JSON)\n";
  message += "  GET  /ping      - Health check\n";
  
  server.send(404, "text/plain", message);
}

// ============================================
// SETUP
// ============================================
void setup() {
  Serial.begin(115200);
  Serial.println();
  Serial.println("========================================");
  Serial.println("ESP32 Buzzer Alert System");
  Serial.println("========================================");

  pinMode(BUZZER_PIN, OUTPUT);
  digitalWrite(BUZZER_PIN, LOW);
  
  Serial.println("Buzzer initialized on GPIO " + String(BUZZER_PIN));
  Serial.println("Testing buzzer...");

  shortBeep();
  delay(200);
  shortBeep();
  connectWiFi();

  server.on("/", handleRoot);
  server.on("/alert", handleAlert);
  server.on("/test", handleTest);
  server.on("/status", handleStatus);
  server.on("/ping", handlePing);
  server.onNotFound(handleNotFound);

  server.begin();
  Serial.println("HTTP server started");
  Serial.println("========================================");
  Serial.println("Ready!");
  Serial.print("Control panel: http://");
  Serial.println(WiFi.localIP());
  Serial.println("========================================");
  
  delay(500);
  shortBeep();
  delay(200);
  shortBeep();
}

// ============================================
// LOOP
// ============================================
void loop() {
  checkWiFi();
  server.handleClient();
  delay(1);
}