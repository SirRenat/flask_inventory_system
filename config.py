import os
import tempfile

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-123'
    
    # Используем свойства (property) для ленивой загрузки
    @property
    def is_production(self):
        return os.environ.get('DATABASE_URL') is not None
    
    @property
    def SQLALCHEMY_DATABASE_URI(self):
        if self.is_production:
            # Для продакшена (Selectel, Render, Heroku и т.д.)
            database_url = os.environ.get('DATABASE_URL', '')
            
            # Исправляем URL и добавляем диалект для psycopg3
            if database_url.startswith("postgres://"):
                database_url = database_url.replace("postgres://", "postgresql+psycopg://", 1)
            elif database_url.startswith("postgresql://"):
                # Меняем диалект на psycopg3
                database_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)
            
            return database_url
        else:
            # Локальная разработка - ОБНОВИ ПАРОЛЬ ЗДЕСЬ!
            return 'postgresql+psycopg://postgres:Mat604192@localhost:5432/flask_inventory'
    
    @property
    def DEBUG(self):
        return not self.is_production
    
    @property
    def UPLOAD_FOLDER(self):
        if self.is_production:
            # В продакшене используем временную папку (лучше настроить S3 в будущем)
            return '/opt/flask_inventory_system/app/static/uploads'
        else:
            # Локальная разработка
            return os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app', 'static', 'uploads')
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

    # Telegram Bot настройки
    TELEGRAM_BOT_TOKEN = '8576859315:AAFUsWf2_L2ZaJEE8lUxTgOxK_e2IlOTnD0' 
    TELEGRAM_CHAT_ID = '390300'  # Ваш Chat ID
    TELEGRAM_ENABLED = True

    # Email settings
    MAIL_SERVER = 'mail.hosting.reg.ru'
    MAIL_PORT = 465
    MAIL_USE_SSL = True
    MAIL_USERNAME = 'no-reply@asauda.ru'
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD') or '!Mat604192'
    MAIL_DEFAULT_SENDER = 'no-reply@asauda.ru'

    # DaData API
    DADATA_API_KEY = os.environ.get('DADATA_API_KEY') or '101eb3d6682561b0db5bf155c592a3f8dad52dcf'