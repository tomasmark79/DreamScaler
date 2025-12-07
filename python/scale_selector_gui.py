#!/usr/bin/env python3
"""
DreamScaler - Grafický výběr stupnice
Tkinter GUI pro výběr stupnice, kořenové noty a zobrazení na LED
"""

import tkinter as tk
from tkinter import ttk
import json
from pathlib import Path


# Názvy not
NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

# Barvy pro GUI (odpovídají stupňům stupnice)
DEGREE_COLORS_HEX = {
    1: '#FF4444',  # Prima - Červená
    2: '#FF8800',  # Sekunda - Oranžová
    3: '#44FF44',  # Tercie - Zelená
    4: '#FFFF00',  # Kvarta - Žlutá
    5: '#4444FF',  # Kvinta - Modrá
    6: '#00FFFF',  # Sexta - Tyrkysová
    7: '#FF44FF',  # Septima - Fialová
}


class ScaleSelectorGUI:
    """
    Grafické okno pro výběr stupnice
    
    Umožňuje:
    - Výběr kategorie stupnic
    - Výběr konkrétní stupnice
    - Výběr kořenové noty
    - Zobrazení informací o stupnici
    - Callback pro zobrazení na LED
    """
    
    def __init__(self, scales_data, on_scale_selected=None):
        """
        Args:
            scales_data: seznam stupnic z scales.json
            on_scale_selected: callback funkce(root_note, scale_name, intervals)
        """
        self.scales_data = scales_data
        self.on_scale_selected = on_scale_selected
        self.current_scale = None
        self.current_root = 0
        
        # Seskupit stupnice podle kategorií
        self.categories = {}
        for scale in scales_data:
            cat = scale.get('category', 'Ostatní')
            if cat not in self.categories:
                self.categories[cat] = []
            self.categories[cat].append(scale)
        
        self.root = None
        self.is_running = False
        
    def run(self):
        """Spustí GUI okno"""
        self.root = tk.Tk()
        self.root.title("DreamScaler - Výběr stupnice")
        self.root.geometry("700x600")
        self.root.configure(bg='#2b2b2b')
        
        self.is_running = True
        self._create_widgets()
        
        # Centrovat okno
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')
        
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.mainloop()
        
    def _on_close(self):
        """Handler pro zavření okna"""
        self.is_running = False
        self.root.destroy()
        
    def _create_widgets(self):
        """Vytvoří GUI widgety"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # Konfigurace stylů pro tmavé téma
        style.configure('TFrame', background='#2b2b2b')
        style.configure('TLabel', background='#2b2b2b', foreground='white', font=('Segoe UI', 10))
        style.configure('Title.TLabel', font=('Segoe UI', 14, 'bold'))
        style.configure('Info.TLabel', font=('Segoe UI', 9), foreground='#aaaaaa')
        style.configure('TButton', font=('Segoe UI', 10))
        style.configure('TCombobox', font=('Segoe UI', 10))
        style.configure('TLabelframe', background='#2b2b2b', foreground='white')
        style.configure('TLabelframe.Label', background='#2b2b2b', foreground='white', font=('Segoe UI', 11, 'bold'))
        
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Nadpis
        title_label = ttk.Label(main_frame, text="🎹 DreamScaler - Výběr stupnice", style='Title.TLabel')
        title_label.pack(pady=(0, 20))
        
        # ===== Sekce výběru =====
        select_frame = ttk.LabelFrame(main_frame, text="Výběr stupnice", padding="15")
        select_frame.pack(fill=tk.X, pady=(0, 15))
        
        # Kategorie
        cat_frame = ttk.Frame(select_frame)
        cat_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(cat_frame, text="Kategorie:").pack(side=tk.LEFT, padx=(0, 10))
        self.category_var = tk.StringVar()
        self.category_combo = ttk.Combobox(cat_frame, textvariable=self.category_var, 
                                            values=sorted(self.categories.keys()),
                                            state='readonly', width=30)
        self.category_combo.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.category_combo.bind('<<ComboboxSelected>>', self._on_category_change)
        
        # Stupnice
        scale_frame = ttk.Frame(select_frame)
        scale_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(scale_frame, text="Stupnice:").pack(side=tk.LEFT, padx=(0, 10))
        self.scale_var = tk.StringVar()
        self.scale_combo = ttk.Combobox(scale_frame, textvariable=self.scale_var,
                                         state='readonly', width=30)
        self.scale_combo.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.scale_combo.bind('<<ComboboxSelected>>', self._on_scale_change)
        
        # Kořenová nota
        root_frame = ttk.Frame(select_frame)
        root_frame.pack(fill=tk.X)
        
        ttk.Label(root_frame, text="Kořenová nota:").pack(side=tk.LEFT, padx=(0, 10))
        self.root_var = tk.StringVar(value='C')
        self.root_combo = ttk.Combobox(root_frame, textvariable=self.root_var,
                                        values=NOTE_NAMES, state='readonly', width=10)
        self.root_combo.pack(side=tk.LEFT)
        self.root_combo.bind('<<ComboboxSelected>>', self._on_root_change)
        
        # ===== Sekce informací =====
        info_frame = ttk.LabelFrame(main_frame, text="Informace o stupnici", padding="15")
        info_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        
        # Info grid
        self.info_feelings = ttk.Label(info_frame, text="", style='Info.TLabel', wraplength=600)
        self.info_feelings.pack(anchor=tk.W, pady=2)
        
        self.info_genre = ttk.Label(info_frame, text="", style='Info.TLabel', wraplength=600)
        self.info_genre.pack(anchor=tk.W, pady=2)
        
        self.info_usage = ttk.Label(info_frame, text="", style='Info.TLabel', wraplength=600)
        self.info_usage.pack(anchor=tk.W, pady=2)
        
        self.info_intervals = ttk.Label(info_frame, text="", style='Info.TLabel')
        self.info_intervals.pack(anchor=tk.W, pady=2)
        
        # Vizualizace not ve stupnici
        self.notes_frame = ttk.Frame(info_frame)
        self.notes_frame.pack(fill=tk.X, pady=(15, 0))
        
        ttk.Label(self.notes_frame, text="Noty ve stupnici:").pack(anchor=tk.W)
        self.notes_display = tk.Frame(self.notes_frame, bg='#2b2b2b')
        self.notes_display.pack(fill=tk.X, pady=(5, 0))
        
        # ===== Tlačítka =====
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X)
        
        self.apply_btn = tk.Button(button_frame, text="🎹 Zobrazit na LED", 
                                   command=self._apply_scale,
                                   bg='#4CAF50', fg='white', font=('Segoe UI', 11, 'bold'),
                                   padx=20, pady=10, cursor='hand2')
        self.apply_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        self.clear_btn = tk.Button(button_frame, text="🧹 Vymazat LED",
                                   command=self._clear_leds,
                                   bg='#f44336', fg='white', font=('Segoe UI', 11),
                                   padx=20, pady=10, cursor='hand2')
        self.clear_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        close_btn = tk.Button(button_frame, text="Zavřít",
                              command=self._on_close,
                              bg='#555555', fg='white', font=('Segoe UI', 11),
                              padx=20, pady=10, cursor='hand2')
        close_btn.pack(side=tk.RIGHT)
        
        # Status bar
        self.status_var = tk.StringVar(value="Vyberte kategorii a stupnici")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, 
                              style='Info.TLabel', anchor=tk.W)
        status_bar.pack(fill=tk.X, pady=(10, 0))
        
        # Předvybrat první kategorii
        if self.categories:
            first_cat = sorted(self.categories.keys())[0]
            self.category_combo.set(first_cat)
            self._on_category_change(None)
    
    def _on_category_change(self, event):
        """Handler pro změnu kategorie"""
        category = self.category_var.get()
        if category in self.categories:
            scale_names = [s['name'] for s in self.categories[category]]
            self.scale_combo['values'] = scale_names
            if scale_names:
                self.scale_combo.set(scale_names[0])
                self._on_scale_change(None)
    
    def _on_scale_change(self, event):
        """Handler pro změnu stupnice"""
        scale_name = self.scale_var.get()
        category = self.category_var.get()
        
        # Najít stupnici
        self.current_scale = None
        if category in self.categories:
            for scale in self.categories[category]:
                if scale['name'] == scale_name:
                    self.current_scale = scale
                    break
        
        self._update_info_display()
        self._update_notes_display()
    
    def _on_root_change(self, event):
        """Handler pro změnu kořenové noty"""
        root_name = self.root_var.get()
        self.current_root = NOTE_NAMES.index(root_name)
        self._update_notes_display()
    
    def _update_info_display(self):
        """Aktualizuje zobrazení informací o stupnici"""
        if self.current_scale:
            self.info_feelings.config(text=f"💭 Pocit: {self.current_scale.get('feelings', 'N/A')}")
            self.info_genre.config(text=f"🎵 Žánr: {self.current_scale.get('genre', 'N/A')}")
            self.info_usage.config(text=f"📝 Použití: {self.current_scale.get('usage', 'N/A')}")
            self.info_intervals.config(text=f"🔢 Intervaly: {self.current_scale.get('intervals', [])}")
            self.status_var.set(f"Vybrána stupnice: {self.current_scale['name']}")
        else:
            self.info_feelings.config(text="")
            self.info_genre.config(text="")
            self.info_usage.config(text="")
            self.info_intervals.config(text="")
    
    def _update_notes_display(self):
        """Aktualizuje vizuální zobrazení not ve stupnici"""
        # Vyčistit předchozí noty
        for widget in self.notes_display.winfo_children():
            widget.destroy()
        
        if not self.current_scale:
            return
        
        intervals = self.current_scale.get('intervals', [])
        root = self.current_root
        
        # Vypočítat noty ve stupnici
        notes = [(root, 1)]  # Root je první stupeň
        current = root
        degree = 2
        
        for interval in intervals[:-1]:
            current = (current + interval) % 12
            notes.append((current, degree))
            degree += 1
        
        # Zobrazit noty jako barevné štítky
        for note, deg in notes:
            note_name = NOTE_NAMES[note]
            color = DEGREE_COLORS_HEX.get(deg, '#888888')
            
            # Určit barvu textu podle jasu pozadí
            text_color = 'black' if deg in [3, 4, 6] else 'white'
            
            note_label = tk.Label(self.notes_display, text=f" {note_name} ",
                                  bg=color, fg=text_color,
                                  font=('Segoe UI', 12, 'bold'),
                                  padx=8, pady=4)
            note_label.pack(side=tk.LEFT, padx=2)
            
            # Tooltip s číslem stupně
            degree_names = {1: 'Prima', 2: 'Sekunda', 3: 'Tercie', 4: 'Kvarta',
                           5: 'Kvinta', 6: 'Sexta', 7: 'Septima'}
            tooltip_text = f"{deg}. stupeň ({degree_names.get(deg, '')})"
            self._create_tooltip(note_label, tooltip_text)
    
    def _create_tooltip(self, widget, text):
        """Vytvoří jednoduchý tooltip pro widget"""
        def show_tooltip(event):
            tooltip = tk.Toplevel(widget)
            tooltip.wm_overrideredirect(True)
            tooltip.wm_geometry(f"+{event.x_root+10}+{event.y_root+10}")
            label = tk.Label(tooltip, text=text, bg='#ffffe0', relief='solid', borderwidth=1,
                           font=('Segoe UI', 9), padx=5, pady=2)
            label.pack()
            widget.tooltip = tooltip
            
        def hide_tooltip(event):
            if hasattr(widget, 'tooltip'):
                widget.tooltip.destroy()
                
        widget.bind('<Enter>', show_tooltip)
        widget.bind('<Leave>', hide_tooltip)
    
    def _apply_scale(self):
        """Aplikuje vybranou stupnici (zavolá callback)"""
        if not self.current_scale:
            self.status_var.set("⚠️ Nejprve vyberte stupnici!")
            return
        
        root_name = NOTE_NAMES[self.current_root]
        scale_name = self.current_scale['name']
        intervals = self.current_scale['intervals']
        
        self.status_var.set(f"✓ Zobrazuji: {root_name} {scale_name}")
        
        if self.on_scale_selected:
            self.on_scale_selected(self.current_root, scale_name, intervals)
    
    def _clear_leds(self):
        """Vymaže LED (zavolá callback s None)"""
        self.status_var.set("🧹 LED vymazány")
        if self.on_scale_selected:
            self.on_scale_selected(None, None, None)  # Signal pro vymazání


def load_scales_from_file(filepath='scales.json'):
    """Načte stupnice ze souboru"""
    try:
        path = Path(filepath)
        if not path.exists():
            # Zkusit relativní cestu od tohoto skriptu
            path = Path(__file__).parent / filepath
        
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Chyba při načítání scales.json: {e}")
        return []


def show_scale_selector(on_scale_selected=None):
    """
    Zobrazí GUI pro výběr stupnice
    
    Args:
        on_scale_selected: callback(root_note, scale_name, intervals)
                          root_note=None znamená vymazat LED
    
    Returns:
        ScaleSelectorGUI instance
    """
    scales = load_scales_from_file()
    if not scales:
        print("⚠️ Nepodařilo se načíst stupnice")
        return None
    
    gui = ScaleSelectorGUI(scales, on_scale_selected)
    gui.run()
    return gui


# Pro samostatné testování
if __name__ == '__main__':
    def test_callback(root, name, intervals):
        if root is None:
            print("LED vymazány")
        else:
            print(f"Vybrána stupnice: {NOTE_NAMES[root]} {name}")
            print(f"Intervaly: {intervals}")
    
    show_scale_selector(test_callback)
