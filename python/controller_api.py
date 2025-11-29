#!/usr/bin/env python3
"""
DreamScaler USB Controller API
Python knihovna pro komunikaci s Arduino USB Controllerem pro SK6812 LED pásky

Použití:
    from controller_api import LEDController
    
    controller = LEDController('/dev/ttyACM0')  # nebo 'COM3' na Windows
    controller.connect()
    
    # Nastavení jednotlivé LED
    controller.set_pixel(0, r=255, g=0, b=0, w=0)
    controller.sync()
    
    # Vymazání všech LED
    controller.clear_all()
    
    controller.disconnect()
"""

import serial
import time
import struct
from typing import Tuple, List, Optional
from enum import IntEnum


class Command(IntEnum):
    """Protokolové příkazy"""
    # Systémové
    PING = 0x01
    GET_INFO = 0x02
    RESET = 0x03
    
    # LED konfigurace
    SET_LED_COUNT = 0x10
    SET_LED_PIN = 0x11
    INIT_STRIP = 0x12
    
    # LED ovládání - jednotlivé
    SET_PIXEL_RGBW = 0x20
    SET_PIXEL_RGB = 0x21
    SET_PIXEL_W = 0x22
    
    # LED ovládání - hromadné
    SET_RANGE_RGBW = 0x30
    SET_ALL_RGBW = 0x31
    CLEAR_ALL = 0x32
    
    # Buffer mód
    BUFFER_START = 0x40
    BUFFER_PIXEL = 0x41
    BUFFER_END = 0x42
    
    # Stream mód
    STREAM_START = 0x50
    STREAM_DATA = 0x51
    STREAM_END = 0x52
    
    # Bulk update (optimalizováno)
    BULK_UPDATE = 0x55
    
    # Synchronizace
    SYNC = 0x60
    
    # Efekty
    FILL_GRADIENT = 0x70
    BRIGHTNESS = 0x71


class Response(IntEnum):
    """Odpovědi z controlleru"""
    OK = 0xF0
    PONG = 0xF1
    INFO = 0xF2
    ERROR = 0xFE
    UNKNOWN_CMD = 0xFF


class ErrorCode(IntEnum):
    """Chybové kódy"""
    BUFFER_OVERFLOW = 0x01
    INVALID_PARAM = 0x02
    NOT_INITIALIZED = 0x03
    OUT_OF_RANGE = 0x04
    TIMEOUT = 0x05


class LEDControllerError(Exception):
    """Výjimka pro chyby controlleru"""
    pass


