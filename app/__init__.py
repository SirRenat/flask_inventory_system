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
    from app.admin import admin
    
    app.register_blueprint(main)
    app.register_blueprint(auth)
    app.register_blueprint(admin)

    # ❌ ВРЕМЕННО ЗАКОММЕНТИРУЙТЕ ЭТОТ БЛОК:
    '''
    # ✅ СОВРЕМЕННЫЙ СПОСОБ ИНИЦИАЛИЗАЦИИ ДАННЫХ
    with app.app_context():
        # Создаем таблицы (только для разработки)
        if app.config.get('DEBUG', False):
            db.create_all()
            print("✅ Таблицы созданы (режим разработки)")
        
        # Инициализация данных
        try:
            from app.models import Category, User
            import os
            
            # Создаем категории если их нет
            if Category.query.count() == 0:
                print("🔄 Создаем категории...")
                categories = ['Электроника', 'Оборудование', 'Мебель', 'Стройматериалы']
                for cat_name in categories:
                    db.session.add(Category(name=cat_name))
                db.session.commit()
                print("✅ Категории созданы")
            
            # Создаем администратора если его нет
            admin_email = os.environ.get('ADMIN_EMAIL', 'admin@example.com')
            admin_password = os.environ.get('ADMIN_PASSWORD', 'admin123')
            
            if not User.query.filter_by(email=admin_email).first():
                print("🔄 Создаем администратора...")
                admin_user = User(
                    email=admin_email,
                    company_name='Администратор системы',
                    inn='0000000000',
                    legal_address='г. Москва',
                    contact_person='Администратор',
                    position='Системный администратор',
                    phone='+79990000000',
                    industry='it',
                    username='admin'
                )
                admin_user.set_password(admin_password)
                
                db.session.add(admin_user)
                db.session.commit()
                print("✅ Администратор создан")
            
            print("🎉 База данных инициализирована")
            
        except Exception as e:
            print(f"❌ Ошибка инициализации данных: {e}")
    '''

    return app