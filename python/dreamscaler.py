#!/usr/bin/env python3
"""
DreamScaler USB Controller - Main Tool
Sjednocené rozhraní pro testování a ukázky efektů
"""

import sys
import time
import math
import random
from controller_api import LEDController, LEDControllerError
from arturia_keylab49_map import PIANO_KEY_MAP, WHITE_KEY_COLOR, BLACK_KEY_COLOR, visualize_piano_layout


# ============================================================
# TESTOVACÍ FUNKCE
# ============================================================

def test_ping(controller):
    """Test PING"""
    print("\n[TEST] Ping...")
    if controller.ping():
        print("✓ PONG - Controller odpovídá")
        return True
    else:
        print("✗ Žádná odpověď")
        return False


def test_info(controller):
    """Zobrazení informací"""
    print("\n[TEST] Získávání informací...")
    info = controller.get_info()
    if info:
        print(f"✓ Informace získány:")
        print(f"  - Verze protokolu: {info['protocol_version']}")
        print(f"  - Počet LED: {info['led_count']}")
        print(f"  - Output pin: {info['led_pin']}")
        print(f"  - Inicializováno: {info['initialized']}")
    else:
        print("✗ Nepodařilo se získat informace")


def test_single_leds(controller):
    """Test jednotlivých LED"""
    print("\n[TEST] Test jednotlivých LED...")
    colors = [
        (255, 0, 0, 0, "Červená"),
        (0, 255, 0, 0, "Zelená"),
        (0, 0, 255, 0, "Modrá"),
        (0, 0, 0, 100, "Bílá")
    ]
    
    for r, g, b, w, name in colors:
        print(f"  LED 0: {name}")
        controller.set_pixel(0, r, g, b, w)
        time.sleep(0.5)
    
    controller.clear_all()
    print("✓ Test dokončen")


# ============================================================
# PŘÍKLADY EFEKTŮ
# ============================================================

def example_basic(controller):
    """Základní ovládání LED"""
    print("\n=== Základní ovládání ===")
    
    print("Červená LED 0")
    controller.set_pixel(0, r=255, g=0, b=0, w=0)
    time.sleep(1)
    
    print("Zelená LED 1")
    controller.set_pixel(1, r=0, g=255, b=0, w=0)
    time.sleep(1)
    
    print("Modrá LED 2")
    controller.set_pixel(2, r=0, g=0, b=255, w=0)
    time.sleep(1)
    
    print("Bílá LED 3")
    controller.set_pixel(3, r=0, g=0, b=0, w=255)
    time.sleep(2)  # Delší pauza před clear
    
    controller.clear_all()


def example_range(controller):
    """Rozsahy LED"""
    print("\n=== Rozsahy LED ===")
    
    third = 144 // 3
    
    print("První třetina: červená")
    controller.set_range(0, third-1, r=255, g=0, b=0, w=0)
    time.sleep(1)
    
    print("Druhá třetina: zelená")
    controller.set_range(third, 2*third-1, r=0, g=255, b=0, w=0)
    time.sleep(1)
    
    print("Třetí třetina: modrá")
    controller.set_range(2*third, 143, r=0, g=0, b=255, w=0)
    time.sleep(2)
    
    controller.clear_all()


def example_gradient(controller):
    """Gradienty"""
    print("\n=== Gradienty ===")
    
    gradients = [
        ("Červená → Modrá", 255, 0, 0, 0, 0, 0, 255, 0),
        ("Zelená → Žlutá", 0, 255, 0, 0, 255, 255, 0, 0),
        ("Modrá → Bílá", 0, 0, 255, 0, 0, 0, 0, 255),
    ]
    
    for name, r1, g1, b1, w1, r2, g2, b2, w2 in gradients:
        print(f"  {name}")
        controller.fill_gradient(0, 143, r1, g1, b1, w1, r2, g2, b2, w2)
        time.sleep(2)
    
    controller.clear_all()


