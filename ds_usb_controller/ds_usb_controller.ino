/**
 * DreamScaler USB Controller
 * 
 * Komplexní USB/Serial controller pro ovládání SK6812 RGBW LED pásků
 * Optimalizováno pro rychlost a flexibilitu
 * 
 * Protocol: Binary communication over Serial
 * Baud rate: 115200 (konfigurovatelný)
 */

#include "SK6812.h"

// ========== KONFIGURACE ==========
// #define DEFAULT_LED_COUNT 144 
#define DEFAULT_LED_COUNT 107 
#define DEFAULT_LED_PIN 6
#define BAUD_RATE 115200
#define PROTOCOL_VERSION 11

// Velikost bufferu pro příkazy (optimalizováno pro rychlost)
#define CMD_BUFFER_SIZE 256

// ========== PROTOCOL PŘÍKAZY ==========
// Každý příkaz začína 1 bytem - command ID
enum Command {
  CMD_PING = 0x01,              // Test spojení - odpovídá PONG
  CMD_GET_INFO = 0x02,          // Vrátí info o zařízení
  CMD_RESET = 0x03,             // Reset controlleru
  
  // LED konfigurace
  CMD_SET_LED_COUNT = 0x10,     // Nastaví počet LED (2 bytes: count_hi, count_lo)
  CMD_SET_LED_PIN = 0x11,       // Nastaví output pin (1 byte: pin)
  CMD_INIT_STRIP = 0x12,        // Inicializuje LED strip s aktuálním nastavením
  
  // LED ovládání - jednotlivé LED
  CMD_SET_PIXEL_RGBW = 0x20,    // Nastaví 1 LED (2B index + 4B RGBW)
  CMD_SET_PIXEL_RGB = 0x21,     // Nastaví 1 LED RGB (2B index + 3B RGB, W=0)
  CMD_SET_PIXEL_W = 0x22,       // Nastaví 1 LED jen white (2B index + 1B W, RGB=0)
  
  // LED ovládání - hromadné operace
  CMD_SET_RANGE_RGBW = 0x30,    // Nastaví rozsah LED na stejnou barvu (2B start, 2B end, 4B RGBW)
  CMD_SET_ALL_RGBW = 0x31,      // Nastaví všechny LED na stejnou barvu (4B RGBW)
  CMD_CLEAR_ALL = 0x32,         // Vypne všechny LED
  
  // LED ovládání - buffer mód (pro plynulé animace)
  CMD_BUFFER_START = 0x40,      // Začátek bufferu (následují data)
  CMD_BUFFER_PIXEL = 0x41,      // Data v bufferu: 2B index + 4B RGBW (opakuje se)
  CMD_BUFFER_END = 0x42,        // Konec bufferu - provede sync
  
  // LED ovládání - continuous stream (nejrychlejší)
  CMD_STREAM_START = 0x50,      // Začátek streamu (2B count)
  CMD_STREAM_DATA = 0x51,       // Stream dat: N × 4B RGBW (bez indexů, sekvenčně od 0)
  CMD_STREAM_END = 0x52,        // Konec streamu + sync
  
  // LED ovládání - BULK update (optimalizováno pro rychlost)
  CMD_BULK_UPDATE = 0x55,       // Bulk update: 2B count + N×4B RGBW (bez indexů, od 0) + auto sync
  
  // Synchronizace
  CMD_SYNC = 0x60,              // Okamžitá synchronizace - odešle data na LED pásek
  
  // Efekty a utility
  CMD_FILL_GRADIENT = 0x70,     // Vyplní gradient mezi 2 barvami (2B start, 2B end, 4B RGBW1, 4B RGBW2)
  CMD_BRIGHTNESS = 0x71,        // Globální jas (1B: 0-255, aplikuje se na všechny následující operace)
  
  // Odpovědi a chyby
  RESP_OK = 0xF0,               // Operace úspěšná
  RESP_PONG = 0xF1,             // Odpověď na PING
  RESP_INFO = 0xF2,             // Odpověď s informacemi
  RESP_ERROR = 0xFE,            // Chyba (následuje 1B error code)
  RESP_UNKNOWN_CMD = 0xFF       // Neznámý příkaz
};

// Chybové kódy
enum ErrorCode {
  ERR_BUFFER_OVERFLOW = 0x01,
  ERR_INVALID_PARAM = 0x02,
  ERR_NOT_INITIALIZED = 0x03,
  ERR_OUT_OF_RANGE = 0x04,
  ERR_TIMEOUT = 0x05
};

