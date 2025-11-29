import os
import shutil
from app import create_app, db
from app.models import Category
from werkzeug.security import generate_password_hash

def final_reset():
    """Полный сброс базы данных с правильной структурой"""
    
    print("🧹 ПОЛНЫЙ СБРОС БАЗЫ ДАННЫХ...")
    
    # Удаляем все возможные файлы базы
    db_files = [
        'instance/app.db',
        'app.db', 
        'test.db',
        'instance'
    ]
    
    for db_path in db_files:
        if os.path.exists(db_path):
            if os.path.isfile(db_path):
                os.remove(db_path)
                print(f"🗑️ Удален файл: {db_path}")
            else:
                shutil.rmtree(db_path)
                print(f"🗑️ Удалена папка: {db_path}")
    
    # Создаем приложение
    app = create_app()
    
    with app.app_context():
        # Создаем таблицы с актуальной структурой
        db.create_all()
        print("✅ Таблицы созданы с актуальной структурой")
        
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
        
        db.session.commit()
        
        print("✅ База данных полностью пересоздана")
        print("🎯 Теперь запустите: python app.py")
        print("👤 Администратор будет создан автоматически при запуске")

if __name__ == "__main__":
    final_reset()