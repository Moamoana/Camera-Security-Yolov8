/*
 * ESP32-CAM HTTP Stream Server with Camera Selection
 * Support for multiple camera models
 * Web interface for camera configuration
 * 
 * Supported cameras:
 * - AI-Thinker
 * - M5Stack
 * - M5Stack Wide
 * - ESP Eye
 * - WROVER Kit
 */

#include "esp_camera.h"
#include <WiFi.h>
#include <WebServer.h>
#include <Preferences.h>

// ============================================
// WiFi Configuration
// ============================================
const char* ssid = "Moa";
const char* password = "kontolbahlil";

// ============================================
// Camera Models
// ============================================
enum CameraModel {
  AI_THINKER = 0,
  M5STACK_PSRAM,
  M5STACK_WIDE,
  ESP_EYE,
  WROVER_KIT
};

// Current camera model (default:  AI-Thinker)
CameraModel currentCamera = AI_THINKER;

// ============================================
// Camera Pin Definitions
// ============================================

// AI-Thinker ESP32-CAM
const camera_config_t ai_thinker_config = {
  .pin_pwdn = 32,
  .pin_reset = -1,
  .pin_xclk = 0,
  .pin_sscb_sda = 26,
  .pin_sscb_scl = 27,
  .pin_d7 = 35,
  .pin_d6 = 34,
  .pin_d5 = 39,
  .pin_d4 = 36,
  . pin_d3 = 21,
  .pin_d2 = 19,
  .pin_d1 = 18,
  . pin_d0 = 5,
  .pin_vsync = 25,
  .pin_href = 23,
  .pin_pclk = 22
};

// M5Stack ESP32-CAM
const camera_config_t m5stack_config = {
  .pin_pwdn = -1,
  .pin_reset = 15,
  .pin_xclk = 27,
  .pin_sscb_sda = 25,
  .pin_sscb_scl = 23,
  .pin_d7 = 19,
  .pin_d6 = 36,
  .pin_d5 = 18,
  .pin_d4 = 39,
  .pin_d3 = 5,
  .pin_d2 = 34,
  .pin_d1 = 35,
  .pin_d0 = 32,
  .pin_vsync = 22,
  .pin_href = 26,
  .pin_pclk = 21
};

// M5Stack Wide
const camera_config_t m5stack_wide_config = {
  .pin_pwdn = -1,
  .pin_reset = 15,
  .pin_xclk = 27,
  .pin_sscb_sda = 22,
  .pin_sscb_scl = 23,
  .pin_d7 = 19,
  . pin_d6 = 36,
  .pin_d5 = 18,
  . pin_d4 = 39,
  .pin_d3 = 5,
  . pin_d2 = 34,
  .pin_d1 = 35,
  . pin_d0 = 32,
  .pin_vsync = 25,
  .pin_href = 26,
  .pin_pclk = 21
};

// ESP Eye
const camera_config_t esp_eye_config = {
  .pin_pwdn = -1,
  .pin_reset = -1,
  .pin_xclk = 4,
  .pin_sscb_sda = 18,
  .pin_sscb_scl = 23,
  .pin_d7 = 36,
  .pin_d6 = 37,
  .pin_d5 = 38,
  .pin_d4 = 39,
  . pin_d3 = 35,
  .pin_d2 = 14,
  .pin_d1 = 13,
  . pin_d0 = 34,
  .pin_vsync = 5,
  .pin_href = 27,
  .pin_pclk = 25
};

// WROVER Kit
const camera_config_t wrover_kit_config = {
  .pin_pwdn = -1,
  .pin_reset = -1,
  .pin_xclk = 21,
  .pin_sscb_sda = 26,
  .pin_sscb_scl = 27,
  .pin_d7 = 35,
  .pin_d6 = 34,
  . pin_d5 = 39,
  .pin_d4 = 36,
  . pin_d3 = 19,
  .pin_d2 = 18,
  . pin_d1 = 5,
  .pin_d0 = 4,
  .pin_vsync = 25,
  .pin_href = 23,
  .pin_pclk = 22
};

WebServer server(80);
Preferences preferences;

// Camera settings
int jpegQuality = 10;    // 0-63, lower = higher quality
int frameSize = 10;      // FRAMESIZE_VGA = 10
int brightness = 0;      // -2 to 2
int contrast = 0;        // -2 to 2

// ============================================
// Get Camera Config by Model
// ============================================
camera_config_t getCameraConfig(CameraModel model) {
  switch(model) {
    case AI_THINKER:
      return ai_thinker_config;
    case M5STACK_PSRAM:
      return m5stack_config;
    case M5STACK_WIDE:
      return m5stack_wide_config;
    case ESP_EYE:
      return esp_eye_config;
    case WROVER_KIT:
      return wrover_kit_config;
    default:
      return ai_thinker_config;
  }
}

