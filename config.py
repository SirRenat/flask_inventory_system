import os
import tempfile

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-123'
    
    # Определяем среду
    is_production = os.environ.get('DATABASE_URL') is not None
    
    if is_production:
        # Для продакшена (Selectel, Render, Heroku и т.д.)
        database_url = os.environ.get('DATABASE_URL', '')
        
        # Исправляем URL и добавляем диалект для psycopg3
        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql+psycopg://", 1)
        elif database_url.startswith("postgresql://"):
            # Меняем диалект на psycopg3
            database_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)
        
        SQLALCHEMY_DATABASE_URI = database_url
        DEBUG = False
        print(f"🚀 ПРОДАКШЕН: Используется PostgreSQL с psycopg3")
        
        # В продакшене используем временную папку (лучше настроить S3 в будущем)
        UPLOAD_FOLDER = '/opt/flask_inventory_system/uploads'
        
    else:
        # Локальная разработка
        SQLALCHEMY_DATABASE_URI = 'postgresql://postgres:postgres@localhost:5432/flask_inventory'
        DEBUG = True
        print("💻 РАЗРАБОТКА: Локальный PostgreSQL")
        
        UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app', 'static', 'uploads')
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

    # Telegram Bot настройки
    TELEGRAM_BOT_TOKEN = '8576859315:AAFUsWf2_L2ZaJEE8lUxTgOxK_e2IlOTnD0' 
    TELEGRAM_CHAT_ID = '390300'  # Ваш Chat ID
    TELEGRAM_ENABLED = True