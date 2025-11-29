import os
import shutil
from app import create_app, db
from app.models import User, Product, Category
from werkzeug.security import generate_password_hash

def reset_database():
    print("🔄 Начинаем полный сброс базы данных...")
    
    # Удаляем базу данных
    db_path = 'instance/app.db'
    if os.path.exists(db_path):
        os.remove(db_path)
        print("🗑️ База данных удалена")
    
    # Удаляем папку миграций
    migrations_path = 'migrations'
    if os.path.exists(migrations_path):
        shutil.rmtree(migrations_path)
        print("🗑️ Папка миграций удалена")
    
import os
import shutil
from app import create_app, db
from app.models import User, Product, Category
from werkzeug.security import generate_password_hash

def reset_database():
    print("🔄 Начинаем полный сброс базы данных...")
    
    # Удаляем базу данных
    db_path = 'instance/app.db'
    if os.path.exists(db_path):
        os.remove(db_path)
        print("🗑️ База данных удалена")
    
    # Удаляем папку миграций
    migrations_path = 'migrations'
    if os.path.exists(migrations_path):
        shutil.rmtree(migrations_path)
        print("🗑️ Папка миграций удалена")
    
    # Создаем приложение
    app = create_app()
    
    with app.app_context():
        print("🔧 Создаем таблицы с новой структурой...")
        # Принудительно создаем таблицы по новой схеме
        db.drop_all()  # Удаляем все таблицы если есть
        db.create_all()  # Создаем заново
        print("✅ Таблицы созданы по новой схеме")
        
        # Создаем администратора
        print("👑 Создаем администратора...")
        admin_user = User(
            email='admin@example.com',
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
        
        # Создаем тестовые категории
        print("📂 Создаем категории...")
        categories = ['Электроника', 'Оборудование', 'Мебель', 'Стройматериалы']
        for cat_name in categories:
            db.session.add(Category(name=cat_name))
        
        db.session.commit()
        print("✅ Администратор и категории созданы")
        print("🎉 База данных полностью пересоздана!")
        print("\n📝 Данные для входа:")
        print("   Email: admin@example.com")
        print("   Пароль: admin123")

if __name__ == '__main__':
    reset_database()