// ============================================
// Camera Initialization
// ============================================
bool initCamera() {
  // Get config for current camera model
  camera_config_t config = getCameraConfig(currentCamera);
  
  // Common settings
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;
  config.xclk_freq_hz = 20000000;
  config.pixel_format = PIXFORMAT_JPEG;
  config.frame_size = (framesize_t)frameSize;
  config.jpeg_quality = jpegQuality;
  config.fb_count = 2;
  config.grab_mode = CAMERA_GRAB_LATEST;
  
  // Camera init
  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("Camera init failed: 0x%x\n", err);
    return false;
  }
  
  // Apply settings
  sensor_t *s = esp_camera_sensor_get();
  if (s) {
    s->set_brightness(s, brightness);
    s->set_contrast(s, contrast);
  }
  
  Serial.println("✓ Camera initialized!");
  return true;
}

// ============================================
// Save/Load Settings from Flash
// ============================================
void saveSettings() {
  preferences.begin("camera", false);
  preferences.putInt("model", currentCamera);
  preferences.putInt("quality", jpegQuality);
  preferences.putInt("framesize", frameSize);
  preferences.putInt("brightness", brightness);
  preferences.putInt("contrast", contrast);
  preferences.end();
  Serial.println("Settings saved!");
}

void loadSettings() {
  preferences.begin("camera", true);
  currentCamera = (CameraModel)preferences.getInt("model", AI_THINKER);
  jpegQuality = preferences.getInt("quality", 10);
  frameSize = preferences.getInt("framesize", 10);
  brightness = preferences.getInt("brightness", 0);
  contrast = preferences.getInt("contrast", 0);
  preferences.end();
  Serial.println("Settings loaded!");
}

// ============================================
// HTTP Stream Handler (FIXED)
// ============================================
void handleStream() {
  WiFiClient client = server.client();
  
  String response = "HTTP/1.1 200 OK\r\n";
  response += "Content-Type: multipart/x-mixed-replace; boundary=frame\r\n";
  response += "Connection: close\r\n";
  response += "\r\n";
  server.sendContent(response);
  
  Serial.println("Stream started");
  
  while (client.connected()) {
    camera_fb_t *fb = esp_camera_fb_get();
    if (!fb) {
      Serial.println("Camera capture failed");
      delay(100);
      continue;
    }
    
    // Properly formatted MJPEG boundary
    String header = "--frame\r\n";
    header += "Content-Type: image/jpeg\r\n";
    header += "Content-Length: " + String(fb->len) + "\r\n";
    header += "\r\n";
    
    server.sendContent(header);
    client.write(fb->buf, fb->len);
    server.sendContent("\r\n");
    
    esp_camera_fb_return(fb);
    
    if (!client. connected()) {
      break;
    }
  }
  
  Serial.println("Stream stopped");
}

// ============================================
// Status Handler (JSON)
// ============================================
void handleStatus() {
  String json = "{";
  json += "\"status\": \"online\",";
  json += "\"camera\": \"" + String(getCameraName()) + "\",";
  json += "\"ip\":\"" + WiFi.localIP().toString() + "\",";
  json += "\"quality\":" + String(jpegQuality) + ",";
  json += "\"framesize\":" + String(frameSize) + ",";
  json += "\"brightness\":" + String(brightness) + ",";
  json += "\"contrast\":" + String(contrast) + ",";
  json += "\"rssi\":" + String(WiFi.RSSI());
  json += "}";
  
  server.send(200, "application/json", json);
}

// ============================================
// Camera Name Helper
// ============================================
String getCameraName() {
  switch(currentCamera) {
    case AI_THINKER: return "AI-Thinker";
    case M5STACK_PSRAM: return "M5Stack";
    case M5STACK_WIDE: return "M5Stack Wide";
    case ESP_EYE: return "ESP Eye";
    case WROVER_KIT: return "WROVER Kit";
    default: return "Unknown";
  }
}

