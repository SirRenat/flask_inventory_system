import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def verify_email_connection():
    # Settings from config (hardcoded for independent verification)
    MAIL_SERVER = 'mail.hosting.reg.ru'
    MAIL_PORT = 465
    MAIL_USERNAME = 'no-reply@asauda.ru'
    MAIL_PASSWORD = '!Mat604192' # Using the one from config default
    
    print(f"Testing connection to {MAIL_SERVER}:{MAIL_PORT}...")
    
    try:
        # Create a simple message
        msg = MIMEMultipart()
        msg['From'] = MAIL_USERNAME
        msg['To'] = 'aslan@asauda.ru' # Sending to self equivalent
        msg['Subject'] = 'SMTP Connection Test'
        msg.attach(MIMEText('This is a test email to verify SMTP settings.', 'plain'))
        
        # Connect using SMTP_SSL
        with smtplib.SMTP_SSL(MAIL_SERVER, MAIL_PORT, timeout=30) as server:
            print("Connected. Logging in...")
            server.login(MAIL_USERNAME, MAIL_PASSWORD)
            print("Logged in. Sending message...")
            server.sendmail(MAIL_USERNAME, [msg['To']], msg.as_string())
            print("Message sent successfully!")
            
    except Exception as e:
        print(f"FAILED: {e}")

if __name__ == "__main__":
    verify_email_connection()