// ========== GLOBÁLNÍ PROMĚNNÉ ==========
SK6812* ledStrip = nullptr;
uint16_t ledCount = DEFAULT_LED_COUNT;
uint8_t ledPin = DEFAULT_LED_PIN;
bool stripInitialized = false;

uint8_t globalBrightness = 255;  // Globální jas (255 = 100%)

// Buffer pro příkazy
uint8_t cmdBuffer[CMD_BUFFER_SIZE];
uint16_t cmdBufferPos = 0;

// Stream mode
bool streamMode = false;
uint16_t streamIndex = 0;
uint16_t streamCount = 0;

// ========== FORWARD DEKLARACE ==========
void initializeStrip(uint16_t count, uint8_t pin);
void processCommand(uint8_t cmd);
void cmdSetLedCount();
void cmdSetLedPin();
void cmdSetPixelRGBW();
void cmdSetPixelRGB();
void cmdSetPixelW();
void cmdSetRangeRGBW();
void cmdSetAllRGBW();
void cmdClearAll();
void cmdBufferStart();
void cmdBufferPixel();
void cmdBufferEnd();
void cmdStreamStart();
void cmdStreamData();
void cmdStreamEnd();
void cmdBulkUpdate();
void cmdFillGradient();
void cmdSetBrightness();
void applyBrightness(RGBW* color);
bool waitForBytes(uint16_t count, uint32_t timeout);
void sendResponse(uint8_t response);
void sendError(uint8_t errorCode);
void sendInfo();

// ========== SETUP ==========
void setup() {
  Serial.begin(BAUD_RATE);
  
  // Výchozí inicializace LED stripu
  initializeStrip(ledCount, ledPin);
  
  // Indikace ready - rychlé bliknutí
  if (stripInitialized) {
    RGBW flash = {0, 0, 0, 50};
    for (int i = 0; i < 3; i++) {
      ledStrip->set_rgbw(0, flash);
      ledStrip->sync();
      delay(50);
      RGBW off = {0, 0, 0, 0};
      ledStrip->set_rgbw(0, off);
      ledStrip->sync();
      delay(50);
    }
  }
}

// ========== MAIN LOOP ==========
void loop() {
  // Zpracování příchozích příkazů
  if (Serial.available() > 0) {
    uint8_t cmd = Serial.read();
    processCommand(cmd);
  }
}

// ========== INICIALIZACE ==========
void initializeStrip(uint16_t count, uint8_t pin) {
  // Uvolnění starého stripu pokud existuje
  if (ledStrip != nullptr) {
    delete ledStrip;
    ledStrip = nullptr;
  }
  
  // Vytvoření nového stripu
  ledCount = count;
  ledPin = pin;
  ledStrip = new SK6812(ledCount);
  ledStrip->set_output(ledPin);
  
  // Vymazání všech LED
  RGBW off = {0, 0, 0, 0};
  for (uint16_t i = 0; i < ledCount; i++) {
    ledStrip->set_rgbw(i, off);
  }
  ledStrip->sync();
  
  stripInitialized = true;
}

