# DreamScaler USB Controller

🎹 USB/Serial controller pro SK6812 RGBW LED pásky s podporou **Piano Mode** pro Arturia Keylab 49 MKII a vizualizaci 60+ hudebních stupnic.

> 🌱 **Help Keep This Going**
> Your support makes a real difference. If you value my work and want to help me continue creating, please consider making a donation.  
> 💙 **Donate here:** [https://paypal.me/TomasMark](https://paypal.me/TomasMark)
> Every contribution is truly appreciated ✨

## 🚀 Quick Start

```bash
# 1. Nahraj firmware do Arduina
# Arduino IDE → Open → ds_usb_controller/ds_usb_controller.ino → Upload

# 2. Instaluj Python knihovny
cd python && pip install -r requirements.txt

# 3. Spusť Piano Mode
./piano.py /dev/ttyUSB0  # Linux
python piano.py COM3     # Windows
```

**První program:**
```python
from controller_api import LEDController

with LEDController('/dev/ttyUSB0') as led:
    led.set_all(r=0, g=0, b=0, w=100)  # Všechny LED bílé
    led.clear_all()                     # Vypnout
```

## ✨ Vlastnosti

**🎹 Piano Mode**
- Arturia Keylab 49 MKII (49 kláves → 107 LED)
- 60+ hudebních stupnic (Durová, Aiolská, Pentatonické, Blues, Exotické...)
- Vizualizace kláves s barevným rozlišením
- Automatický cleanup při Ctrl+C

**⚡ LED Controller**
- Rychlý binární protokol (~16-21 FPS)
- SK6812 RGBW (4 kanály)
- Stream/Bulk/Buffer módy
- Hardwarový gradient a globální jas
- Až 1000 LED

## 🔧 Hardware

```
Arduino Pin 6 → SK6812 Data In
Arduino GND   → SK6812 GND → Napájení GND
Napájení 5V   → SK6812 5V
```

**Potřeba:**
- Arduino Uno/Nano/Mega
- SK6812 RGBW LED pásek (ne WS2812!)
- Externí napájení 5V (107 LED = ~8.6A, 144 LED = ~11.5A)

**Konfigurace:** 107 LED, Pin 6, 115200 baud, Protocol v11

## 📦 Instalace

**Arduino:**
1. Otevři `ds_usb_controller/ds_usb_controller.ino` v Arduino IDE
2. Upload (Ctrl+U)

**Python:**
```bash
cd python
pip install -r requirements.txt

# Test
python dreamscaler.py /dev/ttyUSB0  # Základní controller
./piano.py /dev/ttyUSB0             # Piano mode
```

**Zjistit port:**
- Linux: `ls /dev/ttyUSB* /dev/ttyACM*`
- Windows: Device Manager → Ports (COM & LPT)
- Mac: `ls /dev/tty.usbserial-*`

## 🐍 Python API Základy

```python
from controller_api import LEDController

with LEDController('/dev/ttyUSB0') as led:
    # Jednotlivé LED
    led.set_pixel(0, r=255, g=0, b=0, w=0)
    
    # Hromadné
    led.set_range(0, 10, 255, 0, 0, 0)  # Rozsah
    led.set_all(0, 0, 255, 0)           # Všechny
    led.clear_all()                     # Vypnout
    
    # Stream (nejrychlejší pro animace)
    pixels = [(r, g, b, w)] * 107
    led.stream_update(pixels)
    
    # Efekty
    led.fill_gradient(0, 106, 255,0,0,0, 0,0,255,0)  # Gradient
    led.set_brightness(128)                           # 50% jas
    
    # Utility
    r, g, b = led.hsv_to_rgb(180, 1.0, 0.5)
```

## 🎹 Piano Mode

```bash
./piano.py /dev/ttyUSB0
```

**Menu:**
- `1` - Všechny klávesy (bílé=white, černé=zelená)
- `2-3` - Pouze bílé/černé klávesy
- `4` - Oktávy (barevně)
- `5` - Test animace
- `10` - **60+ stupnic** (Durová, Aiolská, Pentatonické, Blues...)
- `6` - Mapa kláves (C2-C6, 49 kláves)

**V kódu:**
```python
from arturia_keylab49_map import visualize_piano_layout, get_all_white_keys

with LEDController('/dev/ttyUSB0') as led:
    visualize_piano_layout(led)  # Zobrazí klaviaturu
```

## 💡 Příklady

**Rainbow:**
```python
with LEDController('/dev/ttyUSB0') as led:
    offset = 0
    while True:
        pixels = [(led.hsv_to_rgb((i*360/107+offset)%360, 1.0, 0.3)+(0,)) 
                  for i in range(107)]
        led.stream_update(pixels)
        offset += 3
        time.sleep(0.02)
```

**Stupnice:**
```python
from piano import load_scales, visualize_scale

scales = load_scales()
major = next(s for s in scales if s['name'] == 'Durová')

with LEDController('/dev/ttyUSB0') as led:
    visualize_scale(led, root_note=0, root_octave=4, 
                   intervals=major['intervals'], scale_name="C dur")
```

**Více příkladů:**
```bash
python dreamscaler.py /dev/ttyUSB0  # 15+ efektů (rainbow, fire, sparkle...)
```

## 🔍 Troubleshooting

| Problém | Řešení |
|---------|--------|
| Arduino se nepřipojí | Zkontroluj USB kabel, port, oprávnění (`sudo chmod 666 /dev/ttyUSB0`) |
| LED nesvítí | Externí napájení! SK6812 (ne WS2812), GND společné, Pin 6 |
| Jas nefunguje | `set_brightness()` PŘED `set_all()` |
| Port zablokovaný | `python release_port.py /dev/ttyUSB0` nebo `fuser -k /dev/ttyUSB0` |
| Nízký FPS | 16 FPS je normální @ 115200 baud. Použij `stream_update()` |

**Test připojení:**
```python
led = LEDController('/dev/ttyUSB0')
led.connect()
if led.ping():
    print(led.get_info())  # {'protocol_version': 11, 'led_count': 107, ...}
```

## 📊 Performance

| Metoda | FPS | Použití |
|--------|-----|---------|
| `stream_update()` | 16-21 | Rainbow, animace |
| `set_range()` | Okamžité | Oblasti stejné barvy |
| `fill_gradient()` | Okamžité | Gradienty |
| `set_all()` | Okamžité | Celý pásek |

**Optimalizace:**
- ✅ `stream_update()` pro plné aktualizace (ne `set_pixel()` v cyklu)
- ✅ `set_range()` pro oblasti stejné barvy
- ✅ Hardwarový `fill_gradient()` místo manuálního výpočtu
- ✅ `set_brightness()` globálně místo úpravy každé barvy

## 📁 Soubory projektu

```
DreamScaler/
├── ds_usb_controller/          # Arduino firmware (Protocol v11)
├── python/
│   ├── controller_api.py       # Python API
│   ├── dreamscaler.py          # Demo menu (15+ efektů)
│   ├── piano.py                # Piano mode (Arturia Keylab 49)
│   ├── arturia_keylab49_map.py # Mapování 49 kláves → 107 LED
│   ├── scales.json             # 60+ hudebních stupnic
│   └── release_port.py         # Uvolnění portu
└── docs/README.md              # Tato dokumentace
```

## 📚 Další dokumentace

- **[API Reference](API.md)** - Kompletní API dokumentace
- **[Protocol Specification](PROTOCOL.md)** - Detailní specifikace protokolu
- **[Hardware Guide](HARDWARE.md)** - Zapojení a výpočty
- **[Examples](EXAMPLES.md)** - Více příkladů kódu
- **[Piano Mode Guide](PIANO.md)** - Detailní průvodce Piano Mode

## 🎯 Co dál?

- **Začátečníci:** Spusťte `./piano.py /dev/ttyUSB0` a vyzkoušejte menu
- **Vývojáři:** Podívejte se na `dreamscaler.py` pro příklady API
- **Pokročilí:** Upravte `scales.json` a přidejte vlastní stupnice

## 📝 Licence

Open source projekt pro DreamScaler Piano.

## 🤝 Přispění

Pull requesty a issue reports vítány! 

**Roadmap:**
- ✅ v1.0: Arduino firmware, Python API, Piano mode, 60+ scales
- 🔨 v1.1: MIDI monitoring, Live scale visualization
- 💡 v2.0: Web interface, REST API, Animation library

---

**Made with ❤️ for DreamScaler Piano Project**
