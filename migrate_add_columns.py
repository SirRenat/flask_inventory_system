# migrate_add_columns.py
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import Product

app = create_app()

with app.app_context():
    print("🔄 Начинаем миграцию базы данных...")
    
    try:
        # Проверяем существование столбцов
        from sqlalchemy import inspect, text
        inspector = inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns('product')]
        
        print(f"📊 Существующие колонки таблицы product: {columns}")
        
        # Добавляем новые столбцы если их нет
        with db.engine.connect() as conn:
            # Добавляем колонку quantity если её нет
            if 'quantity' not in columns:
                print("➕ Добавляем колонку 'quantity'...")
                conn.execute(text("ALTER TABLE product ADD COLUMN quantity INTEGER DEFAULT 1"))
                print("✅ Колонка 'quantity' добавлена")
            
            # Добавляем колонку manufacturer если её нет
            if 'manufacturer' not in columns:
                print("➕ Добавляем колонку 'manufacturer'...")
                conn.execute(text("ALTER TABLE product ADD COLUMN manufacturer VARCHAR(200)"))
                print("✅ Колонка 'manufacturer' добавлена")
            
            # Фиксируем изменения
            conn.commit()
        
        print("🎉 Миграция успешно завершена!")
        
        # Проверяем результат
        inspector = inspect(db.engine)
        updated_columns = [col['name'] for col in inspector.get_columns('product')]
        print(f"📊 Обновленные колонки таблицы product: {updated_columns}")
        
    except Exception as e:
        print(f"❌ Ошибка миграции: {e}")
        import traceback
        traceback.print_exc()

####
