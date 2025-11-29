import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-123'
    
    # Используем DATABASE_URL из Render
    database_url = os.environ.get('DATABASE_URL')
    if database_url:
        if database_url.startswith('postgres://'):
            database_url = database_url.replace('postgres://', 'postgresql://', 1)
        SQLALCHEMY_DATABASE_URI = database_url
        print(f"✅ Используется PostgreSQL")
    else:
        SQLALCHEMY_DATABASE_URI = 'sqlite:///site.db'
        print("⚠️ Используется SQLite (разработка)")
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads')
    
    # ⭐ ДОБАВЛЯЕМ НАСТРОЙКИ ДЛЯ ЗАГРУЗКИ ФАЙЛОВ
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}