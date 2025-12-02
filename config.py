# config.py
import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-123'
    
    # Для продакшена на Render
    if os.environ.get('RENDER'):
        DATABASE_URL = os.environ.get('DATABASE_URL')
        if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
            DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
        SQLALCHEMY_DATABASE_URI = DATABASE_URL
        DEBUG = False
        print(f"🚀 ПРОДАКШЕН: Используется PostgreSQL с Render")
    else:
        # Для локальной разработки - с указанием client_encoding
        SQLALCHEMY_DATABASE_URI = 'postgresql://postgres:postgres@localhost:5432/flask_inventory?client_encoding=utf8'
        DEBUG = True
        print("💻 РАЗРАБОТКА: Используется локальный PostgreSQL с UTF-8")
        print(f"🔗 База: flask_inventory")
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}