// ========== ZPRACOVÁNÍ PŘÍKAZŮ ==========
void processCommand(uint8_t cmd) {
  switch (cmd) {
    // ===== SYSTÉMOVÉ PŘÍKAZY =====
    case CMD_PING:
      sendResponse(RESP_PONG);
      break;
      
    case CMD_GET_INFO:
      sendInfo();
      break;
      
    case CMD_RESET:
      // Soft reset - reinicializace
      initializeStrip(DEFAULT_LED_COUNT, DEFAULT_LED_PIN);
      globalBrightness = 255;
      sendResponse(RESP_OK);
      break;
    
    // ===== KONFIGURACE =====
    case CMD_SET_LED_COUNT:
      cmdSetLedCount();
      break;
      
    case CMD_SET_LED_PIN:
      cmdSetLedPin();
      break;
      
    case CMD_INIT_STRIP:
      initializeStrip(ledCount, ledPin);
      sendResponse(RESP_OK);
      break;
    
    // ===== JEDNOTLIVÉ LED =====
    case CMD_SET_PIXEL_RGBW:
      cmdSetPixelRGBW();
      break;
      
    case CMD_SET_PIXEL_RGB:
      cmdSetPixelRGB();
      break;
      
    case CMD_SET_PIXEL_W:
      cmdSetPixelW();
      break;
    
    // ===== HROMADNÉ OPERACE =====
    case CMD_SET_RANGE_RGBW:
      cmdSetRangeRGBW();
      break;
      
    case CMD_SET_ALL_RGBW:
      cmdSetAllRGBW();
      break;
      
    case CMD_CLEAR_ALL:
      cmdClearAll();
      break;
    
    // ===== BUFFER MÓD =====
    case CMD_BUFFER_START:
      cmdBufferStart();
      break;
      
    case CMD_BUFFER_PIXEL:
      cmdBufferPixel();
      break;
      
    case CMD_BUFFER_END:
      cmdBufferEnd();
      break;
    
    // ===== STREAM MÓD =====
    case CMD_STREAM_START:
      cmdStreamStart();
      break;
      
    case CMD_STREAM_DATA:
      cmdStreamData();
      break;
      
    case CMD_STREAM_END:
      cmdStreamEnd();
      break;
    
    // ===== BULK UPDATE (RYCHLÉ) =====
    case CMD_BULK_UPDATE:
      cmdBulkUpdate();
      break;
    
    // ===== SYNCHRONIZACE =====
    case CMD_SYNC:
      if (stripInitialized) {
        ledStrip->sync();
        sendResponse(RESP_OK);
      } else {
        sendError(ERR_NOT_INITIALIZED);
      }
      break;
    
    // ===== EFEKTY =====
    case CMD_FILL_GRADIENT:
      cmdFillGradient();
      break;
      
    case CMD_BRIGHTNESS:
      cmdSetBrightness();
      break;
    
    default:
      sendResponse(RESP_UNKNOWN_CMD);
      break;
  }
}

// ========== IMPLEMENTACE PŘÍKAZŮ ==========

void cmdSetLedCount() {
  if (waitForBytes(2, 1000)) {
    uint16_t count = (Serial.read() << 8) | Serial.read();
    if (count > 0 && count <= 1000) {  // Rozumný limit
      ledCount = count;
      sendResponse(RESP_OK);
    } else {
      sendError(ERR_INVALID_PARAM);
    }
  }
}

void cmdSetLedPin() {
  if (waitForBytes(1, 1000)) {
    uint8_t pin = Serial.read();
    if (pin < 20) {  // Rozumný limit pro Arduino piny
      ledPin = pin;
      sendResponse(RESP_OK);
    } else {
      sendError(ERR_INVALID_PARAM);
    }
  }
}

void cmdSetPixelRGBW() {
  if (!stripInitialized) {
    sendError(ERR_NOT_INITIALIZED);
    return;
  }
  
  if (waitForBytes(6, 1000)) {  // 2B index + 4B RGBW
    uint16_t index = (Serial.read() << 8) | Serial.read();
    RGBW color;
    color.r = Serial.read();
    color.g = Serial.read();
    color.b = Serial.read();
    color.w = Serial.read();
    
    // Aplikace brightness
    applyBrightness(&color);
    
    if (index < ledCount) {
      ledStrip->set_rgbw(index, color);
      ledStrip->sync();
      sendResponse(RESP_OK);
    } else {
      sendError(ERR_OUT_OF_RANGE);
    }
  }
}

void cmdSetPixelRGB() {
  if (!stripInitialized) {
    sendError(ERR_NOT_INITIALIZED);
    return;
  }
  
  if (waitForBytes(5, 1000)) {  // 2B index + 3B RGB
    uint16_t index = (Serial.read() << 8) | Serial.read();
    RGBW color;
    color.r = Serial.read();
    color.g = Serial.read();
    color.b = Serial.read();
    color.w = 0;
    
    applyBrightness(&color);
    
    if (index < ledCount) {
      ledStrip->set_rgbw(index, color);
      ledStrip->sync();
      sendResponse(RESP_OK);
    } else {
      sendError(ERR_OUT_OF_RANGE);
    }
  }
}

void cmdSetPixelW() {
  if (!stripInitialized) {
    sendError(ERR_NOT_INITIALIZED);
    return;
  }
  
  if (waitForBytes(3, 1000)) {  // 2B index + 1B W
    uint16_t index = (Serial.read() << 8) | Serial.read();
    RGBW color = {0, 0, 0, 0};
    color.w = Serial.read();
    
    applyBrightness(&color);
    
    if (index < ledCount) {
      ledStrip->set_rgbw(index, color);
      ledStrip->sync();
      sendResponse(RESP_OK);
    } else {
      sendError(ERR_OUT_OF_RANGE);
    }
  }
}

