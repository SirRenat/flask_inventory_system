import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import socket

# Config
SMTP_SERVER = 'mail.asauda.ru'
SMTP_PORT_SSL = 465
SMTP_PORT_TLS = 587
USERNAME = 'no-reply@asauda.ru'
PASSWORD = '!Mat604192'

def test_ssl():
    print(f"Testing SSL connection to {SMTP_SERVER}:{SMTP_PORT_SSL}...")
    try:
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT_SSL, timeout=10) as server:
            print("  [OK] Connected via SSL")
            server.login(USERNAME, PASSWORD)
            print("  [OK] Logged in")
            return True
    except Exception as e:
        print(f"  [FAIL] SSL Connection failed: {e}")
        return False

def test_tls():
    print(f"Testing TLS connection to {SMTP_SERVER}:{SMTP_PORT_TLS}...")
    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT_TLS, timeout=10) as server:
            print("  [OK] Connected to server")
            server.starttls()
            print("  [OK] STARTTLS successful")
            server.login(USERNAME, PASSWORD)
            print("  [OK] Logged in")
            return True
    except Exception as e:
        print(f"  [FAIL] TLS Connection failed: {e}")
        return False

if __name__ == "__main__":
    print("--- Starting Email Configuration Check ---")
    ssl_success = test_ssl()
    tls_success = test_tls()
    
    if ssl_success:
        print("\nRECOMMENDATION: Use Port 465 with SSL")
    elif tls_success:
        print("\nRECOMMENDATION: Use Port 587 with TLS")
    else:
        print("\nRECOMMENDATION: Check credentials or firewall/network settings.")
