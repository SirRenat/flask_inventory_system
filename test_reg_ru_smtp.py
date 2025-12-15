import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def verify_email_connection():
    # Settings provided by user (UPDATED)
    MAIL_SERVER = 'mail.hosting.reg.ru'
    MAIL_PORT = 465
    MAIL_USERNAME = 'no-reply@asauda.ru'
    MAIL_PASSWORD = '!Mat604192'
    
    print(f"Testing connection to {MAIL_SERVER}:{MAIL_PORT}...")
    
    try:
        # Create a simple message
        msg = MIMEMultipart()
        msg['From'] = MAIL_USERNAME
        msg['To'] = 'no-reply@asauda.ru' # Send to self to test
        msg['Subject'] = 'SMTP Connection Test (Reg.ru)'
        msg.attach(MIMEText('This is a test email to verify SMTP settings by sending to self.', 'plain'))
        
        # Connect using SMTP_SSL
        print(f"Connecting to {MAIL_SERVER}...")
        with smtplib.SMTP_SSL(MAIL_SERVER, MAIL_PORT, timeout=30) as server:
            print("Connected. Logging in...")
            server.login(MAIL_USERNAME, MAIL_PASSWORD)
            print("Logged in. Sending message...")
            server.sendmail(MAIL_USERNAME, [msg['To']], msg.as_string())
            print("[OK] Message sent successfully!")
            
    except Exception as e:
        print(f"[FAIL] Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    verify_email_connection()
