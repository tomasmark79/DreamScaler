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
from scale_selector_gui import ScaleSelectorGUI, load_scales_from_file

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

# Méně rušivé barvy pro stupnice
SCALE_DEGREE_COLORS = {
    # Akordové tóny (triáda) - jasné barvy
    # POZOR: LED_INTENSITY může být 1, proto používáme násobení pro zachování poměrů
    1: (LED_INTENSITY, 0, 0, 0),                       # Prima - Tónika - Bílá
    3: (0, LED_INTENSITY, 0, 0),                       # Tercie - Zelená
    5: (0, 0, LED_INTENSITY, 0),                       # Kvinta - Modrá
    
    # Průchozí tóny
    2: (LED_INTENSITY, LED_INTENSITY,  0),             # 2. stupeň - Oranžová
    4: (LED_INTENSITY, LED_INTENSITY, 0, 0),           # 4. stupeň - Žlutá
    6: (0, LED_INTENSITY, LED_INTENSITY, 0),           # 6. stupeň - Tyrkysová
    7: (LED_INTENSITY, 0, LED_INTENSITY, 0),           # 7. stupeň - Fialová
    
    'dim': (1, 0, 0, 0),                               # Diminished - minimální červená
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


def show_scale_selector_gui(controller):
    """
    Spustí grafické okno pro výběr stupnice
    
    Args:
        controller: LEDController instance
    """
    import threading
    
    def on_scale_selected(root_note, scale_name, intervals):
        """Callback volaný z GUI při výběru stupnice"""
        if root_note is None:
            # Vymazat LED
            controller.clear_all()
        else:
            # Zobrazit stupnici
            show_scale(controller, root_note, scale_name, intervals)
    
    print("\n🖼️  Otevírám grafický výběr stupnice...")
    print("   (Okno se otevře v samostatném okně)")
    
    # Načíst stupnice
    scales = load_scales_from_file()
    if not scales:
        print("✗ Nepodařilo se načíst stupnice")
        return
    
    # Vytvořit a spustit GUI
    gui = ScaleSelectorGUI(scales, on_scale_selected)
    gui.run()
    
    print("✓ GUI zavřeno")


# ============================================================
# CHORD PROGRESSIONS (Akordové postupy)
# ============================================================

# Definice typických akordových postupů
CHORD_PROGRESSIONS = {
    "I-IV-V-I": {
        "name": "Základní kadence",
        "description": "Nejzákladnější harmonický postup v západní hudbě",
        "genre": "Pop, Rock, Folk, Country",
        "chords": [1, 4, 5, 1],
        "chord_types": ["maj", "maj", "maj", "maj"]
    },
    "I-V-vi-IV": {
        "name": "Pop progrese",
        "description": "Nejpoužívanější postup v pop music (Axis progression)",
        "genre": "Pop, Rock",
        "chords": [1, 5, 6, 4],
        "chord_types": ["maj", "maj", "min", "maj"]
    },
    "ii-V-I": {
        "name": "Jazz kadence",
        "description": "Základní jazzová kadence",
        "genre": "Jazz, Bossa Nova",
        "chords": [2, 5, 1],
        "chord_types": ["min7", "dom7", "maj7"]
    },
    "I-vi-IV-V": {
        "name": "50s progression",
        "description": "Doo-wop postup z 50. let",
        "genre": "Oldies, Doo-wop",
        "chords": [1, 6, 4, 5],
        "chord_types": ["maj", "min", "maj", "maj"]
    },
    "vi-IV-I-V": {
        "name": "Emotional progression",
        "description": "Mollová varianta pop progrese",
        "genre": "Pop, Ballads",
        "chords": [6, 4, 1, 5],
        "chord_types": ["min", "maj", "maj", "maj"]
    },
    "I-IV-vi-V": {
        "name": "Country progression",
        "description": "Běžný postup v country a folk",
        "genre": "Country, Folk",
        "chords": [1, 4, 6, 5],
        "chord_types": ["maj", "maj", "min", "maj"]
    },
    "i-VII-VI-VII": {
        "name": "Andaluská kadence",
        "description": "Flamenco/španělský postup",
        "genre": "Flamenco, Metal",
        "chords": [1, 7, 6, 7],
        "chord_types": ["min", "maj", "maj", "maj"]
    },
    "I-bVII-IV-I": {
        "name": "Mixolydian vamp",
        "description": "Rockový postup s bVII",
        "genre": "Rock, Blues rock",
        "chords": [1, -7, 4, 1],  # -7 = bVII (snížená septima)
        "chord_types": ["maj", "maj", "maj", "maj"]
    },
    "12-bar-blues": {
        "name": "12-taktový blues",
        "description": "Klasická bluesová forma",
        "genre": "Blues, Rock'n'roll",
        "chords": [1, 1, 1, 1, 4, 4, 1, 1, 5, 4, 1, 5],
        "chord_types": ["dom7", "dom7", "dom7", "dom7", "dom7", "dom7", "dom7", "dom7", "dom7", "dom7", "dom7", "dom7"]
    }
}

# Barvy pro akordy v progresi
CHORD_COLORS = {
    1: (LED_INTENSITY * 2, 0, 0, 0),          # I - Červená (tónika)
    2: (LED_INTENSITY, LED_INTENSITY, 0, 0),   # ii - Žlutá
    3: (0, LED_INTENSITY * 2, 0, 0),           # iii - Zelená
    4: (0, LED_INTENSITY, LED_INTENSITY, 0),   # IV - Tyrkysová (subdominanta)
    5: (0, 0, LED_INTENSITY * 2, 0),           # V - Modrá (dominanta)
    6: (LED_INTENSITY, 0, LED_INTENSITY, 0),   # vi - Magenta
    7: (LED_INTENSITY, LED_INTENSITY // 2, 0, 0),  # vii° - Oranžová
    -7: (LED_INTENSITY, 0, 0, LED_INTENSITY),  # bVII - Červená + bílá
}

# Intervaly akordů (od základního tónu)
CHORD_INTERVALS = {
    "maj": [0, 4, 7],           # Durový kvintakord
    "min": [0, 3, 7],           # Mollový kvintakord
    "dim": [0, 3, 6],           # Zmenšený
    "aug": [0, 4, 8],           # Zvětšený
    "maj7": [0, 4, 7, 11],      # Durový septakord
    "min7": [0, 3, 7, 10],      # Mollový septakord
    "dom7": [0, 4, 7, 10],      # Dominantní septakord
    "dim7": [0, 3, 6, 9],       # Zmenšený septakord
}

# Stupně durové stupnice v půltónech od tóniky
SCALE_DEGREES_SEMITONES = {
    1: 0,   # I
    2: 2,   # ii
    3: 4,   # iii
    4: 5,   # IV
    5: 7,   # V
    6: 9,   # vi
    7: 11,  # vii°
    -7: 10, # bVII (snížená septima)
}


def get_chord_notes(root, degree, chord_type):
    """
    Získá noty akordu
    
    Args:
        root: kořenová nota stupnice (0-11)
        degree: stupeň akordu (1-7, nebo -7 pro bVII)
        chord_type: typ akordu ("maj", "min", "dom7", atd.)
    
    Returns:
        Seznam not akordu (0-11)
    """
    # Základní tón akordu
    chord_root = (root + SCALE_DEGREES_SEMITONES[degree]) % 12
    
    # Intervaly akordu
    intervals = CHORD_INTERVALS.get(chord_type, CHORD_INTERVALS["maj"])
    
    # Noty akordu
    return [(chord_root + interval) % 12 for interval in intervals]


def show_chord(controller, root, degree, chord_type, color):
    """
    Zobrazí akord na klaviatuře
    
    Args:
        controller: LEDController instance
        root: kořenová nota stupnice (0-11)
        degree: stupeň akordu
        chord_type: typ akordu
        color: barva pro zobrazení
    """
    chord_notes = get_chord_notes(root, degree, chord_type)
    
    for led_pos, note, is_white, octave in PIANO_KEY_MAP:
        if led_pos < 144:
            if note in chord_notes:
                controller.set_pixel(led_pos, *color)


def show_progression(controller, root_note, progression_key):
    """
    Zobrazí akordový postup s animací
    
    Args:
        controller: LEDController instance
        root_note: kořenová nota (0-11)
        progression_key: klíč do CHORD_PROGRESSIONS
    """
    progression = CHORD_PROGRESSIONS[progression_key]
    
    print(f"\n=== {NOTE_NAMES[root_note]} - {progression['name']} ===")
    print(f"Postup: {progression_key}")
    print(f"Popis: {progression['description']}")
    print(f"Žánr: {progression['genre']}")
    print(f"\nAkordy v progresi:")
    
    chords = progression['chords']
    chord_types = progression['chord_types']
    
    # Zobraz informace o akordech
    for i, (degree, chord_type) in enumerate(zip(chords, chord_types)):
        chord_notes = get_chord_notes(root_note, degree, chord_type)
        chord_name = NOTE_NAMES[chord_notes[0]]
        
        # Přidej typ akordu k názvu
        type_suffix = ""
        if chord_type == "min" or chord_type == "min7":
            type_suffix = "m"
        elif chord_type == "dim" or chord_type == "dim7":
            type_suffix = "°"
        elif chord_type == "dom7":
            type_suffix = "7"
        elif chord_type == "maj7":
            type_suffix = "maj7"
        
        print(f"  {i+1}. {chord_name}{type_suffix} (stupeň {degree if degree > 0 else 'b' + str(-degree)})")
    
    print("\n🎹 Přehrávám progresi... (Enter = další akord, 'q' = konec)")
    
    current_idx = 0
    while True:
        controller.clear_all()
        
        degree = chords[current_idx]
        chord_type = chord_types[current_idx]
        color = CHORD_COLORS.get(degree, (LED_INTENSITY, LED_INTENSITY, LED_INTENSITY, 0))
        
        show_chord(controller, root_note, degree, chord_type, color)
        
        chord_notes = get_chord_notes(root_note, degree, chord_type)
        chord_name = NOTE_NAMES[chord_notes[0]]
        
        print(f"\n  ▶ Akord {current_idx + 1}/{len(chords)}: {chord_name} ({chord_type})")
        
        choice = input("    [Enter=další, 'a'=auto, 'r'=restart, 'q'=konec]: ").strip().lower()
        
        if choice == 'q':
            break
        elif choice == 'r':
            current_idx = 0
            continue
        elif choice == 'a':
            # Auto mode - přehrát celou progresi
            print("\n  🔄 Auto režim (1.5s na akord)...")
            for idx in range(len(chords)):
                controller.clear_all()
                d = chords[idx]
                ct = chord_types[idx]
                col = CHORD_COLORS.get(d, (LED_INTENSITY, LED_INTENSITY, LED_INTENSITY, 0))
                show_chord(controller, root_note, d, ct, col)
                
                cn = get_chord_notes(root_note, d, ct)
                print(f"    ▶ {NOTE_NAMES[cn[0]]} ({ct})")
                time.sleep(1.5)
            
            print("  ✓ Progrese dokončena")
            current_idx = 0
            continue
        else:
            current_idx = (current_idx + 1) % len(chords)
    
    controller.clear_all()


def show_chord_progressions_menu(controller):
    """Menu pro výběr akordového postupu"""
    while True:
        print("\n" + "="*60)
        print("AKORDOVÉ POSTUPY (Chord Progressions)")
        print("="*60)
        print(f"\nDostupné postupy ({len(CHORD_PROGRESSIONS)}):\n")
        
        prog_list = list(CHORD_PROGRESSIONS.keys())
        for i, key in enumerate(prog_list, 1):
            prog = CHORD_PROGRESSIONS[key]
            print(f"{i:2}. {key:20} - {prog['name']}")
            print(f"     {prog['genre']}")
        
        print("\n 0. Zpět")
        print("="*60)
        
        choice = input("\nVyberte postup: ").strip()
        
        if choice == '0':
            controller.clear_all()
            break
        
        try:
            prog_idx = int(choice) - 1
            if 0 <= prog_idx < len(prog_list):
                selected_prog = prog_list[prog_idx]
                show_progression_root_menu(controller, selected_prog)
            else:
                print("✗ Neplatná volba")
        except ValueError:
            print("✗ Neplatná volba")


def show_progression_root_menu(controller, progression_key):
    """Menu pro výběr kořenové noty pro progresi"""
    progression = CHORD_PROGRESSIONS[progression_key]
    
    while True:
        print("\n" + "="*60)
        print(f"POSTUP: {progression_key} - {progression['name']}")
        print("="*60)
        print(f"\nPopis: {progression['description']}")
        print(f"Žánr: {progression['genre']}")
        print("\nVyberte tóninu (kořenovou notu):\n")
        
        for i, note in enumerate(NOTE_NAMES, 1):
            print(f"{i:2}. {note}")
        
        print("\n99. Zpět")
        print("="*60)
        
        choice = input("\nVaše volba: ").strip()
        
        if choice == '99':
            break
        
        try:
            root = int(choice) - 1
            if 0 <= root <= 11:
                show_progression(controller, root, progression_key)
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
    print("\nSTUPNICE A AKORDY:")
    print("10. Všechny stupnice (kategorie)")
    print("11. Akordové postupy (Chord Progressions)")
    print("12. 🖼️  Grafický výběr stupnice (GUI)")
    print("\nUTILITY:")
    print("6. Vypsat mapu kláves")
    print("7. Vymazat všechny LED")
    print("\nMIDI (připraveno):")
    print("8. MIDI monitoring (TODO)")
    print("9. Live MIDI visualizace (TODO)")
    print("\n0. Konec")
    print("="*60)


def execute_menu_choice(controller, choice):
    """
    Vykoná volbu z menu
    
    Args:
        controller: LEDController instance
        choice: volba z menu (string)
    
    Returns:
        'exit' pro ukončení, None jinak
    """
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
    
    elif choice == '11':
        show_chord_progressions_menu(controller)
    
    elif choice == '12':
        show_scale_selector_gui(controller)
    
    elif choice == '8':
        print("\n⚠ MIDI monitoring - zatím neimplementováno")
        print("Připraveno pro Arturia Keylab 49 MKII")
    
    elif choice == '9':
        print("\n⚠ Live MIDI visualizace - zatím neimplementováno")
        print("Připraveno pro Arturia Keylab 49 MKII")
    
    elif choice == '0':
        print("\nKončím...")
        controller.clear_all()
        return 'exit'
    
    else:
        print("\n✗ Neplatná volba")
    
    return None


def main():
    """Hlavní funkce"""
    global _global_controller
    
    if len(sys.argv) < 2:
        print("Použití: python piano.py <serial_port> [volba_menu]")
        print("Příklad: python piano.py /dev/ttyUSB0")
        print("         python piano.py COM3")
        print("         python piano.py COM5 12    # Spustí přímo GUI (volba 12)")
        print("\nDostupné volby menu:")
        print("  1  - Zobrazit všechny klávesy")
        print("  2  - Pouze bílé klávesy")
        print("  3  - Pouze černé klávesy")
        print("  4  - Zobrazit oktávy")
        print("  5  - Test animace")
        print("  10 - Všechny stupnice")
        print("  11 - Akordové postupy")
        print("  12 - Grafický výběr stupnice (GUI)")
        sys.exit(1)
    
    port = sys.argv[1]
    auto_choice = sys.argv[2] if len(sys.argv) > 2 else None
    
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
        
        # Pokud byl zadán parametr menu, spustit přímo
        if auto_choice:
            print(f"\n→ Automatické spuštění volby: {auto_choice}")
            execute_menu_choice(controller, auto_choice)
            return
        
        # Hlavní smyčka
        while True:
            print_menu()
            choice = input("\nVaše volba: ").strip()
            
            try:
                result = execute_menu_choice(controller, choice)
                if result == 'exit':
                    break
            
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
