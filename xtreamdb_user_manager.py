#!/usr/bin/env python3
"""
XtreamMasters Database User Manager
Findet automatisch die Datenbank-Credentials und erstellt neue Admin-User

Usage: python xtreamdb_user_manager.py <SSH_HOST> <SSH_PORT> <SSH_PASSWORD>
Beispiel: python xtreamdb_user_manager.py 89.105.194.222 22 xKHcjijwWkfsKy
"""

import os
import sys
import getpass

try:
    import paramiko
except ImportError:
    print("❌ Fehler: paramiko nicht installiert")
    print("Installation: pip install paramiko")
    sys.exit(1)


def extract_db_credentials(ssh_host, ssh_port, ssh_user, ssh_pass):
    """
    Extrahiert Datenbank-Credentials aus xtreammasters.so Extension
    """
    print("=" * 60)
    print("SCHRITT 1: Extrahiere Datenbank-Credentials")
    print("=" * 60)
    
    php_code = '''<?php
// Lade Extension - versuche verschiedene Varianten
$extensions = [
    '/home/x_m/bin/php/lib/php/extensions/no-debug-non-zts-20190902/xtreamaster.so',
    '/home/x_m/bin/php/lib/php/extensions/no-debug-non-zts-20190902/xtreammasters.so'
];

$loaded = false;
foreach ($extensions as $ext) {
    if (file_exists($ext)) {
        try {
            dl($ext);
            $loaded = true;
            echo "[OK] Extension geladen: $ext\\n";
            break;
        } catch (Exception $e) {
            continue;
        }
    }
}

if (!$loaded && !extension_loaded('xtreammasters')) {
    die("ERROR: Extension konnte nicht geladen werden\\n");
}

$className = 'Xtreammasters\\\\Db8888b0282da86ddecc9d6edecac6a5';

if (!class_exists($className)) {
    die("ERROR: Extension class not found\\n");
}

$obj = new $className();

// Methode die Credentials zurückgibt
$method = 'aeba41ad0a76b7698b828f34f6be6c10';

try {
    $reflect = new ReflectionMethod($className, $method);
    $reflect->setAccessible(true);
    $result = $reflect->invokeArgs($obj, []);
    
    if (is_array($result) && count($result) >= 5) {
        // Format: [host, port, user, password, database]
        echo "DB_HOST=" . $result[0] . "\\n";
        echo "DB_PORT=" . $result[1] . "\\n";
        echo "DB_USER=" . $result[2] . "\\n";
        echo "DB_PASS=" . $result[3] . "\\n";
        echo "DB_NAME=" . $result[4] . "\\n";
    } else {
        die("ERROR: Invalid credentials format\\n");
    }
} catch (Exception $e) {
    die("ERROR: " . $e->getMessage() . "\\n");
}
?>
'''
    
    try:
        print(f"Verbinde zu {ssh_host}:{ssh_port}...")
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(ssh_host, port=ssh_port, username=ssh_user, password=ssh_pass, timeout=10)
        
        # Prüfe ob PHP existiert
        stdin, stdout, stderr = ssh.exec_command('test -f /home/x_m/bin/php/bin/php && echo OK')
        if stdout.read().decode().strip() != 'OK':
            print("✗ PHP binary nicht gefunden unter /home/x_m/bin/php/bin/php")
            ssh.close()
            return None
        
        sftp = ssh.open_sftp()
        remote_php = '/tmp/extract_creds.php'
        temp_php = 'temp_extract.php'
        
        with open(temp_php, 'w') as f:
            f.write(php_code)
        
        sftp.put(temp_php, remote_php)
        sftp.close()
        os.remove(temp_php)
        
        print("Führe PHP-Script aus...")
        stdin, stdout, stderr = ssh.exec_command(f'/home/x_m/bin/php/bin/php {remote_php}')
        output = stdout.read().decode('utf-8')
        error = stderr.read().decode('utf-8')
        
        ssh.exec_command(f'rm -f {remote_php}')
        ssh.close()
        
        if error:
            print(f"⚠️ Fehler-Output: {error}")
        
        credentials = {}
        for line in output.strip().split('\n'):
            if '=' in line:
                key, value = line.split('=', 1)
                credentials[key] = value
        
        if all(k in credentials for k in ['DB_HOST', 'DB_PORT', 'DB_USER', 'DB_PASS', 'DB_NAME']):
            print(f"✓ Credentials gefunden:")
            print(f"  Host: {credentials['DB_HOST']}:{credentials['DB_PORT']}")
            print(f"  User: {credentials['DB_USER']}")
            print(f"  Database: {credentials['DB_NAME']}")
            return credentials
        else:
            print("✗ Fehler beim Extrahieren der Credentials")
            print(f"Output: {output}")
            return None
            
    except Exception as e:
        print(f"✗ Fehler: {e}")
        return None


