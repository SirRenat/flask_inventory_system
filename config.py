import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-123'
    
    # ОБЯЗАТЕЛЬНО используем DATABASE_URL из Render
    database_url = os.environ.get('DATABASE_URL')
    if database_url:
        # Исправляем postgres:// на postgresql://
        if database_url.startswith('postgres://'):
            database_url = database_url.replace('postgres://', 'postgresql://', 1)
        SQLALCHEMY_DATABASE_URI = database_url
        print(f"✅ Используется PostgreSQL: {database_url[:50]}...")
    else:
        SQLALCHEMY_DATABASE_URI = 'sqlite:///site.db'
        print("⚠️ Используется SQLite (разработка)")
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False