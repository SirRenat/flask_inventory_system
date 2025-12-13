# check.py
import sys
import os

print("🔍 Проверяем таблицы в базе данных...")
print("=" * 50)

try:
    # Добавляем текущую папку в путь Python
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    
    # Импортируем Flask app
    from app import create_app
    from sqlalchemy import inspect
    
    # Создаем приложение
    app = create_app()
    
    # Проверяем таблицы
    with app.app_context():
        inspector = inspect(app.extensions['sqlalchemy'].db.engine)
        tables = inspector.get_table_names()
        
        print("📋 ТАБЛИЦЫ В БАЗЕ ДАННЫХ:")
        print("-" * 30)
        
        for table in sorted(tables):
            print(f"  • {table}")
        
        print("-" * 30)
        
        if 'review' in tables:
            print("✅ Таблица 'review' ЕСТЬ!")
        else:
            print("❌ Таблица 'review' ОТСУТСТВУЕТ")
            
        print("=" * 50)
        
except ImportError as e:
    print(f"❌ Ошибка импорта: {e}")
except Exception as e:
    print(f"❌ Другая ошибка: {e}")