// ============================================
// Settings Page Handler
// ============================================
void handleSettings() {
  if (server.hasArg("save")) {
    // Save new settings
    if (server.hasArg("camera")) {
      int newCamera = server.arg("camera").toInt();
      if (newCamera != currentCamera) {
        currentCamera = (CameraModel)newCamera;
        esp_camera_deinit();
        delay(100);
        initCamera();
      }
    }
    if (server.hasArg("quality")) jpegQuality = server.arg("quality").toInt();
    if (server.hasArg("framesize")) frameSize = server.arg("framesize").toInt();
    if (server.hasArg("brightness")) brightness = server.arg("brightness").toInt();
    if (server.hasArg("contrast")) contrast = server.arg("contrast").toInt();
    
    // Apply settings
    sensor_t *s = esp_camera_sensor_get();
    if (s) {
      s->set_quality(s, jpegQuality);
      s->set_framesize(s, (framesize_t)frameSize);
      s->set_brightness(s, brightness);
      s->set_contrast(s, contrast);
    }
    
    saveSettings();
  }
  
  // Build HTML page
  String html = "<!DOCTYPE html><html><head>";
  html += "<meta name='viewport' content='width=device-width, initial-scale=1'>";
  html += "<style>";
  html += "body{font-family: Arial;margin:20px;background:#f0f0f0}";
  html += ". container{max-width:600px;margin:0 auto;background: white;padding:20px;border-radius:10px}";
  html += "h1{color:#333}";
  html += ". setting{margin:15px 0;padding:10px;background:#f9f9f9;border-radius:5px}";
  html += "label{display:block;font-weight:bold;margin-bottom:5px}";
  html += "select,input{width:100%;padding:8px;border:1px solid #ddd;border-radius:4px}";
  html += "button{background:#4CAF50;color:white;padding:10px 20px;border:none;border-radius:5px;cursor:pointer;font-size:16px}";
  html += "button:hover{background:#45a049}";
  html += ". info{background:#e3f2fd;padding:10px;border-radius:5px;margin: 10px 0}";
  html += "</style></head><body>";
  
  html += "<div class='container'>";
  html += "<h1>📷 ESP32-CAM Settings</h1>";
  
  html += "<div class='info'>";
  html += "<strong>Current Camera:</strong> " + getCameraName() + "<br>";
  html += "<strong>IP: </strong> " + WiFi.localIP().toString() + "<br>";
  html += "<strong>Stream: </strong> <a href='/stream'>/stream</a>";
  html += "</div>";
  
  html += "<form action='/settings' method='GET'>";
  
  // Camera Model
  html += "<div class='setting'>";
  html += "<label>Camera Model:</label>";
  html += "<select name='camera'>";
  html += "<option value='0'" + String(currentCamera == AI_THINKER ? " selected" : "") + ">AI-Thinker</option>";
  html += "<option value='1'" + String(currentCamera == M5STACK_PSRAM ? " selected" : "") + ">M5Stack</option>";
  html += "<option value='2'" + String(currentCamera == M5STACK_WIDE ? " selected" : "") + ">M5Stack Wide</option>";
  html += "<option value='3'" + String(currentCamera == ESP_EYE ? " selected" :  "") + ">ESP Eye</option>";
  html += "<option value='4'" + String(currentCamera == WROVER_KIT ?  " selected" : "") + ">WROVER Kit</option>";
  html += "</select>";
  html += "</div>";
  
  // JPEG Quality
  html += "<div class='setting'>";
  html += "<label>JPEG Quality (0=best, 63=worst):</label>";
  html += "<input type='range' name='quality' min='0' max='63' value='" + String(jpegQuality) + "' oninput='this.nextElementSibling.value=this.value'>";
  html += "<output>" + String(jpegQuality) + "</output>";
  html += "</div>";
  
  // Frame Size
  html += "<div class='setting'>";
  html += "<label>Frame Size:</label>";
  html += "<select name='framesize'>";
  html += "<option value='6'" + String(frameSize == 6 ? " selected" : "") + ">QVGA (320x240)</option>";
  html += "<option value='7'" + String(frameSize == 7 ? " selected" : "") + ">CIF (400x296)</option>";
  html += "<option value='8'" + String(frameSize == 8 ? " selected" : "") + ">HVGA (480x320)</option>";
  html += "<option value='10'" + String(frameSize == 10 ? " selected" :  "") + ">VGA (640x480)</option>";
  html += "<option value='11'" + String(frameSize == 11 ? " selected" : "") + ">SVGA (800x600)</option>";
  html += "<option value='12'" + String(frameSize == 12 ? " selected" :  "") + ">XGA (1024x768)</option>";
  html += "<option value='13'" + String(frameSize == 13 ? " selected" : "") + ">HD (1280x720)</option>";
  html += "</select>";
  html += "</div>";
  
  // Brightness
  html += "<div class='setting'>";
  html += "<label>Brightness (-2 to +2):</label>";
  html += "<input type='range' name='brightness' min='-2' max='2' value='" + String(brightness) + "' oninput='this.nextElementSibling.value=this.value'>";
  html += "<output>" + String(brightness) + "</output>";
  html += "</div>";
  
  // Contrast
  html += "<div class='setting'>";
  html += "<label>Contrast (-2 to +2):</label>";
  html += "<input type='range' name='contrast' min='-2' max='2' value='" + String(contrast) + "' oninput='this.nextElementSibling.value=this. value'>";
  html += "<output>" + String(contrast) + "</output>";
  html += "</div>";
  
  html += "<button type='submit' name='save' value='1'>💾 Save Settings</button>";
  html += "</form>";
  
  html += "<div style='margin-top:20px'>";
  html += "<a href='/'><button style='background:#2196F3'>🏠 Home</button></a> ";
  html += "<a href='/stream'><button style='background:#FF9800'>📹 View Stream</button></a>";
  html += "</div>";
  
  html += "</div></body></html>";
  
  server.send(200, "text/html", html);
}

