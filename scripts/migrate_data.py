import sqlite3
import json
from datetime import datetime
from werkzeug.security import generate_password_hash

def migrate_from_old_db():
    """Миграция данных из старой БД в новую структуру"""
    
    # Подключаемся к старой БД
    old_conn = sqlite3.connect('old_production.db')
    old_cursor = old_conn.cursor()
    
    # Подключаемся к новой БД
    new_conn = sqlite3.connect('new_production.db')
    new_cursor = new_conn.cursor()
    
    print("🔄 Начинаем миграцию данных...")
    
    # Миграция пользователей
    print("👥 Миграция пользователей...")
    old_cursor.execute("SELECT id, username, email, password_hash FROM user")
    old_users = old_cursor.fetchall()
    
    for user_id, username, email, password_hash in old_users:
        # Создаем организацию на основе username
        new_cursor.execute("""
            INSERT INTO user (email, password_hash, username, company_name, inn, 
                            legal_address, contact_person, position, phone, industry, 
                            is_active, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            email, password_hash, username, 
            f"Организация {username}",  # company_name
            "0000000000",               # inn (заглушка)
            "Адрес не указан",          # legal_address  
            username,                   # contact_person
            "Менеджер",                 # position
            "+79990000000",             # phone
            "other",                    # industry
            True,                       # is_active
            datetime.utcnow()           # created_at
        ))
    
    # Миграция товаров
    print("📦 Миграция товаров...")
    old_cursor.execute("""
        SELECT id, title, description, price, images, created_at, user_id, category_id 
        FROM product
    """)
    old_products = old_cursor.fetchall()
    
    for (prod_id, title, description, price, images, created_at, user_id, category_id) in old_products:
        new_cursor.execute("""
            INSERT INTO product (title, description, price, images, created_at, 
                               is_active, user_id, category_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            title, description, price, images, created_at,
            True,  # is_active
            user_id, category_id
        ))
    
    # Сохраняем изменения
    new_conn.commit()
    
    print("✅ Миграция завершена!")
    print(f"📊 Перенесено:")
    print(f"   - Пользователей: {len(old_users)}")
    print(f"   - Товаров: {len(old_products)}")
    
    old_conn.close()
    new_conn.close()

if __name__ == "__main__":
    migrate_from_old_db()