void cmdSetRangeRGBW() {
  if (!stripInitialized) {
    sendError(ERR_NOT_INITIALIZED);
    return;
  }
  
  if (waitForBytes(8, 1000)) {  // 2B start + 2B end + 4B RGBW
    uint16_t start = (Serial.read() << 8) | Serial.read();
    uint16_t end = (Serial.read() << 8) | Serial.read();
    RGBW color;
    color.r = Serial.read();
    color.g = Serial.read();
    color.b = Serial.read();
    color.w = Serial.read();
    
    applyBrightness(&color);
    
    if (start < ledCount && end < ledCount && start <= end) {
      for (uint16_t i = start; i <= end; i++) {
        ledStrip->set_rgbw(i, color);
      }
      ledStrip->sync();
      sendResponse(RESP_OK);
    } else {
      sendError(ERR_OUT_OF_RANGE);
    }
  }
}

void cmdSetAllRGBW() {
  if (!stripInitialized) {
    sendError(ERR_NOT_INITIALIZED);
    return;
  }
  
  if (waitForBytes(4, 1000)) {  // 4B RGBW
    RGBW color;
    color.r = Serial.read();
    color.g = Serial.read();
    color.b = Serial.read();
    color.w = Serial.read();
    
    applyBrightness(&color);
    
    for (uint16_t i = 0; i < ledCount; i++) {
      ledStrip->set_rgbw(i, color);
    }
    ledStrip->sync();
    sendResponse(RESP_OK);
  }
}

void cmdClearAll() {
  if (!stripInitialized) {
    sendError(ERR_NOT_INITIALIZED);
    return;
  }
  
  RGBW off = {0, 0, 0, 0};
  for (uint16_t i = 0; i < ledCount; i++) {
    ledStrip->set_rgbw(i, off);
  }
  ledStrip->sync();
  sendResponse(RESP_OK);
}

void cmdBufferStart() {
  cmdBufferPos = 0;
  sendResponse(RESP_OK);
}

void cmdBufferPixel() {
  if (!stripInitialized) {
    sendError(ERR_NOT_INITIALIZED);
    return;
  }
  
  if (waitForBytes(6, 1000)) {  // 2B index + 4B RGBW
    uint16_t index = (Serial.read() << 8) | Serial.read();
    RGBW color;
    color.r = Serial.read();
    color.g = Serial.read();
    color.b = Serial.read();
    color.w = Serial.read();
    
    applyBrightness(&color);
    
    if (index < ledCount) {
      ledStrip->set_rgbw(index, color);
      sendResponse(RESP_OK);
    } else {
      sendError(ERR_OUT_OF_RANGE);
    }
  }
}

void cmdBufferEnd() {
  if (!stripInitialized) {
    sendError(ERR_NOT_INITIALIZED);
    return;
  }
  
  ledStrip->sync();
  cmdBufferPos = 0;
  sendResponse(RESP_OK);
}

void cmdStreamStart() {
  if (!stripInitialized) {
    sendError(ERR_NOT_INITIALIZED);
    return;
  }
  
  if (waitForBytes(2, 1000)) {  // 2B count
    streamCount = (Serial.read() << 8) | Serial.read();
    streamIndex = 0;
    streamMode = true;
    sendResponse(RESP_OK);
  }
}

void cmdStreamData() {
  if (!stripInitialized || !streamMode) {
    sendError(ERR_NOT_INITIALIZED);
    return;
  }
  
  // Čte RGBW data sekvenčně
  if (waitForBytes(4, 1000)) {  // 4B RGBW
    RGBW color;
    color.r = Serial.read();
    color.g = Serial.read();
    color.b = Serial.read();
    color.w = Serial.read();
    
    applyBrightness(&color);
    
    if (streamIndex < ledCount && streamIndex < streamCount) {
      ledStrip->set_rgbw(streamIndex, color);
      streamIndex++;
      sendResponse(RESP_OK);
    } else {
      sendError(ERR_OUT_OF_RANGE);
    }
  }
}

void cmdStreamEnd() {
  if (!stripInitialized) {
    sendError(ERR_NOT_INITIALIZED);
    return;
  }
  
  ledStrip->sync();
  streamMode = false;
  streamIndex = 0;
  streamCount = 0;
  sendResponse(RESP_OK);
}

