print("🔄 Запуск миграции для продакшн...")

from app import create_app, db

app = create_app()

with app.app_context():
    print("🔍 Проверяем базу данных...")
    
    try:
        # Добавляем колонку status если её нет
        print("➕ Добавляем колонку status...")
        db.session.execute('ALTER TABLE product ADD COLUMN IF NOT EXISTS status INTEGER DEFAULT 1')
        
        # Добавляем колонку expires_at если её нет
        print("➕ Добавляем колонку expires_at...")
        db.session.execute('ALTER TABLE product ADD COLUMN IF NOT EXISTS expires_at TIMESTAMP')
        
        # Сохраняем изменения
        db.session.commit()
        print("✅ Миграция успешно завершена!")
        print("✅ Колонки status и expires_at добавлены в таблицу product")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        db.session.rollback()