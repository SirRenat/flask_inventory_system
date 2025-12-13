import os
from app import create_app, db
from app.models import User, Category

def fix_database():
    app = create_app()
    
    with app.app_context():
        print("🔄 Восстановление базы данных...")
        
        # Удаляем все таблицы
        db.drop_all()
        print("✅ Старые таблицы удалены")
        
        # Создаем новые таблицы
        db.create_all()
        print("✅ Новые таблицы созданы")
        
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
        
        # Создаем администратора
        admin = User(
            email="admin@example.com",
            company_name="Администрация системы",
            inn="0000000000",
            legal_address="г. Москва",
            contact_person="Администратор",
            position="Системный администратор",
            phone="+79990000000",
            industry="it",
            username="admin"
        )
        admin.set_password("admin123")
        db.session.add(admin)
        
        db.session.commit()
        
        print("✅ База данных восстановлена")
        print("👤 Админ: admin@example.com / admin123")
        print("🎯 Теперь запустите: python app.py")

if __name__ == "__main__":
    fix_database()
    #ntcn