class LEDController:
    """API pro ovládání SK6812 LED pásku přes USB"""
    
    def __init__(self, port: str, baud_rate: int = 115200, timeout: float = 2.0):
        """
        Inicializace controlleru
        
        Args:
            port: Sériový port (např. '/dev/ttyACM0' nebo 'COM3')
            baud_rate: Rychlost komunikace (výchozí 115200)
            timeout: Timeout pro čtení v sekundách
        """
        self.port = port
        self.baud_rate = baud_rate
        self.timeout = timeout
        self.serial: Optional[serial.Serial] = None
        #self.led_count = 144  # Výchozí hodnota
        self.led_count = 107  # Arturia KeyLab 49 MKII
        self.led_pin = 6
        self.is_initialized = False
    
    def connect(self) -> bool:
        """
        Připojení k controlleru
        
        Returns:
            True pokud úspěšné
        """
        try:
            self.serial = serial.Serial(
                self.port,
                self.baud_rate,
                timeout=self.timeout
            )
            # Počkat na inicializaci Arduina
            time.sleep(2)
            
            # Vymazat veškerá data z bufferu (Arduino bootloader, init messages)
            self.serial.reset_input_buffer()
            self.serial.reset_output_buffer()
            
            # Test spojení
            if self.ping():
                info = self.get_info()
                if info:
                    self.led_count = info['led_count']
                    self.led_pin = info['led_pin']
                    self.is_initialized = info['initialized']
                    print(f"Připojeno k controlleru: {info}")
                    return True
            
            return False
        except Exception as e:
            print(f"Chyba při připojování: {e}")
            return False
    
    def disconnect(self):
        """
        Odpojení od controlleru s agresivním zavřením portu
        
        DŮLEŽITÉ: Implementuje "baudrate trick" pro správné uvolnění portu:
        Po ukončení programu (včetně Ctrl+C) může port zůstat zablokovaný
        v operačním systému. Řešení je znovu otevřít port s JINÝM baudrate
        a hned ho zavřít - to resetuje stav portu v OS a uvolní ho.
        
        Bez tohoto kroku by po Ctrl+C port zůstal zablokovaný a bylo by
        nutné používat release_port.py nebo fyzicky odpojit USB.
        """
        if self.serial:
            port_name = self.port  # Uložit jméno portu
            
            try:
                if self.serial.is_open:
                    # Pokus o graceful close
                    try:
                        self.serial.reset_input_buffer()
                        self.serial.reset_output_buffer()
                    except:
                        pass
                    
                    # Nastavit DTR a RTS na False (může pomoci s uvolněním)
                    try:
                        self.serial.dtr = False
                        self.serial.rts = False
                    except:
                        pass
                    
                    # Počkat chvíli
                    time.sleep(0.1)
                    
                    # Zavřít port
                    try:
                        self.serial.close()
                    except:
                        pass
                            
            except Exception as e:
                pass  # Ignorovat chyby
            finally:
                self.serial = None
                self.is_initialized = False
            
            # ============================================================
            # BAUDRATE TRICK - KLÍČOVÝ KROK PRO UVOLNĚNÍ PORTU
            # ============================================================
            # Když port zamrzne s baudrate 115200, otevření s jiným baudrate
            # (9600) a okamžité zavření resetuje stav portu v OS Windows.
            # Bez tohoto kroku zůstává port zablokovaný po Ctrl+C!
            try:
                time.sleep(0.1)
                temp_serial = serial.Serial(port_name, baudrate=9600, timeout=0.1)
                temp_serial.reset_input_buffer()
                temp_serial.reset_output_buffer()
                temp_serial.dtr = False
                temp_serial.rts = False
                time.sleep(0.1)
                temp_serial.close()
                time.sleep(0.2)  # Důležité počkat aby OS uvolnil port
            except:
                pass  # Pokud se to nepovede, nevadí
    
    def _send_command(self, cmd: int, data: bytes = b'') -> bytes:
        """
        Odeslání příkazu a čekání na odpověď
        
        Args:
            cmd: Command byte
            data: Dodatečná data
            
        Returns:
            Odpověď z controlleru
        """
        if not self.serial or not self.serial.is_open:
            raise LEDControllerError("Controller není připojen")
        
        # Vymazání starých dat z bufferu
        self.serial.reset_input_buffer()
        
        # Odeslání příkazu
        self.serial.write(bytes([cmd]) + data)
        self.serial.flush()
        
        # Čtení odpovědi
        response = self.serial.read(1)
        if len(response) == 0:
            raise LEDControllerError("Timeout - žádná odpověď")
        
        resp_code = response[0]
        
        if resp_code == Response.ERROR:
            error_code = self.serial.read(1)
            if len(error_code) > 0:
                raise LEDControllerError(f"Chyba controlleru: {ErrorCode(error_code[0]).name}")
            else:
                raise LEDControllerError("Neznámá chyba controlleru")
        
        return bytes([resp_code])
    
    def _wait_for_ok(self):
        """Čekání na OK odpověď"""
        resp = self._send_command(0, b'')  # Dummy, již jsme poslali příkaz
        # Ve skutečnosti odpověď dostáváme v _send_command
    
    # ========== SYSTÉMOVÉ PŘÍKAZY ==========
    
    def ping(self) -> bool:
        """Test spojení"""
        try:
            resp = self._send_command(Command.PING)
            return resp[0] == Response.PONG
        except:
            return False
    
    def get_info(self) -> Optional[dict]:
        """
        Získání informací o controlleru
        
        Returns:
            Dict s informacemi nebo None
        """
        try:
            # Vymazání bufferu
            self.serial.reset_input_buffer()
            
            # Odeslání příkazu
            self.serial.write(bytes([Command.GET_INFO]))
            self.serial.flush()
            
            # Čtení odpovědi
            resp = self.serial.read(1)
            
            if len(resp) > 0 and resp[0] == Response.INFO:
                data = self.serial.read(6)  # Protocol version + 5 bytes
                if len(data) == 6:
                    return {
                        'protocol_version': data[0],
                        'led_count': (data[1] << 8) | data[2],
                        'led_pin': data[3],
                        'initialized': bool(data[4]),
                        'brightness': data[5]
                    }
            return None
        except Exception as e:
            print(f"Chyba při získávání info: {e}")
            return None
    
    def reset(self):
        """Reset controlleru"""
        self._send_command(Command.RESET)
    
    # ========== KONFIGURACE ==========
    
    def set_led_count(self, count: int):
        """Nastavení počtu LED"""
        data = struct.pack('>H', count)  # Big-endian uint16
        self._send_command(Command.SET_LED_COUNT, data)
        self.led_count = count
    
    def set_led_pin(self, pin: int):
        """Nastavení output pinu"""
        data = bytes([pin])
        self._send_command(Command.SET_LED_PIN, data)
        self.led_pin = pin
    
    def init_strip(self):
        """Inicializace LED stripu s aktuálním nastavením"""
        self._send_command(Command.INIT_STRIP)
        self.is_initialized = True
    
    # ========== OVLÁDÁNÍ JEDNOTLIVÝCH LED ==========
    
    def set_pixel(self, index: int, r: int = 0, g: int = 0, b: int = 0, w: int = 0):
        """
        Nastavení barvy jednotlivé LED (RGBW)
        
        Args:
            index: Index LED (0-based)
            r, g, b, w: Hodnoty barev 0-255
        """
        data = struct.pack('>HBBBB', index, r, g, b, w)
        self._send_command(Command.SET_PIXEL_RGBW, data)
    
    def set_pixel_rgb(self, index: int, r: int, g: int, b: int):
        """Nastavení LED s RGB (W=0)"""
        data = struct.pack('>HBBB', index, r, g, b)
        self._send_command(Command.SET_PIXEL_RGB, data)
    
    def set_pixel_white(self, index: int, w: int):
        """Nastavení LED jen s White kanálem"""
        data = struct.pack('>HB', index, w)
        self._send_command(Command.SET_PIXEL_W, data)
    
    # ========== HROMADNÉ OPERACE ==========
    
    def set_range(self, start: int, end: int, r: int = 0, g: int = 0, b: int = 0, w: int = 0):
        """
        Nastavení rozsahu LED na stejnou barvu
        
        Args:
            start: Počáteční index
            end: Koncový index (včetně)
            r, g, b, w: Hodnoty barev 0-255
        """
        data = struct.pack('>HHBBBB', start, end, r, g, b, w)
        self._send_command(Command.SET_RANGE_RGBW, data)
    
    def set_all(self, r: int = 0, g: int = 0, b: int = 0, w: int = 0):
        """Nastavení všech LED na stejnou barvu"""
        data = struct.pack('BBBB', r, g, b, w)
        self._send_command(Command.SET_ALL_RGBW, data)
    
    def clear_all(self):
        """Vypnutí všech LED"""
        self._send_command(Command.CLEAR_ALL)
    
    # ========== BUFFER MÓD ==========
    
    def buffer_begin(self):
        """Začátek bufferu"""
        self._send_command(Command.BUFFER_START)
    
    def buffer_set_pixel(self, index: int, r: int = 0, g: int = 0, b: int = 0, w: int = 0):
        """Nastavení LED v buffer módu"""
        data = struct.pack('>HBBBB', index, r, g, b, w)
        self._send_command(Command.BUFFER_PIXEL, data)
    
    def buffer_end(self):
        """Konec bufferu a synchronizace"""
        self._send_command(Command.BUFFER_END)
    
    def buffer_update(self, pixels: List[Tuple[int, int, int, int, int]]):
        """
        Hromadná aktualizace LED pomocí bufferu
        
        Args:
            pixels: List tuplů (index, r, g, b, w)
        """
        self.buffer_begin()
        for pixel in pixels:
            self.buffer_set_pixel(*pixel)
        self.buffer_end()
    
    # ========== STREAM MÓD (NEJRYCHLEJŠÍ) ==========
    
    def stream_begin(self, count: int):
        """Začátek streamu"""
        data = struct.pack('>H', count)
        self._send_command(Command.STREAM_START, data)
    
    def stream_pixel(self, r: int, g: int, b: int, w: int):
        """Odeslání jedné LED v stream módu (sekvenčně)"""
        data = struct.pack('BBBB', r, g, b, w)
        self._send_command(Command.STREAM_DATA, data)
    
    def stream_end(self):
        """Konec streamu a synchronizace"""
        self._send_command(Command.STREAM_END)
    
    def stream_update(self, pixels: List[Tuple[int, int, int, int]], wait_response: bool = False):
        """
        Nejrychlejší způsob aktualizace všech LED
        Používá BULK_UPDATE příkaz pro minimální overhead
        
        Args:
            pixels: List tuplů (r, g, b, w) v pořadí od indexu 0
            wait_response: Ignorováno (pro kompatibilitu)
        """
        if not self.serial or not self.serial.is_open:
            raise LEDControllerError("Controller není připojen")
        
        # Vymazat buffer
        self.serial.reset_input_buffer()
        
        # Sestavit BULK_UPDATE packet: CMD + count(2B) + všechna RGBW data
        packet = bytearray()
        packet.append(Command.BULK_UPDATE)
        packet.extend(struct.pack('>H', len(pixels)))  # Count
        
        # Poslat příkaz a count
        self.serial.write(packet)
        self.serial.flush()
        
        # Čekat na OK že je připraven (delší timeout pro velké množství dat)
        self.serial.timeout = 5.0  # 5 sekund
        resp = self.serial.read(1)
        if len(resp) == 0 or resp[0] != Response.OK:
            raise LEDControllerError("Arduino není připraveno pro bulk update")
        
        # Poslat všechna RGBW data najednou
        data = bytearray()
        for pixel in pixels:
            data.extend(struct.pack('BBBB', *pixel))
        
        self.serial.write(data)
        self.serial.flush()
        
        # Čekat na finální OK (po sync) - delší timeout
        self.serial.timeout = 5.0  # 5 sekund pro příjem a sync
        resp = self.serial.read(1)
        
        # Resetovat timeout
        self.serial.timeout = self.timeout
        
        if len(resp) == 0:
            raise LEDControllerError("Bulk update timeout - žádná odpověď")
        
        if resp[0] == Response.ERROR:
            # Přečíst error kód
            error_code = self.serial.read(1)
            if len(error_code) > 0:
                error_names = {0x01: 'BUFFER_OVERFLOW', 0x02: 'INVALID_PARAM', 
                              0x03: 'NOT_INITIALIZED', 0x04: 'OUT_OF_RANGE', 0x05: 'TIMEOUT'}
                error_name = error_names.get(error_code[0], f'UNKNOWN({error_code[0]:02x})')
                raise LEDControllerError(f"Arduino error: {error_name}")
            else:
                raise LEDControllerError("Arduino error (no code)")
        
        if resp[0] != Response.OK:
            raise LEDControllerError(f"Bulk update unexpected response: {resp[0]:02x}")
    
    # ========== SYNCHRONIZACE ==========
    
    def sync(self):
        """Okamžitá synchronizace - odeslání dat na LED pásek"""
        self._send_command(Command.SYNC)
    
    # ========== EFEKTY ==========
    
    def fill_gradient(self, start: int, end: int, 
                     r1: int, g1: int, b1: int, w1: int,
                     r2: int, g2: int, b2: int, w2: int):
        """
        Vyplnění gradientu mezi dvěma barvami
        
        Args:
            start, end: Rozsah LED
            r1, g1, b1, w1: Počáteční barva
            r2, g2, b2, w2: Koncová barva
        """
        data = struct.pack('>HHBBBBBBBB', start, end, r1, g1, b1, w1, r2, g2, b2, w2)
        self._send_command(Command.FILL_GRADIENT, data)
    
    def set_brightness(self, brightness: int):
        """
        Nastavení globálního jasu
        
        Args:
            brightness: 0-255 (0=vypnuto, 255=plný jas)
        """
        data = bytes([brightness])
        self._send_command(Command.BRIGHTNESS, data)
    
    # ========== UTILITY FUNKCE ==========
    
    def rgb_to_rgbw(self, r: int, g: int, b: int) -> Tuple[int, int, int, int]:
        """
        Konverze RGB na RGBW (extrakce bílé složky)
        
        Args:
            r, g, b: RGB hodnoty 0-255
            
        Returns:
            Tuple (r, g, b, w)
        """
        # Jednoduchá metoda - white = minimum z RGB
        w = min(r, g, b)
        return (r - w, g - w, b - w, w)
    
    def hsv_to_rgb(self, h: float, s: float, v: float) -> Tuple[int, int, int]:
        """
        Konverze HSV na RGB
        
        Args:
            h: Hue 0-360
            s: Saturation 0-1
            v: Value 0-1
            
        Returns:
            Tuple (r, g, b) 0-255
        """
        import colorsys
        r, g, b = colorsys.hsv_to_rgb(h/360, s, v)
        return (int(r * 255), int(g * 255), int(b * 255))
    
    def __enter__(self):
        """Context manager support"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager cleanup"""
        try:
            # Vypnout všechny LED před odpojením
            if self.serial and self.serial.is_open:
                try:
                    self.clear_all()
                except:
                    pass  # Ignorovat chyby při závěrečném čištění
        except:
            pass
        finally:
            self.disconnect()
        return False  # Nepotlačovat výjimky


