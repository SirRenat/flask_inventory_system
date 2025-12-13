import os
import sys

def migrate_database():
    print("🚀 ЗАПУСК АВТОМАТИЧЕСКОЙ МИГРАЦИИ...")
    
    try:
        from app import create_app, db
        
        app = create_app()
        
        with app.app_context():
            print("🔍 Проверяем структуру базы данных...")
            
            # Проверяем существование колонки status
            try:
                # Простая проверка - пытаемся получить первую запись
                from app.models import Product
                test_product = Product.query.first()
                if test_product:
                    # Пробуем обратиться к полю status
                    _ = test_product.status
                    print("✅ Колонка status уже существует")
                    return True
            except Exception as e:
                print(f"📋 Колонка status отсутствует: {e}")
            
            print("🔄 Добавляем недостающие колонки...")
            
            try:
                # Добавляем колонку status
                print("➕ Добавляем колонку status...")
                db.session.execute('ALTER TABLE product ADD COLUMN status INTEGER DEFAULT 1')
                
                # Добавляем колонку expires_at
                print("➕ Добавляем колонку expires_at...")
                db.session.execute('ALTER TABLE product ADD COLUMN expires_at TIMESTAMP')
                
                # Обновляем существующие записи
                print("🔄 Обновляем существующие товары...")
                db.session.execute("UPDATE product SET status = 1 WHERE status IS NULL")
                db.session.execute("UPDATE product SET expires_at = NOW() + INTERVAL '30 days' WHERE expires_at IS NULL")
                
                db.session.commit()
                print("✅ МИГРАЦИЯ УСПЕШНО ЗАВЕРШЕНА!")
                print("✅ Колонки status и expires_at добавлены")
                return True
                
            except Exception as e:
                print(f"❌ Ошибка при миграции: {e}")
                db.session.rollback()
                return False
                
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        return False

if __name__ == '__main__':
    success = migrate_database()
    sys.exit(0 if success else 1)