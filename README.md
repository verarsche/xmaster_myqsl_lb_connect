# XtreamMasters Database User Manager

Automatisches Tool zum Extrahieren von Datenbank-Credentials und Erstellen von MySQL-Admin-Usern auf XtreamUI/XtreamCodes Servern.

---

## 🎵 musicgen — Video-to-Music-Genre Toolkit

Extract audio from any video file and transform it into **rock**, **rap**, or **metal** style — all locally, no cloud required.

### Quick start

```bash
# 1. Install system dependency
sudo apt install ffmpeg          # Ubuntu/Debian
# brew install ffmpeg            # macOS

# 2. Install Python dependencies
pip install -r requirements_music.txt

# 3. Extract audio from your video
python -m musicgen extract-audio myvideo.mp4 -o audio.wav

# 4. (Optional) Separate vocals from instrumental
python -m musicgen separate audio.wav \
    --vocals     vocals.wav \
    --instrumental instrumental.wav

# 5. Generate genre-styled versions
python -m musicgen genre audio.wav --style rock  -o rock_out.wav
python -m musicgen genre audio.wav --style rap   -o rap_out.wav
python -m musicgen genre audio.wav --style metal -o metal_out.wav
```

### Commands

| Command | Description |
|---------|-------------|
| `extract-audio <video> -o <out.wav>` | Extract audio track from a video file |
| `separate <audio> --vocals V --instrumental I` | Split into vocals + instrumental |
| `genre <audio> --style rock\|rap\|metal -o <out.wav>` | Apply genre processing |

#### `extract-audio` options

| Flag | Default | Description |
|------|---------|-------------|
| `--sample-rate` | 44100 | Output sample rate in Hz |
| `--channels` | 2 | 1 = mono, 2 = stereo |

#### `separate` options

| Flag | Default | Description |
|------|---------|-------------|
| `--backend` | `auto` | `auto` / `demucs` / `builtin` |

The `auto` backend tries **demucs** first (better quality) and falls back to the built-in spectral mid/side separator.  
Install demucs for best results: `pip install demucs`

### Genre processing pipeline

Each genre applies a deterministic DSP chain to the input audio, plus a synthetic drum layer:

| Stage | Rock | Rap | Metal |
|-------|------|-----|-------|
| High-pass filter | 80 Hz | — | 100 Hz |
| Distortion | soft-clip (tanh, drive=4) | — | hard-clip (drive=10) |
| EQ boost | +6 dB @ 1 kHz | +8 dB sub-bass @ 80 Hz | +8 dB presence @ 3 kHz |
| Compressor | 4:1, -18 dBFS | 6:1, -20 dBFS | 10:1, -24 dBFS |
| Reverb | — | 40 ms room | 60 ms plate |
| Drum layer | 120 BPM rock beat | 90 BPM boom-bap | 180 BPM blast-beat |

### Integrating an AI model

The genre pipeline exposes an `_ai_hook()` function in `musicgen/genre.py`.  
Replace it with a call to any model (e.g. MusicGen, Stable Audio) to upgrade quality:

```python
# musicgen/genre.py — _ai_hook
from audiocraft.models import MusicGen

def _ai_hook(samples, rate, style):
    model = MusicGen.get_pretrained("facebook/musicgen-melody")
    out = model.generate_with_chroma(
        descriptions=[{"rock": "electric guitar rock", "rap": "hip hop beat", "metal": "heavy metal"}[style]],
        melody_wavs=torch.tensor(samples).unsqueeze(0),
        melody_sample_rate=rate,
    )
    return out[0].numpy()
```

### Dependencies

| Package | Purpose |
|---------|---------|
| `numpy` | Signal arrays |
| `scipy` | DSP filters (Butterworth, peaking EQ) |
| `ffmpeg` *(system)* | Video demux + format conversion |
| `demucs` *(optional)* | High-quality vocal separation |

### Running the tests

```bash
pip install pytest numpy scipy
python -m pytest tests/test_music_tools.py -v
```

---

## Features

- ✅ Automatische Extraktion der DB-Credentials aus `xtreammasters.so` Extension
- ✅ Sicheres SSH-Verbindungsmanagement mit Paramiko
- ✅ Erstellt MySQL-User mit konfigurierbaren Berechtigungen
- ✅ Passwort-Eingabe ohne Echo (getpass)
- ✅ Kommandozeilen-Parameter oder interaktive Eingabe
- ✅ Automatische Verbindungstests

## Installation

### Voraussetzungen

```bash
pip install paramiko
```

