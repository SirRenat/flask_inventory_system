from app import create_app, db
from app.models import User
from werkzeug.security import generate_password_hash

def create_admin():
    app = create_app()
    
    with app.app_context():
        # Проверяем существующих пользователей
        users = User.query.all()
        print("📋 Существующие пользователи:")
        for user in users:
            print(f"   - {user.email} (роль: {user.role})")
        
        # Создаем администратора если его нет
        admin_email = 'admin@example.com'
        admin_user = User.query.filter_by(email=admin_email).first()
        
        if not admin_user:
            print("👑 Создаем администратора...")
            admin_user = User(
                email=admin_email,
                company_name='Администратор системы',
                inn='0000000000',
                legal_address='г. Москва',
                contact_person='Администратор',
                position='Системный администратор',
                phone='+79990000000',
                industry='it',
                username='admin',
                role='admin'
            )
            admin_user.set_password('admin123')
            db.session.add(admin_user)
            db.session.commit()
            print("✅ Администратор создан!")
        else:
            print("✅ Администратор уже существует")
            # Сбрасываем пароль на случай если забыли
            admin_user.set_password('admin123')
            db.session.commit()
            print("🔑 Пароль сброшен на 'admin123'")
        
        print("\n📝 Данные для входа:")
        print(f"   Email: {admin_email}")
        print("   Пароль: admin123")
        print("\n⚠️ Не забудьте сменить пароль после входа!")

if __name__ == '__main__':
    create_admin()