// ============================================
// Root Handler (Home Page)
// ============================================
void handleRoot() {
  String html = "<!DOCTYPE html><html><head>";
  html += "<meta name='viewport' content='width=device-width, initial-scale=1'>";
  html += "<style>";
  html += "body{font-family:Arial;margin:0;padding:20px;background:#f0f0f0}";
  html += ".container{max-width:600px;margin:0 auto;background:white;padding:20px;border-radius:10px;box-shadow:0 2px 10px rgba(0,0,0,0.1)}";
  html += "h1{color:#333;margin-top:0}";
  html += ".status{background:#4CAF50;color:white;padding:15px;border-radius:5px;margin:15px 0}";
  html += ".button{display:inline-block;background:#2196F3;color: white;padding:15px 30px;margin:10px 5px;text-decoration:none;border-radius:5px;font-size:16px}";
  html += ".button:hover{background:#0b7dda}";
  html += ".button. orange{background:#FF9800}";
  html += ".button.orange:hover{background:#e68900}";
  html += ".info{background:#e3f2fd;padding:15px;border-radius:5px;margin:15px 0}";
  html += "</style></head><body>";
  
  html += "<div class='container'>";
  html += "<h1>📷 ESP32-CAM Stream Server</h1>";
  
  html += "<div class='status'>";
  html += "✓ Status: <strong>Online</strong>";
  html += "</div>";
  
  html += "<div class='info'>";
  html += "<strong>Camera Model:</strong> " + getCameraName() + "<br>";
  html += "<strong>IP Address:</strong> " + WiFi. localIP().toString() + "<br>";
  html += "<strong>Signal Strength:</strong> " + String(WiFi.RSSI()) + " dBm<br>";
  html += "<strong>Quality:</strong> " + String(jpegQuality) + "<br>";
  html += "<strong>Resolution:</strong> ";
  switch(frameSize) {
    case 6: html += "QVGA (320x240)"; break;
    case 7: html += "CIF (400x296)"; break;
    case 8: html += "HVGA (480x320)"; break;
    case 10: html += "VGA (640x480)"; break;
    case 11: html += "SVGA (800x600)"; break;
    case 12: html += "XGA (1024x768)"; break;
    case 13: html += "HD (1280x720)"; break;
  }
  html += "</div>";
  
  html += "<a href='/stream' class='button orange'>📹 View Stream</a>";
  html += "<a href='/settings' class='button'>⚙️ Settings</a>";
  html += "<a href='/status' class='button'>📊 Status JSON</a>";
  
  html += "</div></body></html>";
  
  server.send(200, "text/html", html);
}

// ============================================
// Setup
// ============================================
void setup() {
  Serial.begin(115200);
  Serial.println("\n\nESP32-CAM HTTP Stream Server");
  Serial.println("============================");
  
  // Load saved settings
  loadSettings();
  Serial.println("Camera Model: " + getCameraName());
  
  // Initialize camera
  if (! initCamera()) {
    Serial.println("Camera initialization failed!");
    Serial.println("Trying default AI-Thinker config...");
    currentCamera = AI_THINKER;
    if (!initCamera()) {
      Serial.println("Failed again!  Check your camera model selection.");
      ESP.restart();
    }
  }
  
  // Connect to WiFi
  Serial.print("Connecting to WiFi");
  WiFi.begin(ssid, password);
  
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 20) {
    delay(500);
    Serial.print(".");
    attempts++;
  }
  
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("\nWiFi connection failed!");
    ESP.restart();
  }
  
  Serial.println("\n✓ WiFi connected!");
  Serial.print("IP Address: ");
  Serial.println(WiFi.localIP());
  Serial.print("Stream URL: http://");
  Serial.print(WiFi.localIP());
  Serial.println("/stream");
  Serial.print("Settings: http://");
  Serial.print(WiFi.localIP());
  Serial.println("/settings");
  
  // Setup HTTP server
  server.on("/", handleRoot);
  server.on("/stream", handleStream);
  server.on("/status", handleStatus);
  server.on("/settings", handleSettings);
  
  server.begin();
  Serial.println("✓ HTTP server started");
  Serial.println("============================\n");
}

// ============================================
// Loop
// ============================================
void loop() {
  server.handleClient();
}