## Verwendung

### Option 1: Mit Kommandozeilen-Parametern

```bash
python xtreamdb_user_manager.py <SSH_HOST> <SSH_PORT> <SSH_PASSWORD>
```

**Beispiel:**
```bash
python xtreamdb_user_manager.py your-server-ip.com 22 your-ssh-password
```

### Option 2: Interaktiv

```bash
python xtreamdb_user_manager.py
```

Das Script fragt dann nach:
- SSH Host
- SSH Port (Standard: 22)
- SSH Password

## Ablauf

### Schritt 1: DB-Credentials extrahieren
- Verbindet per SSH zum Server
- Lädt PHP-Script zum Server
- Liest Credentials aus `xtreammasters.so` Extension
- Gibt DB-Host, Port, User, Pass und Database-Name aus

### Schritt 2: User-Daten eingeben
- **Username:** fest `masterxtream`
- **Password:** Freie Eingabe (ohne Echo)
- **Zugriffs-Level:**
  - `1` - GRANT ALL PRIVILEGES (voller Admin)
  - `2` - SELECT, INSERT, UPDATE, DELETE (Standard)
  - `3` - SELECT only (Nur Lesen)
- **Host-Zugriff:**
  - `%` - Von überall (empfohlen)
  - `localhost` - Nur lokal
  - Spezifische IP

### Schritt 3: MySQL User erstellen
- Löscht alte User-Einträge
- Erstellt neuen User
- Vergibt Berechtigungen
- Testet Verbindung
- Zeigt alle Grants an

## Sicherheitshinweise

⚠️ **Wichtig:**
- Verwendet SSH-Root-Zugang
- Passwörter werden nicht im Klartext gespeichert
- Temporäre PHP-Dateien werden nach Ausführung gelöscht
- Nutzt sichere SSH-Verbindungen mit Timeout

## Requirements

- Python 3.6+
- paramiko
- SSH-Root-Zugang zum XtreamUI Server
- XtreamMasters Extension installiert auf dem Server

## Fehlerbehebung

### "paramiko nicht installiert"
```bash
pip install paramiko
```

### "PHP binary nicht gefunden"
Der Server muss XtreamUI/XtreamCodes mit PHP unter `/home/x_m/bin/php/bin/php` installiert haben.

### "SSH Authentifizierung fehlgeschlagen"
- Prüfe SSH-Host, Port und Passwort
- Stelle sicher, dass Root-Login erlaubt ist

## Beispiel-Output

```
============================================================
XtreamMasters Database User Manager
============================================================

✓ Parameter von Kommandozeile:
  Host: your-server-ip.com
  Port: 22

============================================================
SCHRITT 1: Extrahiere Datenbank-Credentials
============================================================
Verbinde zu your-server-ip.com:22...
Führe PHP-Script aus...
✓ Credentials gefunden:
  Host: localhost:3306
  User: db_username
  Database: xtream_database

============================================================
SCHRITT 2: Neue User-Daten eingeben
============================================================
Username: masterxtream (fest)
Password: 

Zugriffs-Level:
1) GRANT ALL PRIVILEGES (voller Admin-Zugriff)
2) SELECT, INSERT, UPDATE, DELETE (Standard-Zugriff)
3) SELECT only (Nur Lesen)
Wähle (1-3) [Standard: 1]: 1

Zugriff von:
1) Überall (%) - empfohlen
2) Localhost only
3) Spezifische IP
Wähle (1-3) [Standard: 1]: 1

============================================================
SCHRITT 3: Erstelle MySQL User
============================================================
Führe MySQL User-Erstellung aus...
✓ Verbunden mit Datenbank
✓ Alte User-Einträge gelöscht
✓ User erstellt: masterxtream@%
✓ Rechte vergeben
✓ Privileges aktualisiert

=== Berechtigungen ===
GRANT ALL PRIVILEGES ON *.* TO 'masterxtream'@'%' WITH GRANT OPTION

=== Teste neue Verbindung ===
✓✓✓ VERBINDUNG ERFOLGREICH! ✓✓✓
Host: localhost via TCP/IP
Server: 10.4.32-MariaDB

============================================================
ZUSAMMENFASSUNG
============================================================
✓ User erfolgreich erstellt!

Verbindungs-Details:
  Host:     localhost
  Port:     3306
  User:     masterxtream
  Password: ********
  Database: xtream_database
  Zugriff:  %
```

## Lizenz

Für private und kommerzielle Nutzung.

## Support

Bei Fragen oder Problemen bitte ein Issue erstellen.
