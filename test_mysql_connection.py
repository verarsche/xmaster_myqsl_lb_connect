#!/usr/bin/env python3
import paramiko
import sys
import getpass

# Verbindungsdaten
ssh_host = "45.148.147.18"
ssh_port = 22
ssh_user = "root"
ssh_pass = "zo41ye"

mysql_host = "45.143.222.233"
mysql_port = 7999
mysql_user = "masterxtream"
mysql_db = "xtreammasters"

print(f"Verbinde zu SSH Server {ssh_host}...")

try:
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(ssh_host, port=ssh_port, username=ssh_user, password=ssh_pass, timeout=10)
    
    print(f"✓ SSH Verbindung hergestellt")
    print(f"\nTeste MySQL Verbindung zu {mysql_host}:{mysql_port}...")
    
    # Frage nach Passwort
    mysql_pass = getpass.getpass("MySQL Password für masterxtream: ")
    
    # Escape für PHP
    mysql_pass_escaped = mysql_pass.replace("'", "\\'")
    
    # Test MySQL Verbindung über PHP
    php_code = f'''<?php
$link = mysqli_init();
if (mysqli_real_connect($link, '{mysql_host}', '{mysql_user}', '{mysql_pass_escaped}', '{mysql_db}', {mysql_port})) {{
    echo "[SUCCESS] VERBINDUNG ERFOLGREICH!\\n\\n";
    
    $result = mysqli_query($link, "SELECT VERSION()");
    $row = mysqli_fetch_row($result);
    echo "MySQL Version: " . $row[0] . "\\n";
    
    $result = mysqli_query($link, "SELECT USER()");
    $row = mysqli_fetch_row($result);
    echo "Current User: " . $row[0] . "\\n";
    
    $result = mysqli_query($link, "SELECT DATABASE()");
    $row = mysqli_fetch_row($result);
    echo "Current Database: " . $row[0] . "\\n";
    
    echo "\\n=== User Grants ===\\n";
    $result = mysqli_query($link, "SHOW GRANTS FOR '{mysql_user}'@'%'");
    while ($row = mysqli_fetch_row($result)) {{
        echo $row[0] . "\\n";
    }}
    
    mysqli_close($link);
}} else {{
    echo "ERROR: " . mysqli_connect_error() . "\\n";
    exit(1);
}}
?>'''
    
    # Upload PHP script
    sftp = ssh.open_sftp()
    remote_php = '/tmp/test_mysql.php'
    temp_php = 'temp_test_mysql.php'
    
    with open(temp_php, 'w') as f:
        f.write(php_code)
    
    sftp.put(temp_php, remote_php)
    sftp.close()
    
    import os
    os.remove(temp_php)
    
    # Execute PHP
    cmd = f"/home/x_m/bin/php/bin/php {remote_php}"
    stdin, stdout, stderr = ssh.exec_command(cmd)
    output = stdout.read().decode('utf-8', errors='replace')
    error = stderr.read().decode('utf-8', errors='replace')
    
    # Cleanup
    ssh.exec_command(f'rm -f {remote_php}')
    ssh.close()
    
    if output:
        print("\n" + "="*60)
        print("AUSGABE:")
        print("="*60)
        print(output)
    
    if "ERROR" in output or "ERROR" in error:
        print("\n[X] MySQL Verbindung fehlgeschlagen")
        if error:
            print(f"Fehler: {error}")
        sys.exit(1)
    else:
        print("\n[SUCCESS] MySQL Verbindung ERFOLGREICH!")
        
except Exception as e:
    print(f"\n✗ Fehler: {e}")
    sys.exit(1)
