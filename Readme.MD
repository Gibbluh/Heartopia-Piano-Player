# Heartopia Player Setup

## Requirements

- Windows
- Python 3 installed
- A MIDI file (`.mid`)

## Files

- `musicplayer.py` - the Heartopia Player app

## Install Python Packages

Open PowerShell in the `music` folder and run:

```powershell
py -m pip install mido keyboard
```

If `py` does not work, try:

```powershell
python -m pip install mido keyboard
```

## Run The App

In PowerShell, go to the `music` folder:

```powershell
cd "F:\Python Scripts\music"
py musicplayer.py
```

## How To Use

1. Open the app.
2. Click `Import MIDI`.
3. Select a `.mid` file.
4. Set the octave or tempo if needed.
5. Open the game or app where the notes should be played.
6. Press the hotkeys below.

## Hotkeys

- `F1` - Start playing
- `F2` - Stop playing
- `F3` - Pause or resume

## Notes

- The script simulates keyboard input, so the target game or app must be focused when playback starts.
- Some MIDI files may need octave shifting to match the playable note range.
- If the script says a module is missing, reinstall the packages with the commands above.

## Troubleshooting

### `ModuleNotFoundError`

Install missing packages again:

```powershell
py -m pip install mido keyboard
```

### Hotkeys do not work

- Make sure the script is still running.
- Try running PowerShell as Administrator if global hotkeys are blocked.
- Confirm no other program is already using the same function keys.

### The wrong notes are played

- Change the octave setting in the app.
- Try a different MIDI file.