void cmdBulkUpdate() {
  if (!stripInitialized) {
    sendError(ERR_NOT_INITIALIZED);
    return;
  }
  
  // Přečíst počet LED (2 bytes)
  if (waitForBytes(2, 1000)) {
    uint16_t count = (Serial.read() << 8) | Serial.read();
    
    if (count > ledCount) {
      sendError(ERR_OUT_OF_RANGE);
      return;
    }
    
    // Poslat OK že jsme připraveni
    sendResponse(RESP_OK);
    
    // Přečíst všechna RGBW data postupně ale efektivně
    // Nebudeme čekat na všechna data najednou, ale přečteme je jak přicházejí
    uint32_t timeout = 1000;  // 1 sekunda na všechna data
    uint32_t startTime = millis();
    
    for (uint16_t i = 0; i < count; i++) {
      // Počkat na 4 byty pro tento pixel
      while (Serial.available() < 4) {
        if (millis() - startTime > timeout) {
          sendError(ERR_TIMEOUT);
          return;
        }
      }
      
      RGBW color;
      color.r = Serial.read();
      color.g = Serial.read();
      color.b = Serial.read();
      color.w = Serial.read();
      
      applyBrightness(&color);
      ledStrip->set_rgbw(i, color);
      
      // Reset timeout pro každý pixel - pokud data tečou, jsme OK
      startTime = millis();
    }
    
    // Provést sync
    ledStrip->sync();
    
    // Poslat finální OK
    sendResponse(RESP_OK);
  }
}

void cmdFillGradient() {
  if (!stripInitialized) {
    sendError(ERR_NOT_INITIALIZED);
    return;
  }
  
  if (waitForBytes(12, 1000)) {  // 2B start + 2B end + 4B RGBW1 + 4B RGBW2
    uint16_t start = (Serial.read() << 8) | Serial.read();
    uint16_t end = (Serial.read() << 8) | Serial.read();
    
    RGBW color1, color2;
    color1.r = Serial.read();
    color1.g = Serial.read();
    color1.b = Serial.read();
    color1.w = Serial.read();
    
    color2.r = Serial.read();
    color2.g = Serial.read();
    color2.b = Serial.read();
    color2.w = Serial.read();
    
    if (start < ledCount && end < ledCount && start <= end) {
      uint16_t steps = end - start;
      for (uint16_t i = 0; i <= steps; i++) {
        RGBW color;
        if (steps > 0) {
          color.r = map(i, 0, steps, color1.r, color2.r);
          color.g = map(i, 0, steps, color1.g, color2.g);
          color.b = map(i, 0, steps, color1.b, color2.b);
          color.w = map(i, 0, steps, color1.w, color2.w);
        } else {
          color = color1;
        }
        
        applyBrightness(&color);
        ledStrip->set_rgbw(start + i, color);
      }
      ledStrip->sync();
      sendResponse(RESP_OK);
    } else {
      sendError(ERR_OUT_OF_RANGE);
    }
  }
}

void cmdSetBrightness() {
  if (waitForBytes(1, 1000)) {
    globalBrightness = Serial.read();
    sendResponse(RESP_OK);
  }
}

// ========== UTILITY FUNKCE ==========

void applyBrightness(RGBW* color) {
  if (globalBrightness < 255) {
    color->r = (color->r * globalBrightness) >> 8;
    color->g = (color->g * globalBrightness) >> 8;
    color->b = (color->b * globalBrightness) >> 8;
    color->w = (color->w * globalBrightness) >> 8;
  }
}

bool waitForBytes(uint16_t count, uint32_t timeout = 1000) {
  uint32_t startTime = millis();
  while (Serial.available() < count) {
    if (millis() - startTime > timeout) {
      sendError(ERR_TIMEOUT);
      return false;
    }
  }
  return true;
}

void sendResponse(uint8_t response) {
  Serial.write(response);
}

void sendError(uint8_t errorCode) {
  Serial.write(RESP_ERROR);
  Serial.write(errorCode);
}

void sendInfo() {
  Serial.write(RESP_INFO);
  Serial.write(PROTOCOL_VERSION);
  Serial.write((ledCount >> 8) & 0xFF);  // LED count high byte
  Serial.write(ledCount & 0xFF);         // LED count low byte
  Serial.write(ledPin);
  Serial.write(stripInitialized ? 1 : 0);
  Serial.write(globalBrightness);
}
