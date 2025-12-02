# diagnose_db.py
import os
import sys

def diagnose_connection():
    print("🔍 ДИАГНОСТИКА ПРОБЛЕМЫ С ПОДКЛЮЧЕНИЕМ")
    print("=" * 50)
    
    # Проверяем переменные окружения
    print("📊 Переменные окружения:")
    for key in ['DATABASE_URL', 'DB_PASSWORD', 'SECRET_KEY']:
        value = os.environ.get(key)
        if value:
            print(f"  {key}: {'*' * len(value) if 'PASSWORD' in key else value[:50]}")
        else:
            print(f"  {key}: не установлена")
    
    # Тестовая строка подключения
    test_conn = 'postgresql://postgres:postgres@localhost/flask_inventory?client_encoding=utf8'
    print(f"\n📝 Тестовая строка подключения:")
    print(f"  {test_conn}")
    print(f"  Длина: {len(test_conn)} символов")
    
    # Проверяем ASCII символы
    try:
        test_conn.encode('ascii')
        print("  ✅ Содержит только ASCII символы")
    except UnicodeEncodeError as e:
        print(f"  ❌ Содержит не-ASCII символы: {e}")
        # Находим проблемный символ
        for i, char in enumerate(test_conn):
            try:
                char.encode('ascii')
            except UnicodeEncodeError:
                print(f"  ⚠️ Не-ASCII символ на позиции {i}: {repr(char)}")
    
    # Проверяем UTF-8
    try:
        test_conn.encode('utf-8')
        print("  ✅ Корректная UTF-8 кодировка")
    except UnicodeEncodeError as e:
        print(f"  ❌ Проблема с UTF-8: {e}")
    
    print("\n🔧 Проверяем PostgreSQL:")
    try:
        import psycopg2
        print("  ✅ psycopg2 установлен")
    except ImportError:
        print("  ❌ psycopg2 не установлен")
        print("  Установите: pip install psycopg2-binary")
    
    print("\n🚀 Тестируем подключение к PostgreSQL...")
    try:
        # Пробуем несколько вариантов
        test_connections = [
            'postgresql://postgres:postgres@localhost:5432/postgres',
            'postgresql://postgres:@localhost:5432/postgres',
            'postgresql://postgres@localhost:5432/postgres'
        ]
        
        for conn_str in test_connections:
            print(f"\n  Пробуем: {conn_str.split('@')[0]}@...")
            try:
                import psycopg2
                conn = psycopg2.connect(conn_str)
                print(f"  ✅ Успешно!")
                conn.close()
                break
            except Exception as e:
                print(f"  ❌ Ошибка: {e}")
                
    except Exception as e:
        print(f"  ❌ Общая ошибка: {e}")

if __name__ == "__main__":
    diagnose_connection()