import paramiko
import os

encrypted = "PeIm/VQqh1BSPwQp2fVJbS347JvqKak/v6pzY1H6sIKVgxzZZg+c4ufpl60eC4Pvp3+sefE1kKBzOg7rARSMjw=="

php_code = f'''<?php
// XUI Encryption Key aus config holen
if (file_exists('/home/xtreamcodes/config')) {{
    $config = file_get_contents('/home/xtreamcodes/config');
    preg_match('/encryption_key["\']\\s*=>\\s*["\'](.*?)["\']/i', $config, $matches);
    if (isset($matches[1])) {{
        $enc_key = $matches[1];
        echo "Found encryption_key: $enc_key\\n\\n";
    }}
}}

// Alternative: aus database config
if (file_exists('/home/xtreamcodes/wwwww/config.php')) {{
    include('/home/xtreamcodes/wwwww/config.php');
    if (defined('ENCRYPTION_KEY')) {{
        $enc_key = ENCRYPTION_KEY;
        echo "Found ENCRYPTION_KEY: $enc_key\\n\\n";
    }}
}}

// Alternative: Standard XUI Key
if (!isset($enc_key)) {{
    $enc_key = 'xtreamcodes';
}}

$encrypted = "{encrypted}";

echo "=== Entschlüssele SSH Passwort ===\\n";
echo "Encrypted: $encrypted\\n\\n";

// XUI Standard Decrypt Funktion
function xui_decrypt($encrypted, $key) {{
    $cipher = "AES-256-CBC";
    $data = base64_decode($encrypted);
    
    // XUI nutzt MD5 hash als key
    $enc_key = md5($key);
    
    // IV ist die ersten 16 bytes
    $iv_length = openssl_cipher_iv_length($cipher);
    $iv = substr($data, 0, $iv_length);
    $encrypted_data = substr($data, $iv_length);
    
    $decrypted = openssl_decrypt($encrypted_data, $cipher, $enc_key, OPENSSL_RAW_DATA, $iv);
    
    return $decrypted;
}}

// Methode 1: Standard XUI Decrypt
echo "=== Methode 1: XUI Standard Decrypt ===\\n";
try {{
    $result = xui_decrypt($encrypted, $enc_key);
    if ($result !== false) {{
        echo "✓ ERFOLG!\\n";
        echo "Passwort: $result\\n\\n";
    }} else {{
        echo "✗ Fehlgeschlagen\\n\\n";
    }}
}} catch (Exception $e) {{
    echo "✗ Fehler: " . $e->getMessage() . "\\n\\n";
}}

// Methode 2: Verschiedene Keys probieren
echo "=== Methode 2: Verschiedene Keys ===\\n";
$possible_keys = [
    'xtreamcodes',
    'xtream_codes',
    'xui',
    'admin',
    'encryption',
];

foreach ($possible_keys as $key) {{
    try {{
        $result = xui_decrypt($encrypted, $key);
        if ($result !== false && strlen($result) > 0 && ctype_print($result)) {{
            echo "✓ SUCCESS mit key: $key\\n";
            echo "Passwort: $result\\n\\n";
            break;
        }}
    }} catch (Exception $e) {{
        // Continue
    }}
}}

// Methode 3: Ohne IV (alte XUI Versionen)
echo "=== Methode 3: Ohne IV (alte Version) ===\\n";
foreach ($possible_keys as $key) {{
    try {{
        $data = base64_decode($encrypted);
        $enc_key = md5($key);
        $result = openssl_decrypt($data, 'AES-256-CBC', $enc_key, OPENSSL_RAW_DATA);
        
        if ($result !== false && strlen($result) > 0 && ctype_print($result)) {{
            echo "✓ SUCCESS mit key: $key (ohne IV)\\n";
            echo "Passwort: $result\\n\\n";
            break;
        }}
    }} catch (Exception $e) {{
        // Continue
    }}
}}

// Methode 4: AES-128-CBC
echo "=== Methode 4: AES-128-CBC ===\\n";
foreach ($possible_keys as $key) {{
    try {{
        $data = base64_decode($encrypted);
        $cipher = 'AES-128-CBC';
        $enc_key = substr(md5($key), 0, 16);
        
        $iv_length = openssl_cipher_iv_length($cipher);
        $iv = substr($data, 0, $iv_length);
        $encrypted_data = substr($data, $iv_length);
        
        $result = openssl_decrypt($encrypted_data, $cipher, $enc_key, OPENSSL_RAW_DATA, $iv);
        
        if ($result !== false && strlen($result) > 0 && ctype_print($result)) {{
            echo "✓ SUCCESS mit key: $key (AES-128)\\n";
            echo "Passwort: $result\\n\\n";
            break;
        }}
    }} catch (Exception $e) {{
        // Continue
    }}
}}

// Methode 5: mcrypt style (sehr alte Versionen)
echo "=== Methode 5: mcrypt Kompatibilität ===\\n";
if (function_exists('mcrypt_decrypt')) {{
    foreach ($possible_keys as $key) {{
        try {{
            $data = base64_decode($encrypted);
            $result = mcrypt_decrypt(MCRYPT_RIJNDAEL_128, md5($key), $data, MCRYPT_MODE_CBC);
            $result = rtrim($result, "\\0");
            
            if (strlen($result) > 0 && ctype_print($result)) {{
                echo "✓ SUCCESS mit key: $key (mcrypt)\\n";
                echo "Passwort: $result\\n\\n";
                break;
            }}
        }} catch (Exception $e) {{
            // Continue
        }}
    }}
}} else {{
    echo "mcrypt nicht verfügbar\\n\\n";
}}

// Methode 6: Aus XUI Database holen falls dort gespeichert
echo "=== Methode 6: Check XUI Database ===\\n";
if (extension_loaded('xtreammasters')) {{
    $className = 'Xtreammasters\\\\Db8888b0282da86ddecc9d6edecac6a5';
    $obj = new $className();
    $method = 'bd2cfa5d95c64155adc788157e5af7e2';
    
    try {{
        $reflect = new ReflectionMethod($className, $method);
        $reflect->setAccessible(true);
        $link = $reflect->invokeArgs($obj, []);
        
        if ($link instanceof mysqli) {{
            // Suche in servers table nach encrypted passwords
            $query = "SELECT * FROM servers WHERE server_ip IS NOT NULL LIMIT 10";
            $result = mysqli_query($link, $query);
            
            echo "Servers in DB:\\n";
            while ($row = mysqli_fetch_assoc($result)) {{
                if (isset($row['ssh_password'])) {{
                    echo "Server " . $row['id'] . ": " . $row['ssh_password'] . "\\n";
                    
                    // Versuche zu entschlüsseln
                    foreach ($possible_keys as $key) {{
                        $decrypted = xui_decrypt($row['ssh_password'], $key);
                        if ($decrypted && ctype_print($decrypted)) {{
                            echo "  Decrypted: $decrypted (key: $key)\\n";
                        }}
                    }}
                }}
            }}
        }}
    }} catch (Exception $e) {{
        echo "Konnte nicht auf DB zugreifen\\n";
    }}
}}

echo "\\n=== Fertig ===\\n";
?>
'''

try:
    print("Verbinde zu Server...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect('212.237.231.243', username='system_admin', password='erundsie')
    
    sftp = ssh.open_sftp()
    remote_php = '/tmp/decrypt_ssh_password.php'
    temp_php = 'temp_decrypt_ssh.php'
    
    with open(temp_php, 'w') as f:
        f.write(php_code)
    
    sftp.put(temp_php, remote_php)
    sftp.close()
    os.remove(temp_php)
    
    print("Fuehre Entschluesselung aus...\n")
    stdin, stdout, stderr = ssh.exec_command(f'/home/x_m/bin/php/bin/php {remote_php}')
    output = stdout.read().decode('utf-8', errors='replace')
    
    ssh.exec_command(f'rm -f {remote_php}')
    ssh.close()
    
    # Replace checkmarks for Windows console
    output = output.replace('✓', '[OK]').replace('✗', '[X]')
    print(output)
    
except Exception as e:
    print(f"✗ Fehler: {e}")
