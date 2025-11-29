from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from app import db
from app.models import User

auth = Blueprint('auth', __name__)

@auth.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        try:
            # Получаем данные из формы
            email = request.form['email']
            password = request.form['password']
            confirm_password = request.form['confirm_password']
            
            # Проверяем пароли
            if password != confirm_password:
                flash('Пароли не совпадают', 'error')
                return redirect(url_for('auth.register'))
            
            # Проверяем, существует ли пользователь
            existing_user = User.query.filter_by(email=email).first()
            if existing_user:
                flash('Пользователь с таким email уже существует', 'error')
                return redirect(url_for('auth.register'))
            
            # Проверяем согласие с условиями
            if 'agree_terms' not in request.form:
                flash('Необходимо согласие с условиями использования', 'error')
                return redirect(url_for('auth.register'))
            
            # Создаем нового пользователя
            new_user = User(
                email=email,
                company_name=request.form['company_name'],
                inn=request.form['inn'],
                legal_address=request.form['legal_address'],
                contact_person=request.form['contact_person'],
                position=request.form['position'],
                phone=request.form['phone'],
                industry=request.form.get('industry', ''),
                about=request.form.get('about', ''),
                # Генерируем username из email
                username=email.split('@')[0]
            )
            new_user.set_password(password)
            
            # Сохраняем в базу
            db.session.add(new_user)
            db.session.commit()
            
            flash('Регистрация успешна! Теперь вы можете войти в систему.', 'success')
            return redirect(url_for('auth.login'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при регистрации: {str(e)}', 'error')
            return redirect(url_for('auth.register'))
    
    return render_template('register.html')

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        user = User.query.filter_by(email=email).first()
        
        if user and check_password_hash(user.password_hash, password):
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