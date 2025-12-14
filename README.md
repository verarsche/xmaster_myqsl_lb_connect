# XtreamMasters Database User Manager

Automatisches Tool zum Verwalten von MySQL-Usern in XtreamMasters/XUI-Systemen.

## Features

- **Automatische Credential-Extraktion**: Findet DB-Credentials aus der xtreammasters.so Extension
- **Interaktive User-Erstellung**: Fragt nach Username, Password und Zugriffsrechten
- **Flexible Berechtigungen**: 
  - GRANT ALL PRIVILEGES (voller Admin)
  - Standard-Zugriff (SELECT, INSERT, UPDATE, DELETE)
  - Read-Only (SELECT only)
- **Zugriffskontrolle**: Von überall (%), localhost oder spezifische IP
- **Automatischer Test**: Validiert die neue Verbindung

## Requirements

```bash
pip install paramiko
```

## Installation

```bash
git clone <dein-repo>
cd <dein-repo>
pip install paramiko
```

## Usage

```bash
python xtreamdb_user_manager.py
```

Das Script fragt nach:
1. SSH-Credentials (Server wo XtreamMasters läuft)
2. Neuer Username
3. Neues Password
4. Zugriffs-Level (1-3)
5. Host-Einschränkung (%, localhost, IP)

## Beispiel

```
XtreamMasters Database User Manager
====================================

SSH Host [212.237.231.243]: 212.237.231.243
SSH User [system_admin]: system_admin
SSH Password [erundsie]: erundsie

============================================================
SCHRITT 1: Extrahiere Datenbank-Credentials
============================================================
✓ Credentials gefunden:
  Host: 117.55.203.215:7999
  User: xtream_masters_user_3
  Database: xtreammasters

============================================================
SCHRITT 2: Neue User-Daten eingeben
============================================================
Username: myadmin
Password: securepass123

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
✓ Verbunden mit Datenbank
✓ Alte User-Einträge gelöscht
✓ User erstellt: myadmin@%
✓ Rechte vergeben
✓ Privileges aktualisiert

=== Berechtigungen ===
GRANT ALL PRIVILEGES ON *.* TO `myadmin`@`%` WITH GRANT OPTION

=== Teste neue Verbindung ===
✓✓✓ VERBINDUNG ERFOLGREICH! ✓✓✓
Host: 117.55.203.215 via TCP/IP
Server: 5.5.5-10.6.22-MariaDB-ubu2204

============================================================
ZUSAMMENFASSUNG
============================================================
✓✓✓ USER ERFOLGREICH ERSTELLT! ✓✓✓

Username: myadmin
Password: securepass123
Host: %

Connection String:
mysql -h 117.55.203.215 -P 7999 -u myadmin -psecurepass123 xtreammasters
```

## Wie es funktioniert

1. **Credential-Extraktion**:
   - Verbindet per SSH zum XtreamMasters Server
   - Lädt xtreammasters.so PHP Extension
   - Nutzt PHP Reflection API um private Methode `aeba41ad0a76b7698b828f34f6be6c10()` aufzurufen
   - Diese Methode gibt ein Array mit [Host, Port, User, Password, Database] zurück

2. **User-Erstellung**:
   - Löscht existierende User-Einträge (falls vorhanden)
   - Erstellt neuen MySQL User mit gewählten Credentials
   - Vergibt die gewählten Berechtigungen
   - Flushed Privileges
   - Testet die neue Verbindung

3. **Sicherheit**:
   - Alle temporären PHP-Dateien werden nach Ausführung gelöscht
   - SSH-Verbindung wird nach Nutzung geschlossen
   - Keine Credentials werden gespeichert

## Zugriffs-Levels

### Level 1: GRANT ALL PRIVILEGES
```sql
GRANT ALL PRIVILEGES ON *.* TO 'user'@'host' WITH GRANT OPTION
```
- Voller Admin-Zugriff
- Kann andere User erstellen
- Kann alle Datenbanken verwalten

### Level 2: Standard-Zugriff
```sql
GRANT SELECT, INSERT, UPDATE, DELETE ON *.* TO 'user'@'host'
```
- Standard CRUD-Operationen
- Keine DDL (CREATE/DROP TABLE)
- Keine User-Verwaltung

### Level 3: Read-Only
```sql
GRANT SELECT ON *.* TO 'user'@'host'
```
- Nur Lesen
- Keine Änderungen möglich
- Sicher für Reporting/Monitoring

## Troubleshooting

**Problem**: "Extension class not found"
- Lösung: Prüfe ob xtreammasters.so existiert unter `/home/x_m/bin/php/lib/php/extensions/`

**Problem**: "Access denied for user"
- Lösung: Prüfe SSH-Credentials und ob Extension-Zugriff funktioniert

**Problem**: "Host is not allowed to connect"
- Lösung: Nutze Host '%' für Zugriff von überall

## License

MIT License - Free to use and modify

## Author

Created for XtreamMasters/XUI Database Management
