#!/usr/bin/env python3
"""
DreamScaler Piano - MIDI Controller pro Arturia Keylab 49 MKII
Vizualizace a ovládání LED podle MIDI vstupů z piana
"""

import sys
import time
import json
import atexit
import signal
from controller_api import LEDController, LEDControllerError
from arturia_keylab49_map import (
    PIANO_KEY_MAP, 
    WHITE_KEY_COLOR, 
    BLACK_KEY_COLOR,
    OCTAVE_COLORS,
    LED_INTENSITY,
    visualize_piano_layout,
    get_all_white_keys,
    get_all_black_keys,
    print_piano_map
)

# Globální reference na controller pro cleanup
_global_controller = None

def cleanup_on_exit():
    """
    Cleanup funkce volaná při jakémkoliv ukončení programu
    
    DŮLEŽITÉ: Tato funkce se volá automaticky pomocí atexit.register()
    při každém ukončení Pythonu - normálním i násilném (Ctrl+C).
    Zajišťuje že LED se vždy vypnou a port se správně uvolní.
    """
    global _global_controller
    if _global_controller is not None:
        try:
            print("\n🧹 Cleanup: Vypínám LED a uzavírám port...")
            _global_controller.clear_all()
            _global_controller.disconnect()
            _global_controller = None
            print("✓ Cleanup dokončen")
        except:
            pass  # Ignorovat chyby při cleanup

def signal_handler(signum, frame):
    """
    Handler pro signály (Ctrl+C, atd.)
    
    DŮLEŽITÉ: Zachytává SIGINT (Ctrl+C) a SIGTERM před tím, než
    Python začne standardní ukončení. Tím zajistíme že port se
    uvolní i při násilném ukončení programu.
    """
    print(f"\n\n⚠ Přijat signál {signum} - ukončuji...")
    cleanup_on_exit()
    sys.exit(0)

# ============================================================
# REGISTRACE CLEANUP HANDLERŮ
# ============================================================
# atexit: Volá cleanup_on_exit() při jakémkoliv ukončení
# signal: Zachytává Ctrl+C (SIGINT) a terminate (SIGTERM)
# Díky tomu se port vždy korektně uvolní bez nutnosti release_port.py
atexit.register(cleanup_on_exit)
signal.signal(signal.SIGINT, signal_handler)  # Ctrl+C
signal.signal(signal.SIGTERM, signal_handler)  # Terminate


# ============================================================
# VIZUALIZACE FUNKCÍ
# ============================================================

def show_piano_keys(controller):
    """
    Zobrazí všechny klávesy podle mapy
    Bílé klávesy = white LED, Černé klávesy = zelená
    """
    print("\n=== Zobrazení klaviatury ===")
    print(f"Zobrazuji {len(PIANO_KEY_MAP)} kláves...")
    print(f"Aktuální intenzita LED: {LED_INTENSITY}")
    print("  Bílé klávesy: White LED")
    print("  Černé klávesy: Zelená")
    
    visualize_piano_layout(controller)
    
    white_count = len(get_all_white_keys())
    black_count = len(get_all_black_keys())
    
    print(f"\n✓ Zobrazeno:")
    print(f"  - {white_count} bílých kláves")
    print(f"  - {black_count} černých kláves")
    print(f"  - Celkem: {len(PIANO_KEY_MAP)} kláves")


def show_white_keys_only(controller):
    """Zobrazí pouze bílé klávesy"""
    print("\n=== Bílé klávesy ===")
    
    controller.clear_all()
    white_keys = get_all_white_keys()
    
    for led_pos in white_keys:
        controller.set_pixel(led_pos, *WHITE_KEY_COLOR)
    
    print(f"✓ Zobrazeno {len(white_keys)} bílých kláves")


def show_black_keys_only(controller):
    """Zobrazí pouze černé klávesy"""
    print("\n=== Černé klávesy ===")
    
    controller.clear_all()
    black_keys = get_all_black_keys()
    
    for led_pos in black_keys:
        controller.set_pixel(led_pos, *BLACK_KEY_COLOR)
    
    print(f"✓ Zobrazeno {len(black_keys)} černých kláves")


def test_key_animation(controller):
    """Test animace - postupné rozsvěcování kláves"""
    print("\n=== Test animace kláves ===")
    print("Postupné rozsvěcování všech kláves...")
    
    controller.clear_all()
    
    for led_pos, note, is_white, octave in PIANO_KEY_MAP:
        if led_pos < 144:
            color = WHITE_KEY_COLOR if is_white else BLACK_KEY_COLOR
            controller.set_pixel(led_pos, *color)
            time.sleep(0.05)
    
    print("✓ Animace dokončena")
    time.sleep(2)
    controller.clear_all()


