import tkinter as tk
from tkinter import filedialog, ttk
import ctypes
import time
import threading
import mido
import keyboard
import os

# --- 1. DIRECT INPUT SETUP (Keyboard Simulation) ---
SendInput = ctypes.windll.user32.SendInput
PUL = ctypes.POINTER(ctypes.c_ulong)
class KeyBdInput(ctypes.Structure):
    _fields_ = [("wVk", ctypes.c_ushort), ("wScan", ctypes.c_ushort),
                ("dwFlags", ctypes.c_ulong), ("time", ctypes.c_ulong),
                ("dwExtraInfo", PUL)]
class HardwareInput(ctypes.Structure):
    _fields_ = [("uMsg", ctypes.c_ulong), ("wParamL", ctypes.c_short),
                ("wParamH", ctypes.c_short)]
class MouseInput(ctypes.Structure):
    _fields_ = [("dx", ctypes.c_long), ("dy", ctypes.c_long),
                ("mouseData", ctypes.c_ulong), ("dwFlags", ctypes.c_ulong),
                ("time", ctypes.c_ulong), ("dwExtraInfo", PUL)]
class Input_I(ctypes.Union):
    _fields_ = [("ki", KeyBdInput), ("mi", MouseInput), ("hi", HardwareInput)]
class Input(ctypes.Structure):
    _fields_ = [("type", ctypes.c_ulong), ("ii", Input_I)]

def PressKey(hexKeyCode):
    extra = ctypes.c_ulong(0)
    ii_ = Input_I()
    ii_.ki = KeyBdInput(0, hexKeyCode, 0x0008, 0, ctypes.pointer(extra)) # 0x0008 is SCANCODE flag
    x = Input(ctypes.c_ulong(1), ii_)
    ctypes.windll.user32.SendInput(1, ctypes.pointer(x), ctypes.sizeof(x))

def ReleaseKey(hexKeyCode):
    extra = ctypes.c_ulong(0)
    ii_ = Input_I()
    ii_.ki = KeyBdInput(0, hexKeyCode, 0x0008 | 0x0002, 0, ctypes.pointer(extra))
    x = Input(ctypes.c_ulong(1), ii_)
    ctypes.windll.user32.SendInput(1, ctypes.pointer(x), ctypes.sizeof(x))


# --- 2. KEYBOARD MAPPING (Based on your in-game screenshot) ---
# Maps standard MIDI note numbers to Hardware Scan Codes
SCAN_CODES = {
    # === LOW OCTAVE (Bottom Row) ===
    48: 0x33, # C3  (,)
    49: 0x26, # C#3 (L)
    50: 0x34, # D3  (.)
    51: 0x27, # D#3 (;)
    52: 0x35, # E3  (/)
    53: 0x18, # F3  (O)
    54: 0x0B, # F#3 (0)
    55: 0x19, # G3  (P)
    56: 0x0C, # G#3 (-)
    57: 0x1A, # A3  ([)
    58: 0x0D, # A#3 (=)
    59: 0x1B, # B3  (])

    # === MIDDLE OCTAVE (Middle Row) ===
    60: 0x2C, # C4  (Z)
    61: 0x1F, # C#4 (S)
    62: 0x2D, # D4  (X)
    63: 0x20, # D#4 (D)
    64: 0x2E, # E4  (C)
    65: 0x2F, # F4  (V)
    66: 0x22, # F#4 (G)
    67: 0x30, # G4  (B)
    68: 0x23, # G#4 (H)
    69: 0x31, # A4  (N)
    70: 0x24, # A#4 (J)
    71: 0x32, # B4  (M)

    # === HIGH OCTAVE (Top Row) ===
    72: 0x10, # C5  (Q)
    73: 0x03, # C#5 (2)
    74: 0x11, # D5  (W)
    75: 0x04, # D#5 (3)
    76: 0x12, # E5  (E)
    77: 0x13, # F5  (R)
    78: 0x06, # F#5 (5)
    79: 0x14, # G5  (T)
    80: 0x07, # G#5 (6)
    81: 0x15, # A5  (Y)
    82: 0x08, # A#5 (7)
    83: 0x16, # B5  (U)
    84: 0x17, # C6  (I)
}