def get_user_input():
    """
    Fragt Benutzer nach neuen User-Daten
    """
    print("\n" + "=" * 60)
    print("SCHRITT 2: Neue User-Daten eingeben")
    print("=" * 60)
    
    # Username ist fest
    username = "masterxtream"
    print(f"Username: {username} (fest)")
    
    password = getpass.getpass("Password: ").strip()
    if not password:
        print("✗ Password darf nicht leer sein")
        sys.exit(1)
    
    print("\nZugriffs-Level:")
    print("1) GRANT ALL PRIVILEGES (voller Admin-Zugriff)")
    print("2) SELECT, INSERT, UPDATE, DELETE (Standard-Zugriff)")
    print("3) SELECT only (Nur Lesen)")
    
    access_choice = input("Wähle (1-3) [Standard: 1]: ").strip() or "1"
    
    access_levels = {
        "1": "GRANT ALL PRIVILEGES ON *.* TO '{}'@'{}' WITH GRANT OPTION",
        "2": "GRANT SELECT, INSERT, UPDATE, DELETE ON *.* TO '{}'@'{}'",
        "3": "GRANT SELECT ON *.* TO '{}'@'{}'"
    }
    
    grant_template = access_levels.get(access_choice, access_levels["1"])
    
    print("\nZugriff von:")
    print("1) Überall (%) - empfohlen")
    print("2) Localhost only")
    print("3) Spezifische IP")
    
    host_choice = input("Wähle (1-3) [Standard: 1]: ").strip() or "1"
    
    if host_choice == "1":
        host = "%"
    elif host_choice == "2":
        host = "localhost"
    elif host_choice == "3":
        host = input("IP-Adresse: ").strip()
    else:
        host = "%"
    
    return {
        'username': username,
        'password': password,
        'host': host,
        'grant_template': grant_template
    }


def create_mysql_user(ssh_host, ssh_port, ssh_user, ssh_pass, db_creds, user_data):
    """
    Erstellt neuen MySQL User
    """
    print("\n" + "=" * 60)
    print("SCHRITT 3: Erstelle MySQL User")
    print("=" * 60)
    
    # Escape Sonderzeichen für PHP
    db_pass_escaped = db_creds["DB_PASS"].replace("'", "\\'")
    new_pass_escaped = user_data["password"].replace("'", "\\'")
    
    php_code = f'''<?php
$link = mysqli_init();
if (!mysqli_real_connect($link, '{db_creds["DB_HOST"]}', '{db_creds["DB_USER"]}', 
                          '{db_pass_escaped}', '{db_creds["DB_NAME"]}', 
                          {db_creds["DB_PORT"]})) {{
    die("ERROR: " . mysqli_connect_error() . "\\n");
}}

echo "[OK] Verbunden mit Datenbank\\n";

$new_user = '{user_data["username"]}';
$new_pass = '{new_pass_escaped}';
$new_host = '{user_data["host"]}';

// Drop existing user
$drop_queries = [
    "DROP USER IF EXISTS '$new_user'@'%'",
    "DROP USER IF EXISTS '$new_user'@'localhost'",
    "DROP USER IF EXISTS '$new_user'@'$new_host'"
];

foreach ($drop_queries as $query) {{
    @mysqli_query($link, $query);
}}

echo "[OK] Alte User-Einträge gelöscht\\n";

// Create new user with GRANT (kompatibel mit älteren MySQL Versionen)
$grant = "{user_data["grant_template"]}";
$grant_query = sprintf($grant, $new_user, $new_host);

// Versuche CREATE USER + GRANT
$create = "CREATE USER IF NOT EXISTS '$new_user'@'$new_host' IDENTIFIED BY '$new_pass'";
if (!mysqli_query($link, $create)) {{
    echo "INFO: " . mysqli_error($link) . "\\n";
}}

echo "[OK] User erstellt: $new_user@$new_host\\n";

// Grant privileges - versuche mehrere Varianten für Kompatibilität
if (mysqli_query($link, $grant_query)) {{
    echo "[OK] Rechte vergeben\\n";
}} else {{
    // Fallback für ältere MySQL Versionen - grant auf alle Datenbanken
    $fallback_grant = "GRANT ALL PRIVILEGES ON *.* TO '$new_user'@'$new_host' IDENTIFIED BY '$new_pass' WITH GRANT OPTION";
    if (mysqli_query($link, $fallback_grant)) {{
        echo "[OK] Rechte vergeben (Fallback-Methode)\\n";
    }} else {{
        echo "ERROR: " . mysqli_error($link) . "\\n";
    }}
}}

// Flush privileges
mysqli_query($link, "FLUSH PRIVILEGES");
echo "[OK] Privileges aktualisiert\\n";

// Show grants - mit error handling
echo "\\n=== Berechtigungen ===\\n";
$result = @mysqli_query($link, "SHOW GRANTS FOR '$new_user'@'$new_host'");
if ($result) {{
    while ($row = mysqli_fetch_row($result)) {{
        echo $row[0] . "\\n";
    }}
}} else {{
    echo "INFO: Kann Grants nicht anzeigen (Normal bei älteren MySQL Versionen)\\n";
}}

// Test connection
echo "\\n=== Teste neue Verbindung ===\\n";
$test = mysqli_init();
if (mysqli_real_connect($test, '{db_creds["DB_HOST"]}', '$new_user', '$new_pass', 
                         '{db_creds["DB_NAME"]}', {db_creds["DB_PORT"]})) {{
    echo "[SUCCESS] VERBINDUNG ERFOLGREICH!\\n";
    echo "Host: " . mysqli_get_host_info($test) . "\\n";
    echo "Server: " . mysqli_get_server_info($test) . "\\n";
    mysqli_close($test);
}} else {{
    echo "[ERROR] Test-Verbindung fehlgeschlagen\\n";
}}

mysqli_close($link);
?>
'''
    
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(ssh_host, username=ssh_user, password=ssh_pass)
        
        sftp = ssh.open_sftp()
        remote_php = '/tmp/create_user.php'
        temp_php = 'temp_create_user.php'
        
        with open(temp_php, 'w') as f:
            f.write(php_code)
        
        sftp.put(temp_php, remote_php)
        sftp.close()
        os.remove(temp_php)
        
        print("Führe MySQL User-Erstellung aus...")
        stdin, stdout, stderr = ssh.exec_command(f'/home/x_m/bin/php/bin/php {remote_php}')
        output = stdout.read().decode('utf-8', errors='replace')
        error = stderr.read().decode('utf-8', errors='replace')
        
        ssh.exec_command(f'rm -f {remote_php}')
        ssh.close()
        
        print(output)
        if error:
            print(f"Fehler: {error}")
        
        return "[SUCCESS] VERBINDUNG ERFOLGREICH!" in output
            
    except Exception as e:
        print(f"✗ Fehler: {e}")
        return False


