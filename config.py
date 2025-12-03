import os
import tempfile

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-123'
    
    # Определяем среду
    is_render = os.environ.get('RENDER') or os.environ.get('DATABASE_URL')
    
    if is_render:
        # Для Render с psycopg3
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
        
        # На Render используем временную папку
        UPLOAD_FOLDER = os.path.join(tempfile.gettempdir(), 'uploads')
        print(f"⚠️ Render: файлы хранятся временно")
        
    else:
        # Локальная разработка с psycopg2
        SQLALCHEMY_DATABASE_URI = 'postgresql://postgres:postgres@localhost:5432/flask_inventory'
        DEBUG = True
        print("💻 РАЗРАБОТКА: Локальный PostgreSQL")
        
        # ← ИСПРАВЛЕНО: путь внутри app/static/uploads (чтобы Flask мог обслуживать)
        UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app', 'static', 'uploads')
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}