import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-123'
    
    # Используем DATABASE_URL с psycopg3
    database_url = os.environ.get('DATABASE_URL')
    if database_url:
        # Явно указываем использование psycopg3
        if database_url.startswith('postgres://'):
            database_url = database_url.replace('postgres://', 'postgresql+psycopg://', 1)
        elif database_url.startswith('postgresql://'):
            database_url = database_url.replace('postgresql://', 'postgresql+psycopg://', 1)
        
        SQLALCHEMY_DATABASE_URI = database_url
        DEBUG = False
        print(f"🚀 ПРОДАКШЕН: Используется PostgreSQL с psycopg3")
        print(f"🔗 DATABASE_URL: {database_url[:50]}...")
    else:
        # Локальная разработка
        SQLALCHEMY_DATABASE_URI = 'sqlite:///site.db'
        DEBUG = True
        print("💻 РАЗРАБОТКА: Используется SQLite")
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}