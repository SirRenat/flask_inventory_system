# test_final_connection.py
import os
import sys

# Устанавливаем UTF-8 для Python
os.environ['PYTHONUTF8'] = '1'

print("🔍 ФИНАЛЬНАЯ ПРОВЕРКА ПОДКЛЮЧЕНИЯ")
print("=" * 50)

# Тест 1: Прямое подключение psycopg2
try:
    import psycopg2
    conn = psycopg2.connect(
        host="localhost",
        database="flask_inventory",
        user="postgres",
        password="postgres",
        port=5432
    )
    print("✅ 1. Psycopg2 подключение успешно")
    
    # Проверяем UTF-8
    cursor = conn.cursor()
    cursor.execute("SELECT 'Привет мир! Тест UTF-8: ελληνικά 中文'")
    result = cursor.fetchone()
    print(f"✅ 2. UTF-8 строка: {result[0]}")
    
    cursor.close()
    conn.close()
except Exception as e:
    print(f"❌ Ошибка psycopg2: {e}")

print()

# Тест 2: SQLAlchemy подключение
try:
    from flask import Flask
    from flask_sqlalchemy import SQLAlchemy
    
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:postgres@localhost:5432/flask_inventory?client_encoding=utf8'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    db = SQLAlchemy(app)
    
    # Простая модель
    class TestItem(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        title = db.Column(db.String(100))
    
    with app.app_context():
        db.create_all()
        print("✅ 3. SQLAlchemy создал таблицы")
        
        # Тест с русским текстом
        item = TestItem(title="Тестовый русский текст")
        db.session.add(item)
        db.session.commit()
        print("✅ 4. Русский текст сохранен в БД")
        
        # Чтение
        result = TestItem.query.first()
        print(f"✅ 5. Текст прочитан: {result.title}")
        
except Exception as e:
    print(f"❌ Ошибка SQLAlchemy: {e}")
    import traceback
    traceback.print_exc()

print()
print("🎉 Проверка завершена!")