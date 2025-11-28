from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
import os

db = SQLAlchemy()
login_manager = LoginManager()

def create_app():
    app = Flask(__name__)
    app.config.from_object('config.Config')
    
    # Инициализация расширений
    db.init_app(app)
    login_manager.init_app(app)
    
    # Создаем папку для загрузок если её нет
    try:
        upload_folder = app.config.get('UPLOAD_FOLDER')
        if upload_folder:
            os.makedirs(upload_folder, exist_ok=True)
            print(f"✅ Папка загрузок: {upload_folder}")
    except Exception as e:
        print(f"⚠️ Не удалось создать папку загрузок: {e}")
    
    # Регистрация blueprint
    from app.routes import main
    from app.auth import auth
    
    app.register_blueprint(main)
    app.register_blueprint(auth)
    
    return app