def example_brightness(controller):
    """Ovládání jasu"""
    print("\n=== Ovládání jasu ===")
    
    # Fade in
    print("Fade in...")
    for brightness in range(0, 256, 5):
        controller.set_brightness(brightness)
        controller.set_all(r=0, g=0, b=0, w=255)
        time.sleep(0.01)
    
    time.sleep(0.5)
    
    # Fade out
    print("Fade out...")
    for brightness in range(255, -1, -5):
        controller.set_brightness(brightness)
        controller.set_all(r=0, g=0, b=0, w=255)
        time.sleep(0.01)
    
    controller.set_brightness(255)
    controller.clear_all()


def example_rainbow(controller, duration=10):
    """Rainbow animace"""
    print(f"\n=== Rainbow animace ({duration}s) ===")
    
    start_time = time.time()
    frame = 0
    
    while time.time() - start_time < duration:
        pixels = []
        offset = frame * 3
        
        for i in range(144):
            hue = (i * 360 / 144 + offset) % 360
            r, g, b = controller.hsv_to_rgb(hue, 1.0, 0.3)
            pixels.append((r, g, b, 0))
        
        controller.stream_update(pixels)
        frame += 1
        time.sleep(0.02)
    
    print(f"  {frame} frames ({frame/duration:.1f} FPS)")
    controller.clear_all()


