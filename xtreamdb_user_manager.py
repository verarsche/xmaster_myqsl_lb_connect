#!/usr/bin/env python3
"""
XtreamMasters Database User Manager
Findet automatisch die Datenbank-Credentials und erstellt neue Admin-User
"""

import subprocess
import os
import sys
import paramiko

def extract_db_credentials(ssh_host, ssh_user, ssh_pass):
    """
    Extrahiert Datenbank-Credentials aus xtreammasters.so Extension
    """
    print("=" * 60)
    print("SCHRITT 1: Extrahiere Datenbank-Credentials")
    print("=" * 60)
    
    php_code = '''<?php
// Lade Extension
if (!extension_loaded('xtreammasters')) {
    dl('/home/x_m/bin/php/lib/php/extensions/no-debug-non-zts-20190902/xtreammasters.so');
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
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(ssh_host, username=ssh_user, password=ssh_pass)
        
        # Upload PHP script
        sftp = ssh.open_sftp()
        remote_php = '/tmp/extract_creds.php'
        temp_php = 'temp_extract.php'
        
        with open(temp_php, 'w') as f:
            f.write(php_code)
        
        sftp.put(temp_php, remote_php)
        sftp.close()
        os.remove(temp_php)
        
        # Execute PHP
        stdin, stdout, stderr = ssh.exec_command(f'/home/x_m/bin/php/bin/php {remote_php}')
        output = stdout.read().decode('utf-8')
        
        # Cleanup
        ssh.exec_command(f'rm -f {remote_php}')
        ssh.close()
        
        # Parse output
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
    
    username = input("Username: ").strip()
    if not username:
        print("✗ Username darf nicht leer sein")
        sys.exit(1)
    
    password = input("Password: ").strip()
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


def create_mysql_user(ssh_host, ssh_user, ssh_pass, db_creds, user_data):
    """
    Erstellt neuen MySQL User
    """
    print("\n" + "=" * 60)
    print("SCHRITT 3: Erstelle MySQL User")
    print("=" * 60)
    
    php_code = f'''<?php
$link = mysqli_init();
if (!mysqli_real_connect($link, '{db_creds["DB_HOST"]}', '{db_creds["DB_USER"]}', 
                          '{db_creds["DB_PASS"]}', '{db_creds["DB_NAME"]}', 
                          {db_creds["DB_PORT"]})) {{
    die("ERROR: " . mysqli_connect_error() . "\\n");
}}

echo "✓ Verbunden mit Datenbank\\n";

$new_user = '{user_data["username"]}';
$new_pass = '{user_data["password"]}';
$new_host = '{user_data["host"]}';

// Drop existing user
$drop_queries = [
    "DROP USER IF EXISTS '$new_user'@'%'",
    "DROP USER IF EXISTS '$new_user'@'localhost'",
    "DROP USER IF EXISTS '$new_user'@'$new_host'"
];

foreach ($drop_queries as $query) {{
    mysqli_query($link, $query);
}}

echo "✓ Alte User-Einträge gelöscht\\n";

// Create new user
$create = "CREATE USER '$new_user'@'$new_host' IDENTIFIED BY '$new_pass'";
if (mysqli_query($link, $create)) {{
    echo "✓ User erstellt: $new_user@$new_host\\n";
}} else {{
    die("ERROR: " . mysqli_error($link) . "\\n");
}}

// Grant privileges
$grant = "{user_data["grant_template"]}";
$grant_query = sprintf($grant, $new_user, $new_host);

if (mysqli_query($link, $grant_query)) {{
    echo "✓ Rechte vergeben\\n";
}} else {{
    die("ERROR: " . mysqli_error($link) . "\\n");
}}

// Flush privileges
mysqli_query($link, "FLUSH PRIVILEGES");
echo "✓ Privileges aktualisiert\\n";

// Show grants
echo "\\n=== Berechtigungen ===\\n";
$result = mysqli_query($link, "SHOW GRANTS FOR '$new_user'@'$new_host'");
while ($row = mysqli_fetch_row($result)) {{
    echo $row[0] . "\\n";
}}

// Test connection
echo "\\n=== Teste neue Verbindung ===\\n";
$test = mysqli_init();
if (mysqli_real_connect($test, '{db_creds["DB_HOST"]}', '$new_user', '$new_pass', 
                         '{db_creds["DB_NAME"]}', {db_creds["DB_PORT"]})) {{
    echo "✓✓✓ VERBINDUNG ERFOLGREICH! ✓✓✓\\n";
    echo "Host: " . mysqli_get_host_info($test) . "\\n";
    echo "Server: " . mysqli_get_server_info($test) . "\\n";
    mysqli_close($test);
}} else {{
    echo "✗ Test-Verbindung fehlgeschlagen\\n";
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
        
        # Execute
        stdin, stdout, stderr = ssh.exec_command(f'/home/x_m/bin/php/bin/php {remote_php}')
        output = stdout.read().decode('utf-8')
        
        # Cleanup
        ssh.exec_command(f'rm -f {remote_php}')
        ssh.close()
        
        print(output)
        
        if "✓✓✓ VERBINDUNG ERFOLGREICH!" in output:
            return True
        else:
            return False
            
    except Exception as e:
        print(f"✗ Fehler: {e}")
        return False


def main():
    print("=" * 60)
    print("XtreamMasters Database User Manager")
    print("=" * 60)
    print()
    
    # SSH Credentials
    SSH_HOST = input("SSH Host [212.237.231.243]: ").strip() or "212.237.231.243"
    SSH_USER = input("SSH User [system_admin]: ").strip() or "system_admin"
    SSH_PASS = input("SSH Password [erundsie]: ").strip() or "erundsie"
    
    # Schritt 1: DB Credentials extrahieren
    db_creds = extract_db_credentials(SSH_HOST, SSH_USER, SSH_PASS)
    if not db_creds:
        print("\n✗ Fehler beim Extrahieren der Credentials")
        sys.exit(1)
    
    # Schritt 2: User-Daten eingeben
    user_data = get_user_input()
    
    # Schritt 3: User erstellen
    success = create_mysql_user(SSH_HOST, SSH_USER, SSH_PASS, db_creds, user_data)
    
    # Zusammenfassung
    print("\n" + "=" * 60)
    print("ZUSAMMENFASSUNG")
    print("=" * 60)
    
    if success:
        print(f"✓✓✓ USER ERFOLGREICH ERSTELLT! ✓✓✓")
        print(f"\nUsername: {user_data['username']}")
        print(f"Password: {user_data['password']}")
        print(f"Host: {user_data['host']}")
        print(f"\nConnection String:")
        print(f"mysql -h {db_creds['DB_HOST']} -P {db_creds['DB_PORT']} " +
              f"-u {user_data['username']} -p{user_data['password']} {db_creds['DB_NAME']}")
    else:
        print("✗ Fehler beim Erstellen des Users")
        sys.exit(1)


if __name__ == "__main__":
    main()
