# recreate_tables.py
from app import create_app, db
from app.models import User, Category, Product

app = create_app()

with app.app_context():
    print("🗑️ Очистка и создание таблиц")
    print("=" * 50)
    
    try:
        # Удаляем все таблицы (осторожно!)
        db.drop_all()
        print("✅ Старые таблицы удалены")
        
        # Создаем все таблицы заново
        db.create_all()
        print("✅ Все таблицы созданы заново")
        
        # Проверяем
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        
        print(f"\n📊 Создано таблиц: {len(tables)}")
        expected_tables = ['user', 'category', 'product']
        
        for table in sorted(tables):
            if table in expected_tables:
                print(f"  ✅ {table}")
            else:
                print(f"  ⚠️ {table} (неожиданная таблица)")
        
        # Проверяем отсутствие нужных таблиц
        missing = [t for t in expected_tables if t not in tables]
        if missing:
            print(f"\n❌ Отсутствуют таблицы: {missing}")
        else:
            print("\n🎉 Все необходимые таблицы созданы!")
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()