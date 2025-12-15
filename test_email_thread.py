from app import create_app
from app.email import send_email
import time

app = create_app()

def test_ajax_send():
    print("--- Testing App Context Email Sending ---")
    with app.app_context():
        # Use a dummy email but real credentials from config
        recipient = "aslan@asauda.ru" # sending to self or similar for test
        print(f"Sending email to {recipient}...")
        
        # We don't have templates rendered here easily without request context for url_for, 
        # but send_email handles text/html kwargs.
        
        send_email(
            to=recipient,
            subject="Integration Test",
            template="confirm_email", # won't find template likely if not in right request context/folder, but let's see logic
            text_body="This is a test email from the threaded sender.",
            html_body="<h1>Test</h1><p>This is a test.</p>"
        )
        
        print("Function returned (non-blocking verification). Waiting 5s for thread...")
        time.sleep(5)
        print("Done.")

if __name__ == "__main__":
    test_ajax_send()