def example_knight_rider(controller, duration=10):
    """Knight Rider efekt"""
    print(f"\n=== Knight Rider ({duration}s) ===")
    
    start_time = time.time()
    pos = 0
    direction = 1
    tail_length = 10
    
    while time.time() - start_time < duration:
        controller.clear_all()
        
        # Hlavní bod
        controller.set_pixel(pos, r=255, g=0, b=0, w=0)
        
        # Ocasek
        for i in range(1, tail_length):
            tail_pos = pos - (i * direction)
            if 0 <= tail_pos < 144:
                brightness = 255 - (i * 255 // tail_length)
                controller.set_pixel(tail_pos, r=brightness, g=0, b=0, w=0)
        
        pos += direction
        if pos >= 143 or pos <= 0:
            direction *= -1
        
        time.sleep(0.01)
    
    controller.clear_all()


def example_fire(controller, duration=10):
    """Simulace ohně"""
    print(f"\n=== Simulace ohně ({duration}s) ===")
    
    start_time = time.time()
    
    while time.time() - start_time < duration:
        pixels = []
        
        for i in range(144):
            intensity = random.randint(100, 255)
            r = intensity
            g = intensity // 2
            b = 0
            pixels.append((r, g, b, 0))
        
        controller.stream_update(pixels)
        time.sleep(0.05)
    
    controller.clear_all()


def example_sparkle(controller, duration=10):
    """Třpytivý efekt"""
    print(f"\n=== Sparkle efekt ({duration}s) ===")
    
    start_time = time.time()
    base_color = (30, 20, 0, 10)
    
    while time.time() - start_time < duration:
        pixels = [base_color] * 144
        
        for _ in range(10):
            pos = random.randint(0, 143)
            pixels[pos] = (255, 255, 200, 255)
        
        controller.stream_update(pixels)
        time.sleep(0.05)
    
    controller.clear_all()


def example_wave(controller, duration=10):
    """Vlnový efekt"""
    print(f"\n=== Vlnový efekt ({duration}s) ===")
    
    start_time = time.time()
    frame = 0
    
    while time.time() - start_time < duration:
        pixels = []
        
        for i in range(144):
            phase = (i / 144.0 * 2 * math.pi) + (frame * 0.1)
            brightness = int((math.sin(phase) + 1) * 127.5)
            pixels.append((0, 0, brightness, 0))
        
        controller.stream_update(pixels)
        frame += 1
        time.sleep(0.03)
    
    controller.clear_all()


def example_color_cycle(controller, duration=10):
    """Cyklování barev"""
    print(f"\n=== Color cycle ({duration}s) ===")
    
    start_time = time.time()
    hue = 0
    
    while time.time() - start_time < duration:
        r, g, b = controller.hsv_to_rgb(hue, 1.0, 0.5)
        controller.set_all(r, g, b, 0)
        
        hue = (hue + 2) % 360
        time.sleep(0.02)
    
    controller.clear_all()


def example_theater_chase(controller, duration=10):
    """Theater chase efekt"""
    print(f"\n=== Theater chase ({duration}s) ===")
    
    start_time = time.time()
    offset = 0
    
    colors = [
        (255, 0, 0, 0),
        (0, 255, 0, 0),
        (0, 0, 255, 0),
    ]
    
    while time.time() - start_time < duration:
        controller.clear_all()
        
        for i in range(offset, 144, 3):
            color = colors[(i // 3) % len(colors)]
            controller.set_pixel(i, *color)
        
        offset = (offset + 1) % 3
        time.sleep(0.1)
    
    controller.clear_all()


def example_performance_test(controller):
    """Test výkonu různých metod"""
    print("\n=== Performance test ===")
    
    iterations = 100
    
    # Test 1: Stream update
    print("\n1. Stream update (plná aktualizace)")
    pixels = [(255, 0, 0, 0)] * 144
    start = time.time()
    for _ in range(iterations):
        controller.stream_update(pixels)
    elapsed = time.time() - start
    print(f"   {iterations} updates v {elapsed:.2f}s = {iterations/elapsed:.1f} FPS")
    
    # Test 2: Single pixel
    print("\n2. Single pixel update")
    start = time.time()
    for _ in range(iterations):
        controller.set_pixel(0, 255, 0, 0, 0)
    elapsed = time.time() - start
    print(f"   {iterations} updates v {elapsed:.2f}s = {iterations/elapsed:.1f} FPS")
    
    # Test 3: Range set
    print("\n3. Range set")
    start = time.time()
    for _ in range(iterations):
        controller.set_range(0, 143, 255, 0, 0, 0)
    elapsed = time.time() - start
    print(f"   {iterations} updates v {elapsed:.2f}s = {iterations/elapsed:.1f} FPS")
    
    controller.clear_all()
    print("\n✓ Performance test dokončen")


def example_piano_layout(controller):
    """Vizualizace klavírního layoutu"""
    print("\n=== Piano Layout ===")
    print("Zobrazení klaviatury:")
    print("  Bílé klávesy = White LED")
    print("  Černé klávesy = Zelená")
    
    visualize_piano_layout(controller)
    
    print(f"\n✓ Zobrazeno {len(PIANO_KEY_MAP)} kláves")
    time.sleep(3)
    controller.clear_all()


def run_all_demos(controller):
    """Spustí všechny demo funkce postupně"""
    print("\n" + "="*60)
    print("SPOUŠTĚNÍ VŠECH DEMO FUNKCÍ")
    print("="*60)
    print("Stiskněte Ctrl+C pro přerušení\n")
    
    demos = [
        ("Ping test", lambda: test_ping(controller)),
        ("Info", lambda: test_info(controller)),
        ("Test jednotlivých LED", lambda: test_single_leds(controller)),
        ("Základní ovládání", lambda: example_basic(controller)),
        ("Rozsahy LED", lambda: example_range(controller)),
        ("Gradienty", lambda: example_gradient(controller)),
        ("Ovládání jasu", lambda: example_brightness(controller)),
        ("Rainbow animace", lambda: example_rainbow(controller, 5)),
        ("Knight Rider", lambda: example_knight_rider(controller, 5)),
        ("Simulace ohně", lambda: example_fire(controller, 5)),
        ("Sparkle efekt", lambda: example_sparkle(controller, 5)),
        ("Vlnový efekt", lambda: example_wave(controller, 5)),
        ("Color cycle", lambda: example_color_cycle(controller, 5)),
        ("Theater chase", lambda: example_theater_chase(controller, 5)),
        ("Piano Layout", lambda: example_piano_layout(controller)),
    ]
    
    try:
        for i, (name, func) in enumerate(demos, 1):
            print(f"\n[{i}/{len(demos)}] {name}...")
            func()
            time.sleep(0.5)  # Krátká pauza mezi demo
        
        print("\n" + "="*60)
        print("✓ VŠECHNA DEMA DOKONČENA")
        print("="*60)
    
    except KeyboardInterrupt:
        print("\n\n⚠ Demo přerušeno uživatelem")
        controller.clear_all()


# ============================================================
# HLAVNÍ MENU
# ============================================================

def main():
    """Hlavní funkce"""
    if len(sys.argv) < 2:
        print("Použití: python dreamscaler.py <serial_port>")
        print("Příklad: python dreamscaler.py /dev/ttyUSB0")
        print("         python dreamscaler.py COM3")
        sys.exit(1)
    
    port = sys.argv[1]
    
    print(f"Připojování k {port}...")
    
    try:
        with LEDController(port) as controller:
            if not controller.serial or not controller.serial.is_open:
                print("✗ Nepodařilo se připojit")
                return
            
            print("✓ Připojeno!")
            
            # Menu položky
            menu_items = [
                # Testy
                ("TESTY", None),
                ("  Ping test", lambda: test_ping(controller)),
                ("  Zobrazit info", lambda: test_info(controller)),
                ("  Test jednotlivých LED", lambda: test_single_leds(controller)),
                
                # Příklady
                ("PŘÍKLADY", None),
                ("  Základní ovládání", lambda: example_basic(controller)),
                ("  Rozsahy LED", lambda: example_range(controller)),
                ("  Gradienty", lambda: example_gradient(controller)),
                ("  Ovládání jasu", lambda: example_brightness(controller)),
                
                # Efekty
                ("EFEKTY", None),
                ("  Rainbow animace", lambda: example_rainbow(controller, 10)),
                ("  Knight Rider", lambda: example_knight_rider(controller, 10)),
                ("  Simulace ohně", lambda: example_fire(controller, 10)),
                ("  Sparkle efekt", lambda: example_sparkle(controller, 10)),
                ("  Vlnový efekt", lambda: example_wave(controller, 10)),
                ("  Color cycle", lambda: example_color_cycle(controller, 10)),
                ("  Theater chase", lambda: example_theater_chase(controller, 10)),
                
                # Ostatní
                ("OSTATNÍ", None),
                ("  Piano Layout", lambda: example_piano_layout(controller)),
                ("  Performance test", lambda: example_performance_test(controller)),
                ("  Spustit všechna dema", lambda: run_all_demos(controller)),
                ("  Vymazat všechny LED", lambda: controller.clear_all()),
            ]
            
            # Hlavní smyčka
            while True:
                print("\n" + "="*60)
                print("DreamScaler USB Controller")
                print("="*60)
                
                idx = 1
                item_map = {}
                for name, func in menu_items:
                    if func is None:
                        print(f"\n{name}")
                    else:
                        print(f"{idx}. {name}")
                        item_map[idx] = (name, func)
                        idx += 1
                
                print("\n0. Konec")
                print("="*60)
                
                choice = input("\nVaše volba: ").strip()
                
                try:
                    if choice == '0':
                        print("\nKončím...")
                        controller.clear_all()
                        break
                    
                    choice_num = int(choice)
                    if choice_num in item_map:
                        name, func = item_map[choice_num]
                        print(f"\nSpouštím: {name}")
                        func()
                        print("✓ Hotovo")
                    else:
                        print("\n✗ Neplatná volba")
                
                except KeyboardInterrupt:
                    print("\n\nPřerušeno...")
                    controller.clear_all()
                    break
                except LEDControllerError as e:
                    print(f"\n✗ Chyba controlleru: {e}")
                except Exception as e:
                    print(f"\n✗ Chyba: {e}")
    
    except Exception as e:
        print(f"✗ Chyba: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
