import os
import sqlite3
import shutil
from datetime import datetime
from werkzeug.security import generate_password_hash

def migrate_production_data():
    """Переносит данные из старой продакшен БД в новую структуру"""
    
    print("🔄 МИГРАЦИЯ ДАННЫХ ПРОДАКШЕН")
    print("=" * 50)
    
    # Пути к базам данных
    old_db_path = 'old_production.db'  # Замените на путь к вашей продакшен БД
    new_db_path = 'instance/app.db'    # Новая база
    
    if not os.path.exists(old_db_path):
        print(f"❌ Старая БД не найдена: {old_db_path}")
        print("📋 Доступные файлы:")
        for file in os.listdir('.'):
            if file.endswith('.db'):
                print(f"   - {file}")
        return
    
    # Создаем бэкап
    backup_path = f'backup_production_{datetime.now().strftime("%Y%m%d_%H%M%S")}.db'
    shutil.copy2(old_db_path, backup_path)
    print(f"✅ Бэкап создан: {backup_path}")
    
    # Подключаемся к базам
    old_conn = sqlite3.connect(old_db_path)
    old_cursor = old_conn.cursor()
    
    new_conn = sqlite3.connect(new_db_path)
    new_cursor = new_conn.cursor()
    
    # Миграция пользователей
    print("👥 Миграция пользователей...")
    old_cursor.execute("SELECT id, username, email, password_hash FROM user")
    old_users = old_cursor.fetchall()
    
    user_id_map = {}  # Для сопоставления старых и новых ID
    
    for old_id, username, email, password_hash in old_users:
        new_cursor.execute("""
            INSERT INTO user (email, password_hash, username, company_name, inn, 
                            legal_address, contact_person, position, phone, industry, 
                            is_active, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            email, 
            password_hash, 
            username,
            f"Организация {username}",  # company_name
            "0000000000",               # inn
            "Адрес будет обновлен",     # legal_address
            username,                   # contact_person
            "Менеджер",                 # position
            "+79990000000",             # phone
            "other",                    # industry
            1,                          # is_active
            datetime.now()              # created_at
        ))
        
        # Получаем новый ID
        new_id = new_cursor.lastrowid
        user_id_map[old_id] = new_id
        print(f"   ✅ {username} -> ID {old_id} → {new_id}")
    
    # Миграция товаров
    print("📦 Миграция товаров...")
    old_cursor.execute("""
        SELECT id, title, description, price, images, created_at, user_id, category_id 
        FROM product
    """)
    old_products = old_cursor.fetchall()
    
    for (old_id, title, description, price, images, created_at, old_user_id, category_id) in old_products:
        new_user_id = user_id_map.get(old_user_id)
        
        if new_user_id:
            new_cursor.execute("""
                INSERT INTO product (title, description, price, images, created_at, 
                                   is_active, user_id, category_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                title, description, price, images, created_at,
                1,  # is_active
                new_user_id, 
                category_id if category_id else None
            ))
            print(f"   ✅ {title} -> пользователь {old_user_id} → {new_user_id}")
        else:
            print(f"   ⚠️ Пропущен: {title} (пользователь {old_user_id} не найден)")
    
    # Сохраняем изменения
    new_conn.commit()
    
    print("✅ Миграция завершена!")
    print(f"📊 Перенесено:")
    print(f"   - Пользователей: {len(old_users)}")
    print(f"   - Товаров: {len(old_products)}")
    
    old_conn.close()
    new_conn.close()

if __name__ == "__main__":
    migrate_production_data()