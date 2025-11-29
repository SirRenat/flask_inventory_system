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
    app.config.from_object('config.Config')
    
    # Инициализация расширений
    db.init_app(app)
    migrate.init_app(app, db) 
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

    # ⭐ ДОБАВЛЯЕМ СОЗДАНИЕ ДАННЫХ ДЛЯ ПРОДАКШЕНА
    with app.app_context():
        # Создаем таблицы
        db.create_all()
        
        # Импортируем функции создания данных
        from app.models import Category, Unit, User
        from werkzeug.security import generate_password_hash
        
        # Создаем категории если их нет
        if Category.query.count() == 0:
            print("🔄 Создаем категории на продакшене...")
            # Базовые категории
            categories = ['Электроника', 'Оборудование', 'Мебель', 'Стройматериалы']
            for cat_name in categories:
                db.session.add(Category(name=cat_name))
            db.session.commit()
            print("✅ Категории созданы")
        
        # Создаем единицы измерения если их нет
        if Unit.query.count() == 0:
            print("🔄 Создаем единицы измерения на продакшене...")
            units = ['шт', 'кг', 'м', 'упаковка']
            for unit_name in units:
                db.session.add(Unit(name=unit_name))
            db.session.commit()
            print("✅ Единицы измерения созданы")
        
        # Создаем администратора если его нет
        admin_email = 'admin@example.com'
        if not User.query.filter_by(email=admin_email).first():
            print("🔄 Создаем администратора на продакшене...")
            hashed_password = generate_password_hash('admin123')
            admin_user = User(
                company_name='Администратор системы',
                email=admin_email,
                password_hash=hashed_password,
                phone='+7 (999) 123-45-67',
                inn='1234567890',
                role='admin'
            )
            db.session.add(admin_user)
            db.session.commit()
            print('✅ Администратор создан')
        
        print("🎉 Продакшен база данных инициализирована")

    return app  # ⭐ ТОЛЬКО ОДИН RETURN