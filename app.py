from app import create_app, db
from app.models import User, Category, Product
import json
from werkzeug.security import generate_password_hash
from flask import render_template
import os

app = create_app()
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.jinja_env.auto_reload = True

def migrate_database():
    """Автоматическая миграция базы данных"""
    print("[INFO] Проверяем необходимость миграции...")
    
    try:
        # Проверяем существование колонки status
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns('product')]
        
        if 'status' not in columns:
            print("[INFO] Обнаружена старая структура БД, применяем миграцию...")
            
            # Добавляем колонку status
            db.session.execute('ALTER TABLE product ADD COLUMN status INTEGER DEFAULT 1')
            print("[OK] Добавлена колонка status")
            
            # Добавляем колонку expires_at
            db.session.execute('ALTER TABLE product ADD COLUMN expires_at TIMESTAMP')
            print("[OK] Добавлена колонка expires_at")
            
            # Обновляем существующие записи
            db.session.execute("UPDATE product SET status = 1 WHERE status IS NULL")
            db.session.execute("UPDATE product SET expires_at = NOW() + INTERVAL '30 days' WHERE expires_at IS NULL")
            
            db.session.commit()
            print("[SUCCESS] Миграция базы данных завершена успешно!")
        else:
            print("[OK] Структура базы данных актуальна")
            
    except Exception as e:
        print(f"[ERROR] Ошибка при миграции: {e}")
        db.session.rollback()

def create_default_categories():
    """Создает готовую структуру категорий для неликвидов из JSON файла"""
    try:
        with open('categories_structure.json', 'r', encoding='utf-8') as f:
            categories_structure = json.load(f)
    except FileNotFoundError:
        print("[ERROR] Файл categories_structure.json не найден")
        # Создаем базовые категории вручную
        categories_structure = [
            {
                "name": "Электроника",
                "description": "Электронные устройства и компоненты",
                "children": [
                    {"name": "Смартфоны", "description": "Мобильные телефоны"},
                    {"name": "Ноутбуки", "description": "Портативные компьютеры"},
                    {"name": "Компьютеры", "description": "Стационарные ПК и комплектующие"}
                ]
            },
            {
                "name": "Одежда", 
                "description": "Одежда и аксессуары",
                "children": [
                    {"name": "Мужская одежда", "description": ""},
                    {"name": "Женская одежда", "description": ""},
                    {"name": "Детская одежда", "description": ""}
                ]
            }
        ]
    
    def create_categories(parent_id=None, categories_list=None):
        for category_data in categories_list:
            # Проверяем, существует ли уже категория с таким именем
            existing_category = Category.query.filter_by(name=category_data['name'], parent_id=parent_id).first()
            if not existing_category:
                category = Category(
                    name=category_data['name'],
                    description=category_data.get('description', ''),
                    parent_id=parent_id
                )
                db.session.add(category)
                db.session.flush()  # Получаем ID созданной категории
                print(f"[OK] Создана категория: {category_data['name']}")
                
                # Рекурсивно создаем дочерние категории
                if 'children' in category_data:
                    create_categories(category.id, category_data['children'])
    
    if Category.query.count() == 0:
        create_categories(None, categories_structure)
        db.session.commit()
        print('[OK] Структура категорий создана')
    else:
        print('[INFO] Категории уже существуют в базе данных')

def setup_database():
    with app.app_context():
        # ВЫПОЛНЯЕМ МИГРАЦИЮ ПЕРВЫМ ДЕЛОМ
        migrate_database()
        
        # Создаем структуру категорий если её нет
        create_default_categories()
        
        # Создаем первого администратора если его нет
        admin_email = 'admin@example.com'
        admin_user = User.query.filter_by(email=admin_email).first()
        if not admin_user:
            hashed_password = generate_password_hash('admin123')
            admin_user = User(
                company_name='Администратор системы',
                email=admin_email,
                password_hash=hashed_password,
                phone='+7 (999) 123-45-67',
                inn='1234567890',
                role='admin'
            )
            db.session.add(admin_user)
            db.session.commit()
            print('[OK] Создан администратор: admin@example.com / admin123')
        
        print("[OK] База данных готова к работе")

# Диагностика путей в контексте приложения
with app.app_context():
    print("=" * 50)
    print("[INFO] ДИАГНОСТИКА ПУТЕЙ:")
    print(f"Текущая рабочая папка: {os.getcwd()}")
    print(f"Папка проекта: {os.path.dirname(os.path.abspath(__file__))}")

    # Проверим конфигурацию
    upload_folder = app.config.get('UPLOAD_FOLDER', 'uploads')
    print(f"UPLOAD_FOLDER из конфига: {upload_folder}")
    print(f"Папка существует: {os.path.exists(upload_folder)}")
    
    # Создаем папку принудительно
    os.makedirs(upload_folder, exist_ok=True)
    print(f"Папка создана/проверена: {upload_folder}")
    
    # Покажем что в папке
    if os.path.exists(upload_folder):
        files = os.listdir(upload_folder)
        print(f"Файлов в папке: {len(files)}")
        for f in files[:5]:  # первые 5 файлов
            print(f"  - {f}")
    print("=" * 50)

setup_database()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80, debug=False)