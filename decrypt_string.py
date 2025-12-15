import base64
import paramiko
import os

encrypted = "PeIm/VQqh1BSPwQp2fVJbS347JvqKak/v6pzY1H6sIKVgxzZZg+c4ufpl60eC4Pvp3+sefE1kKBzOg7rARSMjw=="

print("=" * 60)
print("Entschlüssele String")
print("=" * 60)
print(f"Input: {encrypted}\n")

# Methode 1: Base64 dekodieren
print("=== Methode 1: Base64 dekodieren ===")
try:
    decoded = base64.b64decode(encrypted)
    print(f"Hex: {decoded.hex()}")
    print(f"Bytes: {decoded}")
    try:
        print(f"UTF-8: {decoded.decode('utf-8')}")
    except:
        print("UTF-8: Nicht dekodierbar")
    print()
except Exception as e:
    print(f"Fehler: {e}\n")

# Methode 2: XOR mit license key
print("=== Methode 2: XOR mit License Key ===")
try:
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect('212.237.231.243', username='system_admin', password='erundsie')
    
    sftp = ssh.open_sftp()
    license_data = sftp.file('/home/license').read()
    sftp.close()
    ssh.close()
    
    print(f"License Size: {len(license_data)} bytes")
    
    # XOR Decrypt
    decoded = base64.b64decode(encrypted)
    result = bytearray()
    
    for i, byte in enumerate(decoded):
        key_byte = license_data[i % len(license_data)]
        result.append(byte ^ key_byte)
    
    print(f"XOR Result Hex: {result.hex()}")
    try:
        print(f"XOR Result UTF-8: {result.decode('utf-8')}")
    except:
        print("XOR Result: Nicht lesbar als UTF-8")
        # Versuche printable chars zu finden
        printable = ''.join(chr(b) if 32 <= b <= 126 else '.' for b in result)
        print(f"XOR Result Printable: {printable}")
    print()
    
except Exception as e:
    print(f"Fehler: {e}\n")

# Methode 3: PHP Extension Method nutzen
print("=== Methode 3: PHP Extension Decrypt ===")
php_code = f'''<?php
if (!extension_loaded('xtreammasters')) {{
    dl('/home/x_m/bin/php/lib/php/extensions/no-debug-non-zts-20190902/xtreammasters.so');
}}

$className = 'Xtreammasters\\\\Db8888b0282da86ddecc9d6edecac6a5';
$obj = new $className();

$encrypted = "{encrypted}";

// Alle Methoden durchprobieren
$methods = [
    'a1e66c7d5e7b69ccf5c2166f38f05906', // tokenDecode
    '8f565c03f1e3c6d61e7c5f5b8f7b5c3e', // makeToken
    'c2QDc4NSg2NzUmNGZuZmchbmZyaGokZm', // mystery method
];

foreach ($methods as $method) {{
    try {{
        $reflect = new ReflectionMethod($className, $method);
        $reflect->setAccessible(true);
        
        echo "Method: $method\\n";
        
        // Versuche verschiedene Parameter
        $tests = [
            [$encrypted],
            [base64_decode($encrypted)],
            [$encrypted, 'key'],
            [$encrypted, file_get_contents('/home/license')],
        ];
        
        foreach ($tests as $idx => $params) {{
            try {{
                $result = $reflect->invokeArgs($obj, $params);
                echo "  Test $idx: " . var_export($result, true) . "\\n";
            }} catch (Exception $e) {{
                // Silent
            }}
        }}
    }} catch (Exception $e) {{
        // Method nicht gefunden
    }}
}}

// Direkte openssl Versuche
echo "\\n=== OpenSSL Attempts ===\\n";

$ciphers = ['AES-128-CBC', 'AES-256-CBC', 'DES-EDE3', 'BF-CBC'];
$keys = [
    'xtreammasters',
    file_get_contents('/home/license'),
    substr(file_get_contents('/home/license'), 0, 32),
];

foreach ($ciphers as $cipher) {{
    foreach ($keys as $kidx => $key) {{
        try {{
            $iv_length = openssl_cipher_iv_length($cipher);
            $decoded = base64_decode($encrypted);
            
            if (strlen($decoded) > $iv_length) {{
                $iv = substr($decoded, 0, $iv_length);
                $data = substr($decoded, $iv_length);
                
                $result = openssl_decrypt($data, $cipher, $key, OPENSSL_RAW_DATA, $iv);
                if ($result !== false && strlen($result) > 0) {{
                    echo "SUCCESS: $cipher with key $kidx\\n";
                    echo "Result: $result\\n";
                }}
            }}
        }} catch (Exception $e) {{
            // Silent
        }}
    }}
}}
?>
'''

try:
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect('212.237.231.243', username='system_admin', password='erundsie')
    
    sftp = ssh.open_sftp()
    remote_php = '/tmp/decrypt_string.php'
    temp_php = 'temp_decrypt.php'
    
    with open(temp_php, 'w') as f:
        f.write(php_code)
    
    sftp.put(temp_php, remote_php)
    sftp.close()
    os.remove(temp_php)
    
    stdin, stdout, stderr = ssh.exec_command(f'/home/x_m/bin/php/bin/php {remote_php}')
    output = stdout.read().decode('utf-8')
    
    ssh.exec_command(f'rm -f {remote_php}')
    ssh.close()
    
    print(output)
    
except Exception as e:
    print(f"Fehler: {e}")

print("\n" + "=" * 60)
print("Fertig")
print("=" * 60)
