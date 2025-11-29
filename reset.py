import os
import sys
from app import create_app, db
from app.models import User, Category, Product
from werkzeug.security import generate_password_hash

def reset_database():
    """Полностью пересоздает базу данных"""
    app = create_app()
    
    with app.app_context():
        print("🔄 Полный сброс базы данных...")
        
        # Удаляем файл базы данных если существует
        db_path = app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', '')
        if os.path.exists(db_path):
            os.remove(db_path)
            print(f"🗑️ Удален файл базы: {db_path}")
        
        # Создаем все таблицы
        db.create_all()
        print("✅ Таблицы созданы")
        
        # Создаем категории
        categories = [
            Category(name="Оборудование", description="Промышленное и офисное оборудование"),
            Category(name="Электроника", description="Электронные компоненты и устройства"),
            Category(name="Мебель", description="Офисная и производственная мебель"),
            Category(name="Сырье", description="Производственное сырье и материалы"),
            Category(name="Транспорт", description="Транспортные средства"),
            Category(name="Инструменты", description="Профессиональные инструменты")
        ]
        
        for category in categories:
            db.session.add(category)
        
        # Создаем администратора - проверяем, не существует ли он уже
        admin_email = 'admin@example.com'
        existing_admin = User.query.filter_by(email=admin_email).first()
        if not existing_admin:
            admin = User(
                email=admin_email,
                company_name="Администрация системы",
                inn="0000000000",
                legal_address="г. Москва",
                contact_person="Администратор",
                position="Системный администратор",
                phone="+79990000000",
                industry="it",
                username="admin"
            )
            admin.password_hash = generate_password_hash("admin123")
            db.session.add(admin)
            print("✅ Администратор создан")
        else:
            print("ℹ️ Администратор уже существует")
        
        db.session.commit()
        
        print("✅ База данных полностью пересоздана")
        print("👤 Админ для входа: admin@example.com / admin123")
        print("🎯 Теперь запустите: python app.py")

if __name__ == "__main__":
    reset_database()