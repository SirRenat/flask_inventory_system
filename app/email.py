import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import render_template, current_app
from threading import Thread
import logging

logger = logging.getLogger(__name__)

def send_async_email(app, to, subject, html_body, text_body):
    """
    Background task to send email via SMTP (SSL).
    """
    with app.app_context():
        smtp_server = app.config.get('MAIL_SERVER')
        smtp_port = app.config.get('MAIL_PORT')
        smtp_user = app.config.get('MAIL_USERNAME')
        smtp_password = app.config.get('MAIL_PASSWORD')
        smtp_sender = app.config.get('MAIL_DEFAULT_SENDER')
        
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = smtp_sender
        msg['To'] = to

        # Attach parts
        if text_body:
            part1 = MIMEText(text_body, 'plain')
            msg.attach(part1)
        if html_body:
            part2 = MIMEText(html_body, 'html')
            msg.attach(part2)

        try:
            # Using SMTP_SSL for port 465
            with smtplib.SMTP_SSL(smtp_server, smtp_port, timeout=20) as server:
                server.login(smtp_user, smtp_password)
                server.sendmail(smtp_sender, to, msg.as_string())
            
            logger.info(f"[Email Thread] Email sent successfully to {to}")
        except Exception as e:
            logger.error(f"[Email Thread] Failed to send email to {to}: {e}")

def send_email(to, subject, template, **kwargs):
    """
    Starts a background thread to send an email.
    """
    app = current_app._get_current_object()
    
    # Render templates
    try:
        html_body = render_template(f'email/{template}.html', **kwargs)
    except Exception:
        html_body = kwargs.get('html_body', '')
        
    try:
        text_body = render_template(f'email/{template}.txt', **kwargs)
    except Exception:
        text_body = kwargs.get('text_body', strip_tags(html_body))
        
    # Prefix subject
    full_subject = app.config.get('MAIL_SUBJECT_PREFIX', '[ASAUDA] ') + subject
    
    # Start thread
    thr = Thread(target=send_async_email, args=[app, to, full_subject, html_body, text_body])
    thr.start()
    return thr

def strip_tags(html):
    import re
    clean = re.compile('<.*?>')
    return re.sub(clean, '', html)