def show_octaves(controller):
    """Zobrazí oktávy různými barvami"""
    print("\n=== Zobrazení oktáv ===")
    print("Každá oktáva má jinou barvu...")
    print(f"Aktuální intenzita LED: {LED_INTENSITY}")
    
    controller.clear_all()
    
    # Zobrazit klávesy podle skutečné oktávy z mapy
    for led_pos, note, is_white, octave in PIANO_KEY_MAP:
        if led_pos < 144 and octave in OCTAVE_COLORS:
            color = OCTAVE_COLORS[octave]
            controller.set_pixel(led_pos, *color)
    
    print("✓ Oktávy zobrazeny")
    print("  Červená  = Oktáva 2")
    print("  Zelená   = Oktáva 3")
    print("  Modrá    = Oktáva 4")
    print("  Žlutá    = Oktáva 5")
    print("  Magenta  = Oktáva 6")


# ============================================================
# STUPNICE (SCALES)
# ============================================================

# Názvy not
NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

# Barvy pro stupně stupnice (jemné pastelové odstíny pro harmonické rozlišení)
SCALE_DEGREE_COLORS = {
    1: (LED_INTENSITY * 2, 0, 0, 0),                           # Root (Tónika) - Výrazná červená
    2: (LED_INTENSITY, LED_INTENSITY // 2, 0, 0),             # 2. stupeň - Oranžová
    3: (LED_INTENSITY, LED_INTENSITY, 0, 0),                   # 3. stupeň - Žlutá
    4: (LED_INTENSITY // 2, LED_INTENSITY, 0, 0),             # 4. stupeň - Žlutozelená
    5: (0, LED_INTENSITY, LED_INTENSITY // 2, 0),             # 5. stupeň - Tyrkysová
    6: (0, LED_INTENSITY // 2, LED_INTENSITY, 0),             # 6. stupeň - Světle modrá
    7: (LED_INTENSITY // 2, 0, LED_INTENSITY, 0),             # 7. stupeň - Fialová
    'dim': (LED_INTENSITY // 3, 0, 0, 0),                      # Diminished - Tmavě červená
}


def load_scales():
    """Načte definice stupnic ze souboru scales.json"""
    try:
        with open('scales.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print("✗ Soubor scales.json nebyl nalezen")
        return []
    except json.JSONDecodeError as e:
        print(f"✗ Chyba při načítání scales.json: {e}")
        return []


def get_scale_notes(root_note, intervals):
    """
    Vrátí seznam not ve stupnici
    
    Args:
        root_note: 0-11 (C-B)
        intervals: seznam intervalů (půltónů)
    
    Returns:
        Seznam not ve stupnici [(nota, stupeň), ...]
    """
    notes = [(root_note, 1)]  # Root je první stupeň
    current = root_note
    degree = 2
    
    for interval in intervals[:-1]:  # Poslední interval vede zpět k root
        current = (current + interval) % 12
        notes.append((current, degree))
        degree += 1
    
    return notes


def show_scale(controller, root_note, scale_name, intervals):
    """
    Zobrazí stupnici na klaviatuře s barevným rozlišením stupňů
    
    Args:
        controller: LEDController instance
        root_note: 0-11 (kořenová nota)
        scale_name: název stupnice
        intervals: seznam intervalů
    """
    print(f"\n=== {NOTE_NAMES[root_note]} {scale_name} ===")
    print(f"Intervaly: {intervals}")
    
    controller.clear_all()
    
    # Získat noty stupnice
    scale_notes = get_scale_notes(root_note, intervals)
    
    # Vytvoř slovník nota -> stupeň
    note_to_degree = {note: degree for note, degree in scale_notes}
    
    # Zobraz na klaviatuře
    for led_pos, note, is_white, octave in PIANO_KEY_MAP:
        if led_pos < 144:
            if note in note_to_degree:
                degree = note_to_degree[note]
                color = SCALE_DEGREE_COLORS.get(degree, (LED_INTENSITY, LED_INTENSITY, LED_INTENSITY, 0))
                controller.set_pixel(led_pos, *color)
    
    print("\n✓ Stupnice zobrazena:")
    for note, degree in scale_notes:
        degree_names = {
            1: "Prima (Tónika)",
            2: "Sekunda",
            3: "Tercie",
            4: "Kvarta",
            5: "Kvinta",
            6: "Sexta",
            7: "Septima"
        }
        print(f"  {degree}. stupeň ({degree_names.get(degree, '')}): {NOTE_NAMES[note]}")
    
    print("\n📊 Legenda barev:")
    print(f"  {'Červená (výrazná)':20} = 1. stupeň (Prima - Tónika)")
    print(f"  {'Oranžová':20} = 2. stupeň (Sekunda)")
    print(f"  {'Žlutá':20} = 3. stupeň (Tercie)")
    print(f"  {'Žlutozelená':20} = 4. stupeň (Kvarta)")
    print(f"  {'Tyrkysová':20} = 5. stupeň (Kvinta)")
    print(f"  {'Světle modrá':20} = 6. stupeň (Sexta)")
    print(f"  {'Fialová':20} = 7. stupeň (Septima)")


def show_major_scales_menu(controller):
    """Interaktivní menu pro výběr Major stupnice"""
    scales = load_scales()
    if not scales:
        return
    
    # Najdi durovou stupnici
    major_scale = None
    for scale in scales:
        if scale['name'] == 'Durová':
            major_scale = scale
            break
    
    if not major_scale:
        print("✗ Durová stupnice nebyla nalezena v scales.json")
        return
    
    while True:
        print("\n" + "="*60)
        print("DUROVÉ STUPNICE - Výběr kořenové noty")
        print("="*60)
        print("\nDostupné kořenové noty:")
        for i, note in enumerate(NOTE_NAMES, 1):
            print(f"{i:2}. {note} Major")
        print("\n99. Zpět")
        print("="*60)
        
        choice = input("\nVaše volba: ").strip()
        
        if choice == '99':
            controller.clear_all()
            break
        
        try:
            root = int(choice) - 1  # Převod z 1-12 na 0-11
            if 0 <= root <= 11:
                show_scale(controller, root, major_scale['name'], major_scale['intervals'])
                input("\nStiskněte Enter pro pokračování...")
            else:
                print("✗ Neplatná volba")
        except ValueError:
            print("✗ Neplatná volba")


def show_all_scales_menu(controller):
    """Dynamické menu pro všechny stupnice z scales.json"""
    scales = load_scales()
    if not scales:
        return
    
    # Seskupit stupnice podle kategorií
    categories = {}
    for scale in scales:
        cat = scale['category']
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(scale)
    
    while True:
        # Hlavní menu - výběr kategorie
        print("\n" + "="*60)
        print("STUPNICE - Výběr kategorie")
        print("="*60)
        print(f"\nCelkem {len(scales)} stupnic v {len(categories)} kategoriích:\n")
        
        cat_list = sorted(categories.keys())
        for i, cat in enumerate(cat_list, 1):
            count = len(categories[cat])
            print(f"{i:2}. {cat:20} ({count} stupnic)")
        
        print("\n 0. Zpět")
        print("="*60)
        
        choice = input("\nVyberte kategorii: ").strip()
        
        if choice == '0':
            controller.clear_all()
            break
        
        try:
            cat_idx = int(choice) - 1
            if 0 <= cat_idx < len(cat_list):
                selected_category = cat_list[cat_idx]
                show_category_scales_menu(controller, selected_category, categories[selected_category])
            else:
                print("✗ Neplatná volba")
        except ValueError:
            print("✗ Neplatná volba")


def show_category_scales_menu(controller, category_name, scales_in_category):
    """Menu pro výběr konkrétní stupnice v kategorii"""
    while True:
        print("\n" + "="*60)
        print(f"KATEGORIE: {category_name}")
        print("="*60)
        print(f"\nDostupné stupnice ({len(scales_in_category)}):\n")
        
        for i, scale in enumerate(scales_in_category, 1):
            print(f"{i:2}. {scale['name']}")
            print(f"     Pocit: {scale['feelings']}")
            print(f"     Žánr: {scale['genre']}")
        
        print("\n 0. Zpět")
        print("="*60)
        
        choice = input("\nVyberte stupnici: ").strip()
        
        if choice == '0':
            break
        
        try:
            scale_idx = int(choice) - 1
            if 0 <= scale_idx < len(scales_in_category):
                selected_scale = scales_in_category[scale_idx]
                show_scale_root_menu(controller, selected_scale)
            else:
                print("✗ Neplatná volba")
        except ValueError:
            print("✗ Neplatná volba")


def show_scale_root_menu(controller, scale):
    """Menu pro výběr kořenové noty pro vybranou stupnici"""
    while True:
        print("\n" + "="*60)
        print(f"STUPNICE: {scale['name']}")
        print("="*60)
        print(f"\nPocit: {scale['feelings']}")
        print(f"Žánr: {scale['genre']}")
        print(f"Použití: {scale['usage']}")
        print(f"Intervaly: {scale['intervals']}")
        print("\nVyberte kořenovou notu:\n")
        
        for i, note in enumerate(NOTE_NAMES, 1):
            print(f"{i:2}. {note} {scale['name']}")
        
        print("\n99. Zpět")
        print("="*60)
        
        choice = input("\nVaše volba: ").strip()
        
        if choice == '99':
            break
        
        try:
            root = int(choice) - 1  # Převod z 1-12 na 0-11
            if 0 <= root <= 11:
                show_scale(controller, root, scale['name'], scale['intervals'])
                input("\nStiskněte Enter pro pokračování...")
            else:
                print("✗ Neplatná volba")
        except ValueError:
            print("✗ Neplatná volba")


# ============================================================
# HLAVNÍ MENU
# ============================================================

def print_menu():
    """Zobrazení menu"""
    print("\n" + "="*60)
    print("DreamScaler Piano - Arturia Keylab 49 MKII")
    print("="*60)
    print(f"\n⚙️  Aktuální intenzita LED: {LED_INTENSITY} (1=večer, 20=den)")
    print("\nVIZUALIZACE:")
    print("1. Zobrazit všechny klávesy")
    print("2. Pouze bílé klávesy")
    print("3. Pouze černé klávesy")
    print("4. Zobrazit oktávy (barevně)")
    print("5. Test animace kláves")
    print("\nSTUPNICE:")
    print("10. Všechny stupnice (kategorie)")
    print("\nUTILITY:")
    print("6. Vypsat mapu kláves")
    print("7. Vymazat všechny LED")
    print("\nMIDI (připraveno):")
    print("8. MIDI monitoring (TODO)")
    print("9. Live MIDI visualizace (TODO)")
    print("\n0. Konec")
    print("="*60)


def main():
    """Hlavní funkce"""
    global _global_controller
    
    if len(sys.argv) < 2:
        print("Použití: python piano.py <serial_port>")
        print("Příklad: python piano.py /dev/ttyUSB0")
        print("         python piano.py COM3")
        sys.exit(1)
    
    port = sys.argv[1]
    
    try:
        print(f"Připojování k {port}...")
        
        controller = LEDController(port)
        _global_controller = controller  # Uložit do globální proměnné pro cleanup
        
        if not controller.connect():
            print("✗ Nepodařilo se připojit")
            _global_controller = None
            return
        
        print("✓ Připojeno k LED controlleru!")
        print(f"✓ Piano mapa načtena: {len(PIANO_KEY_MAP)} kláves")
        
        # Hlavní smyčka
        while True:
            print_menu()
            choice = input("\nVaše volba: ").strip()
            
            try:
                if choice == '1':
                    show_piano_keys(controller)
                    input("\nStiskněte Enter pro pokračování...")
                    controller.clear_all()
                
                elif choice == '2':
                    show_white_keys_only(controller)
                    input("\nStiskněte Enter pro pokračování...")
                    controller.clear_all()
                
                elif choice == '3':
                    show_black_keys_only(controller)
                    input("\nStiskněte Enter pro pokračování...")
                    controller.clear_all()
                
                elif choice == '4':
                    show_octaves(controller)
                    input("\nStiskněte Enter pro pokračování...")
                    controller.clear_all()
                
                elif choice == '5':
                    test_key_animation(controller)
                
                elif choice == '6':
                    print_piano_map()
                    input("\nStiskněte Enter pro pokračování...")
                
                elif choice == '7':
                    print("\nMažu všechny LED...")
                    controller.clear_all()
                    print("✓ Hotovo")
                
                elif choice == '10':
                    show_all_scales_menu(controller)
                
                elif choice == '8':
                    print("\n⚠ MIDI monitoring - zatím neimplementováno")
                    print("Připraveno pro Arturia Keylab 49 MKII")
                
                elif choice == '9':
                    print("\n⚠ Live MIDI visualizace - zatím neimplementováno")
                    print("Připraveno pro Arturia Keylab 49 MKII")
                
                elif choice == '0':
                    print("\nKončím...")
                    controller.clear_all()
                    break
                
                else:
                    print("\n✗ Neplatná volba")
            
            except KeyboardInterrupt:
                # Toto by se nemělo stát díky signal handleru, ale pro jistotu
                print("\n\n⚠ Přerušeno uživatelem (Ctrl+C)")
                break
            except LEDControllerError as e:
                print(f"\n✗ Chyba controlleru: {e}")
            except Exception as e:
                print(f"\n✗ Chyba: {e}")
    
    except KeyboardInterrupt:
        # Toto by se nemělo stát díky signal handleru
        pass
    except Exception as e:
        print(f"✗ Chyba: {e}")
        sys.exit(1)
    finally:
        # Cleanup se provede automaticky přes atexit
        pass


if __name__ == '__main__':
    main()
