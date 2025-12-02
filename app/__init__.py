# __init__.py
import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
import os

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()

@login_manager.user_loader
def load_user(user_id):
    from app.models import User
    return User.query.get(int(user_id))

def create_app():
    app = Flask(__name__)
    
    # Настройки по умолчанию
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')
    
    # Настройка базы данных
    if os.environ.get('DATABASE_URL'):
        # Для продакшн (Render)
        app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
        # Исправляем для PostgreSQL
        if app.config['SQLALCHEMY_DATABASE_URI'].startswith("postgres://"):
            app.config['SQLALCHEMY_DATABASE_URI'] = app.config['SQLALCHEMY_DATABASE_URI'].replace("postgres://", "postgresql://", 1)
        print("🚀 ПРОДАКШЕН: Используется PostgreSQL с Render")
        print(f"🔗 DATABASE_URL: {app.config['SQLALCHEMY_DATABASE_URI'][:60]}...")
    else:
        # Для разработки
        app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:postgres@localhost/flask_inventory'
        print("💻 РАЗРАБОТКА: Используется локальный PostgreSQL")
    
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads')
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB
    
    # Инициализация расширений
    db.init_app(app)
    migrate.init_app(app, db) 
    login_manager.init_app(app)
    
    # Настройка login_manager
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Пожалуйста, войдите в систему для доступа к этой странице.'
    login_manager.login_message_category = 'info'
    
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
    from app.admin import admin
    
    app.register_blueprint(main)
    app.register_blueprint(auth)
    app.register_blueprint(admin)

    # Инициализация базы данных
    with app.app_context():
        # Создаем таблицы если их нет
        try:
            db.create_all()
            print("✅ Таблицы созданы/проверены")
            
            # Создаем администратора если его нет
            from app.models import User
            from werkzeug.security import generate_password_hash
            
            admin_email = os.environ.get('ADMIN_EMAIL', 'admin@example.com')
            admin_password = os.environ.get('ADMIN_PASSWORD', 'admin123')
            admin_user = User.query.filter_by(email=admin_email).first()
            
            if not admin_user:
                print("👤 Создаем администратора...")
                admin_user = User(
                    email=admin_email,
                    company_name='Администратор системы',
                    password_hash=generate_password_hash(admin_password),
                    inn='1234567890',
                    legal_address='г. Москва',
                    contact_person='Администратор',
                    position='Администратор',
                    phone='+79991234567',
                    industry='IT',
                    username='admin',
                    role='admin'
                )
                db.session.add(admin_user)
                db.session.commit()
                print(f"✅ Администратор создан: {admin_email} / {admin_password}")
            else:
                print("📊 Администратор уже существует")
                
            print("🎉 Приложение готово к работе!")
            
        except Exception as e:
            print(f"❌ Ошибка при инициализации базы данных: {e}")
            import traceback
            traceback.print_exc()

    return app