# --- 3. GUI & APPLICATION CLASS ---
class HeartopiaPlayerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Heartopia Player")
        self.root.geometry("380x300")
        self.root.configure(bg="#f0f0f0")
        self.root.resizable(False, False)

        # State Variables
        self.midi_file_path = None
        self.is_playing = False
        self.is_paused = False
        self.play_thread = None
        self.pressed_keys = set()

        # --- UI BUILDER ---
        # Instruction Label
        tk.Label(root, text="Import MIDI, F1 to play, F2 to stop, or F3 to pause", font=("Segoe UI", 10), bg="#f0f0f0").pack(pady=(20, 10))

        # File Label
        self.file_label = tk.Label(root, text="File: Secret base.mid", font=("Segoe UI", 10), bg="#f0f0f0")
        self.file_label.pack(pady=5)

        # Import Button
        import_btn = tk.Button(root, text="Import MIDI", font=("Segoe UI", 10), width=15, relief="groove", command=self.import_midi)
        import_btn.pack(pady=5)

        self.pause_btn = tk.Button(root, text="Pause", font=("Segoe UI", 10), width=15, relief="groove", state="disabled", command=self.toggle_pause)
        self.pause_btn.pack(pady=5)

        # Octave Shift Combobox
        self.octave_var = tk.StringVar(value="Middle")
        octave_cb = ttk.Combobox(root, textvariable=self.octave_var, values=["Middle", "+1 Octave", "-1 Octave", "+2 Octaves", "-2 Octaves"], state="readonly", width=12)
        octave_cb.pack(pady=(10, 5))

        # Tempo Label & Spinbox
        tk.Label(root, text="Tempo", font=("Segoe UI", 10), bg="#f0f0f0").pack()
        self.tempo_var = tk.DoubleVar(value=1.0)
        tempo_spin = ttk.Spinbox(root, from_=0.1, to=5.0, increment=0.1, textvariable=self.tempo_var, width=8)
        tempo_spin.pack(pady=5)

        # Ignore Unmapped Notes Checkbox
        self.ignore_unmapped_var = tk.BooleanVar(value=True)
        ignore_cb = tk.Checkbutton(root, text="Ignore unmapped notes", variable=self.ignore_unmapped_var, font=("Segoe UI", 9), bg="#f0f0f0")
        ignore_cb.pack(pady=5)

        # Credits Label
        credits_lbl = tk.Label(root, text="By gibbluh", font=("Segoe UI", 9, "bold"), fg="#3a4b9c", bg="#f0f0f0")
        credits_lbl.pack(pady=(10, 0))

        # Register Hotkeys
        keyboard.on_press_key("F1", self.hotkey_play)
        keyboard.on_press_key("F2", self.hotkey_stop)
        keyboard.on_press_key("F3", self.hotkey_pause)

    def import_midi(self):
        file_path = filedialog.askopenfilename(filetypes=[("MIDI files", "*.mid")])
        if file_path:
            self.midi_file_path = file_path
            filename = os.path.basename(file_path)
            self.file_label.config(text=f"File: {filename}")

    def hotkey_play(self, event=None):
        if not self.is_playing and self.midi_file_path:
            self.is_playing = True
            self.is_paused = False
            self.pause_btn.config(state="normal", text="Pause")
            self.file_label.config(fg="green", text=f"Playing: {os.path.basename(self.midi_file_path)}")
            self.play_thread = threading.Thread(target=self.play_midi_engine)
            self.play_thread.start()

    def hotkey_stop(self, event=None):
        if self.is_playing:
            self.is_playing = False
            self.is_paused = False
            self.pause_btn.config(state="disabled", text="Pause")
            self.file_label.config(fg="black", text=f"File: {os.path.basename(self.midi_file_path)}")
            self.release_all_keys()

    def hotkey_pause(self, event=None):
        self.toggle_pause()

    def toggle_pause(self):
        if not self.is_playing:
            return

        self.is_paused = not self.is_paused
        if self.is_paused:
            self.pause_btn.config(text="Resume")
            self.file_label.config(fg="orange", text=f"Paused: {os.path.basename(self.midi_file_path)}")
            self.release_all_keys()
        else:
            self.pause_btn.config(text="Pause")
            self.file_label.config(fg="green", text=f"Playing: {os.path.basename(self.midi_file_path)}")

    def release_all_keys(self):
        for code in list(self.pressed_keys):
            ReleaseKey(code)
        self.pressed_keys.clear()

    def wait_with_pause(self, duration):
        elapsed = 0.0
        step = 0.01
        while self.is_playing and elapsed < duration:
            if self.is_paused:
                time.sleep(step)
                continue
            chunk = min(step, duration - elapsed)
            time.sleep(chunk)
            elapsed += chunk

    def play_midi_engine(self):
        try:
            mid = mido.MidiFile(self.midi_file_path)
            
            # Determine Octave Shift Math
            shift_text = self.octave_var.get()
            octave_shift = 0
            if shift_text == "+1 Octave": octave_shift = 12
            elif shift_text == "-1 Octave": octave_shift = -12
            elif shift_text == "+2 Octaves": octave_shift = 24
            elif shift_text == "-2 Octaves": octave_shift = -24

            for msg in mid:
                if not self.is_playing:
                    break

                # Dynamic Tempo Scaling
                tempo_multiplier = self.tempo_var.get()
                if tempo_multiplier <= 0:
                    tempo_multiplier = 1.0
                self.wait_with_pause(msg.time / tempo_multiplier)

                while self.is_playing and self.is_paused:
                    time.sleep(0.01)

                if not self.is_playing:
                    break

                if not msg.is_meta and msg.type in ['note_on', 'note_off']:
                    target_note = msg.note + octave_shift

                    # Auto-transposer if "Ignore Unmapped" is OFF
                    if not self.ignore_unmapped_var.get():
                        while target_note < 48: target_note += 12
                        while target_note > 84: target_note -= 12

                    scan_code = SCAN_CODES.get(target_note)
                    
                    if scan_code:
                        if msg.type == 'note_on' and msg.velocity > 0:
                            PressKey(scan_code)
                            self.pressed_keys.add(scan_code)
                        else: # Note off
                            ReleaseKey(scan_code)
                            if scan_code in self.pressed_keys:
                                self.pressed_keys.remove(scan_code)

        except Exception as e:
            print(f"Playback Error: {e}")
        finally:
            self.is_playing = False
            self.is_paused = False
            self.release_all_keys()
            self.pause_btn.config(state="disabled", text="Pause")
            if self.midi_file_path:
                self.file_label.config(fg="black", text=f"File: {os.path.basename(self.midi_file_path)}")
            else:
                self.file_label.config(fg="black", text="File: No MIDI selected")

# --- 4. START UP ---
if __name__ == "__main__":
    root = tk.Tk()
    app = HeartopiaPlayerApp(root)
    
    # Keeps the app running and listening to hotkeys
    root.mainloop()