# ========== PŘÍKLADY POUŽITÍ ==========

def example_basic():
    """Základní příklad použití"""
    with LEDController('/dev/ttyACM0') as controller:
        # Červená LED na indexu 0
        controller.set_pixel(0, r=255, g=0, b=0, w=0)
        controller.sync()
        time.sleep(1)
        
        # Zelená LED na indexu 1
        controller.set_pixel(1, r=0, g=255, b=0, w=0)
        controller.sync()
        time.sleep(1)
        
        # Bílá všude
        controller.set_all(r=0, g=0, b=0, w=50)
        time.sleep(1)
        
        # Vypnout
        controller.clear_all()


def example_gradient():
    """Příklad gradientu"""
    with LEDController('/dev/ttyACM0') as controller:
        # Gradient od červené k modré
        controller.fill_gradient(
            0, 143,
            255, 0, 0, 0,    # Červená
            0, 0, 255, 0     # Modrá
        )
        controller.sync()


def example_animation():
    """Příklad animace"""
    with LEDController('/dev/ttyACM0') as controller:
        # Rainbow animace
        for offset in range(360):
            pixels = []
            for i in range(144):
                hue = (i * 360 / 144 + offset) % 360
                r, g, b = controller.hsv_to_rgb(hue, 1.0, 0.5)
                pixels.append((r, g, b, 0))
            
            controller.stream_update(pixels)
            time.sleep(0.02)


if __name__ == '__main__':
    print("DreamScaler USB Controller API")
    print("Pro použití importuj: from controller_api import LEDController")
    print("\nSpouštím testovací animaci...")
    
    # Spustit příklad
    # example_basic()
    # example_gradient()
    # example_animation()
