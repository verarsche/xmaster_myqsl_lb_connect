# XtreamMasters Database User Manager

Automatisches Tool zum Extrahieren von Datenbank-Credentials und Erstellen von MySQL-Admin-Usern auf XtreamUI/XtreamCodes Servern.

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
python xtreamdb_user_manager.py 89.105.194.222 22 xKHcjijwWkfsKy
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
  Host: 89.105.194.222
  Port: 22

============================================================
SCHRITT 1: Extrahiere Datenbank-Credentials
============================================================
Verbinde zu 89.105.194.222:22...
Führe PHP-Script aus...
✓ Credentials gefunden:
  Host: localhost:3306
  User: user_iptvpro
  Database: xtream_iptvpro

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
  Database: xtream_iptvpro
  Zugriff:  %
```

## Lizenz

Für private und kommerzielle Nutzung.

## Support

Bei Fragen oder Problemen bitte ein Issue erstellen.
