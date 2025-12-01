"""
DreamScaler Piano - Mapování LED na klávesy pro Arturia Keylab 49 MKII
Kompletní mapování pro 49 kláves na 144 LED SK6812 RGBW pásek
"""

# ============================================================
# KONFIGURACE
# ============================================================

# Intenzita LED pro různé prostředí
# Večer/tma: použij nízkou intenzitu (1)
# Den/světlo: použij vyšší intenzitu (20)
LED_INTENSITY = 1

# ============================================================
# MAPOVÁNÍ KLÁVES
# ============================================================

# Formát: (led_pozice, nota_cislo, je_bila_klavesa, oktava)
# nota_cislo: 0-11 (C, C#, D, D#, E, F, F#, G, G#, A, A#, B)
# je_bila_klavesa: 1 = bílá, 0 = černá
# oktava: 2-6

PIANO_KEY_MAP = [
    # Octave 6 (C6)
    (1, 0, 1, 6),    # C6

    # Octave 5 (B5 to C5)
    (3, 11, 1, 5),   # B5
    (5, 10, 0, 5),   # A#5
    (7, 9, 1, 5),    # A5
    (9, 8, 0, 5),    # G#5
    (11, 7, 1, 5),   # G5
    (13, 6, 0, 5),   # F#5
    (15, 5, 1, 5),   # F5
    (17, 4, 1, 5),   # E5
    (19, 3, 0, 5),   # D#5
    (21, 2, 1, 5),   # D5
    (23, 1, 0, 5),   # C#5
    (25, 0, 1, 5),   # C5
    
    # Octave 4 (B4 to C4)
    (27, 11, 1, 4),  # B4
    (29, 10, 0, 4),  # A#4
    (31, 9, 1, 4),   # A4
    (33, 8, 0, 4),   # G#4
    (34, 7, 1, 4),   # G4
    (36, 6, 0, 4),   # F#4
    (38, 5, 1, 4),   # F4
    (40, 4, 1, 4),   # E4
    (42, 3, 0, 4),   # D#4
    (44, 2, 1, 4),   # D4
    (46, 1, 0, 4),   # C#4
    (48, 0, 1, 4),   # C4
    
    # Octave 3 (B3 to C3)
    (50, 11, 1, 3),  # B3
    (52, 10, 0, 3),  # A#3
    (54, 9, 1, 3),   # A3
    (56, 8, 0, 3),   # G#3
    (57, 7, 1, 3),   # G3
    (59, 6, 0, 3),   # F#3
    (61, 5, 1, 3),   # F3
    (63, 4, 1, 3),   # E3
    (65, 3, 0, 3),   # D#3
    (67, 2, 1, 3),   # D3
    (69, 1, 0, 3),   # C#3
    (71, 0, 1, 3),   # C3
    
    # Octave 2 (B2 to C2)
    (73, 11, 1, 2),  # B2
    (75, 10, 0, 2),  # A#2
    (77, 9, 1, 2),   # A2
    (79, 8, 0, 2),   # G#2
    (81, 7, 1, 2),   # G2
    (83, 6, 0, 2),   # F#2
    (84, 5, 1, 2),   # F2
    (86, 4, 1, 2),   # E2
    (88, 3, 0, 2),   # D#2
    (90, 2, 1, 2),   # D2
    (92, 1, 0, 2),   # C#2
    (94, 0, 1, 2),   # C2
]

# ============================================================
# BARVY
# ============================================================

# Barvy pro klávesy (používají globální LED_INTENSITY)
WHITE_KEY_COLOR = (0, 0, 0, LED_INTENSITY)     # Bílé klávesy - bílá
BLACK_KEY_COLOR = (0, LED_INTENSITY, 0, 0)     # Černé klávesy - zelená

# Barvy pro oktávy (používají globální LED_INTENSITY)
OCTAVE_COLORS = {
    2: (LED_INTENSITY, 0, 0, 0),               # Oktáva 2 - Červená
    3: (0, LED_INTENSITY, 0, 0),               # Oktáva 3 - Zelená
    4: (0, 0, LED_INTENSITY, 0),               # Oktáva 4 - Modrá
    5: (LED_INTENSITY, LED_INTENSITY, 0, 0),   # Oktáva 5 - Žlutá
    6: (LED_INTENSITY, 0, LED_INTENSITY, 0),   # Oktáva 6 - Magenta
}


# ============================================================
# FUNKCE
# ============================================================

def get_led_for_note(note_number, octave):
    """
    Vrátí LED pozici pro danou notu a oktávu
    
    Args:
        note_number: 0-11 (C, C#, D, D#, E, F, F#, G, G#, A, A#, B)
        octave: 2-6
    
    Returns:
        LED pozice nebo None pokud nota není v mapě
    """
    for led_pos, note, is_white, oct in PIANO_KEY_MAP:
        if note == note_number and oct == octave:
            return led_pos
    return None


def get_all_white_keys():
    """Vrátí seznam LED pozic pro všechny bílé klávesy"""
    return [led_pos for led_pos, note, is_white, octave in PIANO_KEY_MAP if is_white]


def get_all_black_keys():
    """Vrátí seznam LED pozic pro všechny černé klávesy"""
    return [led_pos for led_pos, note, is_white, octave in PIANO_KEY_MAP if not is_white]


def visualize_piano_layout(controller):
    """
    Vizualizace klaviatury - bílé klávesy = white LED, černé = zelená
    
    Args:
        controller: LEDController instance
    """
    controller.buffer_begin()
    
    for led_pos, note, is_white, octave in PIANO_KEY_MAP:
        if led_pos < 144:
            color = WHITE_KEY_COLOR if is_white else BLACK_KEY_COLOR
            controller.buffer_set_pixel(led_pos, *color)
    
    controller.buffer_end()


# Názvy not pro debugging
NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

def print_piano_map():
    """Vypíše celou mapu piana pro debugging"""
    print("\nDreamScaler Piano Map:")
    print("LED Pos | Octave | Note | Type")
    print("--------|--------|------|------")
    for led_pos, note, is_white, octave in PIANO_KEY_MAP:
        note_name = NOTE_NAMES[note]
        key_type = "White" if is_white else "Black"
        print(f"  {led_pos:3d}   |   {octave}    | {note_name:3s}  | {key_type}")
