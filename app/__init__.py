# __init__.py
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
import os

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()

def create_app():
    app = Flask(__name__)
    app.config.from_object('config.Config')
    
    # Инициализация расширений
    db.init_app(app)
    migrate.init_app(app, db) 
    login_manager.init_app(app)
    
    # Настройки login_manager
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Пожалуйста, войдите в систему для доступа к этой странице.'
    login_manager.login_message_category = 'info'
    
    # User loader
    @login_manager.user_loader
    def load_user(user_id):
        from app.models import User
        return db.session.get(User, int(user_id))
    
    # Создаем папку для загрузок
    try:
        upload_folder = app.config.get('UPLOAD_FOLDER')
        if upload_folder:
            os.makedirs(upload_folder, exist_ok=True)
            print(f"✅ Папка загрузок: {upload_folder}")
            
            # Проверяем доступность папки
            test_file = os.path.join(upload_folder, 'test.txt')
            with open(test_file, 'w') as f:
                f.write('test')
            os.remove(test_file)
            print("✅ Папка загрузок доступна для записи")
    except Exception as e:
        print(f"⚠️ Ошибка папки загрузок: {e}")
    
    # Регистрация blueprint
    from app.routes import main
    from app.auth import auth
    from app.admin import admin
    
    app.register_blueprint(main)
    app.register_blueprint(auth)
    app.register_blueprint(admin)
    
    # ВАЖНО: Инициализацию данных через db.create_all() можно оставить,
    # но лучше использовать миграции Flask-Migrate
    
    print("=" * 50)
    print("🎉 Приложение инициализировано успешно!")
    print("=" * 50)
    
    return app