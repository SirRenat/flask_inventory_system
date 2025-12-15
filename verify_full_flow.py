import os
import unittest
from unittest.mock import patch
from app import create_app, db
from app.models import User

# Set env to test
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['SECRET_KEY'] = 'test-secret'

class TestAuthFlow(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False 
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.client = self.app.test_client()
        
        with self.app.app_context():
            db.create_all()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    @patch('app.auth.send_email') 
    def test_full_registration_flow(self, mock_send_email):
        print("\n--- Starting Full Registration Flow Test ---")
        
        # 1. Register
        print("1. Registering new user...")
        response = self.client.post('/auth/register', data={
            'email': 'testuser@example.com',
            'username': 'testuser',
            'password': 'password123',
            'confirm_password': 'password123',
            'company_name': 'Test Corp',
            'inn': '1234567890',
            'legal_address': 'Test Address',
            'contact_person': 'Test Person',
            'position': 'Tester',
            'phone': '1234567890',
            'agree_terms': 'y'
        }, follow_redirects=True)
        
        self.assertEqual(response.status_code, 200)
        # Check for success message (utf-8 check)
        responseText = response.data.decode('utf-8')
        if 'Регистрация успешна' in responseText:
            print("   ✅ Registration successful.")
        else:
            print(f"   ❌ Registration failed. Response snippet: {responseText[:100]}")
            self.fail("Registration failed")
        
        # Check if email was sent
        if mock_send_email.called:
             print("   ✅ Email sending triggered.")
        else:
             print("   ❌ Email sending NOT triggered.")
             self.fail("Email not sent")
             
        call_args = mock_send_email.call_args
        args, kwargs = call_args
        # kwargs might contain confirm_url
        confirm_url = kwargs.get('confirm_url')
        print(f"   Captured Link: {confirm_url}")
        
        if not confirm_url:
            self.fail("No confirmation URL found")

        # Extract token from url
        token = confirm_url.split('/')[-1]
        
        # 2. Try to Login (Should fail/Warning)
        print("2. Attempting login before confirmation...")
        response = self.client.post('/auth/login', data={
            'email': 'testuser@example.com',
            'password': 'password123'
        }, follow_redirects=True)
        
        responseText = response.data.decode('utf-8')
        if 'Ваш аккаунт не подтвержден' in responseText:
            print("   ✅ Blocked as expected.")
        else:
            print(f"   ❌ Login allowed or wrong message. Snippet: {responseText[:100]}")
            self.fail("Login should be blocked")

        # 3. Confirm Email
        print("3. Confirming email...")
        response = self.client.get(f'/auth/confirm/{token}', follow_redirects=True)
        responseText = response.data.decode('utf-8')
        
        if 'Ваш аккаунт успешно подтвержден' in responseText:
             print("   ✅ Confirmation successful.")
        elif 'Аккаунт уже подтвержден' in responseText:
             print("   ✅ Confirmation successful (Already confirmed).")
        else:
             print(f"   ❌ Confirmation failed. Snippet: {responseText[:100]}")
             self.fail("Confirmation failed")
        
        # 4. Login Again (Should succeed)
        print("4. Attempting login after confirmation...")
        response = self.client.post('/auth/login', data={
            'email': 'testuser@example.com',
            'password': 'password123'
        }, follow_redirects=True)
        
        responseText = response.data.decode('utf-8')
        if 'Вы успешно вошли в систему' in responseText:
            print("   ✅ Login successful.")
        else:
            print(f"   ❌ Login failed. Snippet: {responseText[:100]}")
            self.fail("Login logic failed after confirmation")

if __name__ == '__main__':
    unittest.main()
