from dotenv import load_dotenv
load_dotenv()

from flask import Flask, g, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect
from time import time
import os

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
csrf = CSRFProtect()

    # Initialize Flask-Mail - Removed
    # from flask_mail import Mail
    # mail = Mail()

# =========== ДОБАВЬТЕ ЭТО ===========
try:
    from .telegram_bot import telegram_bot
except ImportError as e:
    print(f"[ERROR] Не удалось импортировать Telegram бот: {e}")
    telegram_bot = None
# ====================================

def create_app():
    app = Flask(__name__)
    app.config.from_object('config.Config')
    
    # Инициализация расширений
    db.init_app(app)
    migrate.init_app(app, db) 
    login_manager.init_app(app)
    csrf.init_app(app)
    # mail.init_app(app) # Отключено, используем smtplib в app/email.py
    
    # =========== ДОБАВЬТЕ ЭТО ===========
    # Инициализируем Telegram ботаtemplate_folder='templates',
    if telegram_bot:
        telegram_bot.init_app(app)
        print(f"[OK] Telegram бот инициализирован: токен={'установлен' if app.config.get('TELEGRAM_BOT_TOKEN') else 'не указан'}, chat_id={app.config.get('TELEGRAM_CHAT_ID')}")
    else:
        print("[WARN] Telegram бот не загружен")
    # ====================================
    
    @app.before_request
    def before_request():
        g.start_time = time()

    @app.context_processor
    def inject_generation_time():
        if hasattr(g, 'start_time'):
            elapsed = (time() - g.start_time) * 1000  # мс
            return {'generation_time_ms': f"{elapsed:.2f}"}
        return {'generation_time_ms': '0.00'}

    # Настройки login_manager
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Пожалуйста, войдите в систему для доступа к этой странице.'
    login_manager.login_message_category = 'info'
    
    # Регистрация фильтров
    from app.utils import format_price
    app.jinja_env.filters['format_price'] = format_price

    
    @login_manager.user_loader
    def load_user(user_id):
        from app.models import User
        return db.session.get(User, int(user_id))

    # Импортируем Region для Flask-Admin
    from app.models import Region
    
    # Создаем папку для загрузок
    try:
        upload_folder = app.config.get('UPLOAD_FOLDER')
        if upload_folder:
            os.makedirs(upload_folder, exist_ok=True)
            print(f"[OK] Папка загрузок: {upload_folder}")
            
            # Проверяем доступность папки
            test_file = os.path.join(upload_folder, 'test.txt')
            with open(test_file, 'w') as f:
                f.write('test')
            os.remove(test_file)
            print("[OK] Папка загрузок доступна для записи")
    except Exception as e:
        print(f"[ERROR] Ошибка папки загрузок: {e}")
    
    # Регистрация blueprint
    # Импорт Blueprint'ов
    from app.blueprints.main import main
    from app.blueprints.api import api_bp
    from app.auth import auth as auth_blueprint
    from app.admin import admin_bp

    app.register_blueprint(main)
    app.register_blueprint(api_bp)
    app.register_blueprint(auth_blueprint)
    app.register_blueprint(admin_bp)

    from app.blueprints.monitoring import monitoring_bp
    app.register_blueprint(monitoring_bp)

    from flask_admin import Admin
    from flask_admin.contrib.sqla import ModelView

    admin_flask = Admin(app, name='Админка')
    admin_flask.add_view(ModelView(Region, db.session, name='Регионы', category='Справочники'))
    
    # Обработчик ошибок CSRF
    from flask_wtf.csrf import CSRFError
    from werkzeug.exceptions import HTTPException
    
    @app.errorhandler(CSRFError)
    def handle_csrf_error(e):
        return render_template('csrf_error.html', reason=e.description), 400

    # Обработчик всех 500-х ошибок
    @app.errorhandler(500)
    def handle_internal_error(e):
        if telegram_bot:
            telegram_bot.send_error_notification(e)
        return render_template('500.html'), 500

    @app.errorhandler(Exception)
    def handle_exception(e):
        # Pass through HTTP errors
        if isinstance(e, HTTPException):
            return e
            
        # Handle non-HTTP exceptions
        if telegram_bot:
            telegram_bot.send_error_notification(e)
        # We can return a generic 500 page or let Flask handle it (which will trigger 500 handler usually)
        # But handle_exception catches everything.
        print(f"[ERROR-HANDLER] {e}")
        return render_template('500.html'), 500

    # Регистрация хуков запуска и остановки
    import atexit
    
    def on_exit():
        if telegram_bot:
            telegram_bot.send_shutdown_notification()
            print("[INFO] System stop notification sent.")

    atexit.register(on_exit)
    
    # Уведомление о запуске (только для основного процесса, не релоадера)
    if telegram_bot and not app.debug or os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
         try:
             telegram_bot.send_startup_notification()
         except:
             print("[WARN] Could not send startup notification")

    print("=" * 50)
    print("[SUCCESS] Приложение инициализировано успешно!")
    print("=" * 50)
    
    return app