def main():
    print("=" * 60)
    print("XtreamMasters Database User Manager")
    print("=" * 60)
    
    # Kommandozeilen-Argumente prüfen
    if len(sys.argv) == 4:
        SSH_HOST = sys.argv[1]
        SSH_PORT = int(sys.argv[2])
        SSH_PASS = sys.argv[3]
        print(f"\n✓ Parameter von Kommandozeile:")
        print(f"  Host: {SSH_HOST}")
        print(f"  Port: {SSH_PORT}")
    else:
        print("\nUsage: python xtreamdb_user_manager.py <HOST> <PORT> <PASSWORD>")
        print("Beispiel: python xtreamdb_user_manager.py 89.105.194.222 22 xKHcjijwWkfsKy")
        print("\nOder manuelle Eingabe:")
        SSH_HOST = input("\nSSH Host: ").strip()
        if not SSH_HOST:
            print("✗ Host darf nicht leer sein")
            sys.exit(1)
        
        SSH_PORT = input("SSH Port [22]: ").strip() or "22"
        try:
            SSH_PORT = int(SSH_PORT)
        except ValueError:
            print("✗ Port muss eine Zahl sein")
            sys.exit(1)
        
        SSH_PASS = getpass.getpass("SSH Password: ").strip()
        if not SSH_PASS:
            print("✗ Password darf nicht leer sein")
            sys.exit(1)
    
    SSH_USER = "root"  # Immer root
    
    # Schritt 1: DB Credentials extrahieren
    db_creds = extract_db_credentials(SSH_HOST, SSH_PORT, SSH_USER, SSH_PASS)
    if not db_creds:
        print("\n✗ Konnte Datenbank-Credentials nicht extrahieren")
        sys.exit(1)
    
    # Schritt 2: User-Daten eingeben
    user_data = get_user_input()
    
    # Schritt 3: User erstellen
    success = create_mysql_user(SSH_HOST, SSH_PORT, SSH_USER, SSH_PASS, db_creds, user_data)
    
    # Zusammenfassung
    print("\n" + "=" * 60)
    print("ZUSAMMENFASSUNG")
    print("=" * 60)
    
    if success:
        print("✓ User erfolgreich erstellt!")
        print(f"\nVerbindungs-Details:")
        print(f"  Host:     {db_creds['DB_HOST']}")
        print(f"  Port:     {db_creds['DB_PORT']}")
        print(f"  User:     {user_data['username']}")
        print(f"  Password: {user_data['password']}")
        print(f"  Database: {db_creds['DB_NAME']}")
        print(f"  Zugriff:  {user_data['host']}")
    else:
        print("✗ User-Erstellung fehlgeschlagen")
        sys.exit(1)


if __name__ == "__main__":
    main()
