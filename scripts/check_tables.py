# check_tables.py
from app import create_app, db
from sqlalchemy import inspect

app = create_app()

with app.app_context():
    print("📊 Проверка таблиц в базе данных")
    print("=" * 50)
    
    inspector = inspect(db.engine)
    tables = inspector.get_table_names()
    
    if tables:
        print(f"✅ Найдено таблиц: {len(tables)}")
        for table in tables:
            print(f"  - {table}")
    else:
        print("❌ Таблицы не найдены. Нужно создать.")