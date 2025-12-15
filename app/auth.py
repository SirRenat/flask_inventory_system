from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from app import db
from app.models import User
from app.email import send_email
import logging
from flask import current_app
from datetime import datetime

# === ДОБАВЬТЕ ЭТОТ ИМПОРТ ===
from app.telegram_bot import telegram_bot

auth = Blueprint('auth', __name__)
logger = logging.getLogger(__name__)

@auth.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        try:
            email = request.form['email']
            password = request.form['password']
            confirm_password = request.form['confirm_password']
            username = request.form.get('username') or email.split('@')[0]
            
            if password != confirm_password:
                flash('Пароли не совпадают', 'error')
                return redirect(url_for('auth.register'))
            
            if User.query.filter_by(email=email).first():
                flash('Пользователь с таким email уже существует', 'error')
                return redirect(url_for('auth.register'))
            
            if User.query.filter_by(username=username).first():
                flash('Пользователь с таким именем пользователя уже существует', 'error')
                return redirect(url_for('auth.register'))
            
            if 'agree_terms' not in request.form:
                flash('Необходимо согласие с условиями использования', 'error')
                return redirect(url_for('auth.register'))
            
            new_user = User(
                email=email,
                username=username,
                company_name=request.form['company_name'],
                inn=request.form['inn'],
                legal_address=request.form['legal_address'],
                contact_person=request.form['contact_person'],
                position=request.form['position'],
                phone=request.form['phone'],
                industry=request.form.get('industry', ''),
                about=request.form.get('about', ''),
                is_active=False # Требует подтверждения
            )
            new_user.set_password(password)
            
            db.session.add(new_user)
            db.session.commit()
            
            # === ДОБАВЬТЕ ЭТОТ КОД ДЛЯ TELEGRAM УВЕДОМЛЕНИЯ ===
            try:
                # Проверяем, включен ли Telegram бот
                from flask import current_app
                if current_app.config.get('TELEGRAM_ENABLED', True):
                    success = telegram_bot.send_new_user_notification(new_user)
                    if success:
                        logger.info(f"✅ Telegram уведомление отправлено о новом пользователе: {username}")
                    else:
                        logger.warning(f"⚠️ Не удалось отправить Telegram уведомление о пользователе: {username}")
            except Exception as e:
                logger.error(f"❌ Ошибка при отправке Telegram уведомления: {e}")
                # Не прерываем регистрацию из-за ошибки Telegram
            # === КОНЕЦ ДОБАВЛЕННОГО КОДА ===
            
            # =========== ДОБАВЬТЕ ЭТОТ ИМПОРТ ===========
            try:
                from .telegram_bot import telegram_bot
                TELEGRAM_BOT_AVAILABLE = True
            except ImportError:
                telegram_bot = None
                TELEGRAM_BOT_AVAILABLE = False
                print("⚠️ Telegram бот не доступен в auth.py")
            # ============================================

            if TELEGRAM_BOT_AVAILABLE and telegram_bot:
                try:
                    if current_app.config.get('TELEGRAM_ENABLED', True):
                        success = telegram_bot.send_new_user_notification(new_user)
                        if success:
                            logger.info(f"✅ Telegram уведомление отправлено о новом пользователе: {new_user.username}")
                        else:
                            logger.warning(f"⚠️ Не удалось отправить Telegram уведомление о пользователе: {new_user.username}")
                except Exception as e:
                    logger.error(f"❌ Ошибка при отправке Telegram уведомления: {e}")
                    # Не прерываем регистрацию из-за ошибки Telegram
            else:
                logger.info("ℹ️ Telegram бот не доступен, уведомление не отправлено")

            # Автоматический вход отключен, требуем подтверждения почты
            # login_user(new_user)
            
            # Генерируем токен и отправляем письмо
            from itsdangerous import URLSafeTimedSerializer
            ts = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
            token = ts.dumps(email, salt='email-confirm-key')
            
            confirm_url = url_for('auth.confirm_email', token=token, _external=True)
            
            send_email(email, 'Подтверждение регистрации', 'confirm_email', confirm_url=confirm_url)
            
            flash('Регистрация успешна! На вашу почту отправлено письмо для подтверждения аккаунта.', 'info')
            return redirect(url_for('auth.login'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при регистрации: {str(e)}', 'error')
            return redirect(url_for('auth.register'))
    
    return render_template('register.html')

@auth.route('/confirm/<token>')
def confirm_email(token):
    try:
        from itsdangerous import URLSafeTimedSerializer
        ts = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
        email = ts.loads(token, salt='email-confirm-key', max_age=86400)
    except:
        flash('Ссылка подтверждения недействительна или истекла', 'error')
        return redirect(url_for('auth.login'))
    
    user = User.query.filter_by(email=email).first_or_404()
    
    if user.is_active:
        flash('Аккаунт уже подтвержден', 'info')
    else:
        user.is_active = True
        user.confirmed_at = datetime.utcnow()
        db.session.add(user)
        db.session.commit()
        flash('Ваш аккаунт успешно подтвержден! Теперь вы можете войти.', 'success')
        
    return redirect(url_for('auth.login'))


@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(password):
            # Проверяем подтверждение почты
            if not user.is_active:
                flash('Ваш аккаунт не подтвержден. Пожалуйста, проверьте почту и перейдите по ссылке активации.', 'warning')
                return render_template('login.html')

            login_user(user)
            flash('Вы успешно вошли в систему!', 'success')
            return redirect(url_for('main.dashboard'))
        else:
            flash('Неверный email или пароль', 'error')
    
    return render_template('login.html')

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Вы вышли из системы', 'info')
    return redirect(url_for('main.index'))

@auth.route('/debug_register')
def debug_register():
    return render_template('debug_register.html')