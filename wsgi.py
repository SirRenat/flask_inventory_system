from app import create_app, db
from app.models import User, Category, Product

app = create_app()

# ПРИНУДИТЕЛЬНОЕ СОЗДАНИЕ ТАБЛИЦ ПРИ ЗАПУСКЕ
with app.app_context():
    try:
        print("🔄 Создание таблиц в базе данных...")
        db.create_all()
        print("✅ Таблицы созданы успешно!")
        
        # Проверяем что таблицы существуют
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        print(f"✅ Таблицы в БД: {tables}")
        
    except Exception as e:
        print(f"❌ Ошибка создания таблиц: {e}")
        print(f"🔍 DATABASE_URL: {app.config['SQLALCHEMY_DATABASE_URI']}")

if __name__ == '__main__':
    app.run()
